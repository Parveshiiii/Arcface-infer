# NOTE: comments are added using AI
"""
BY me 

- downloading is now truly parallel, utilizing True Producer-Consumer via asyncio.Queue. 
  The GPU starts inferencing the very millisecond the first image finishes downloading.
- GPU processing is fully concurrent via ONNX Runtime native thread-safety + batching(use the updated pakage updated by me).
- Image parsing utilizes aiohttp.
"""
import os
import time
import uuid
import asyncio
import aiohttp
import aiofiles
import orjson
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from insightface.app import FaceAnalysis
import numpy as np
import uvicorn
from load_image import load_image
from utils import analyze_video
# ── Config ──
import simdjson

os.makedirs("./embedding/images", exist_ok=True)
os.makedirs("./embedding/videos", exist_ok=True)

parser = simdjson.Parser()

with open("config.json", "rb") as f:   # open in binary mode
    cfg = parser.parse(f.read())       # parse entire file


BATCH_SIZE      = cfg['inference']['batch_size']
DET_CONCURRENCY = cfg['inference'].get('detection_concurrency', 32)
ALIGN_3D        = cfg['inference'].get('align_3d', False)   # optional — default OFF
NAME            = cfg["model"]["name"]
PROVIDERS       = list(cfg["model"]["providers"])          # simdjson returns its own Array type;
DET_SIZE        = list(cfg["model"]["det_size"])           # ONNX Runtime requires a real Python list
HTTP_CONNECTION_LIMIT = cfg["network"]["http_connection_limit"]
FPS             = cfg["video"]["frames_per_second"]
ROOT            = cfg["model"]["root"]

# ── Fix: ONNX Runtime requires provider_options to be a list if providers is a list ──
RAW_OPTS = cfg["model"].get("provider_options", {})
PROVIDER_OPTIONS = [
    dict(RAW_OPTS.get(p, {})) for p in PROVIDERS
]

# Only load landmark_3d_68 if 3D alignment is enabled
ALLOWED_MODULES = [
    m for m in list(cfg["model"]["allowed_modules"])   # cast simdjson Array → list
    if m != "landmark_3d_68" or ALIGN_3D
]

face_app = FaceAnalysis(
    name=NAME,
    providers=PROVIDERS,
    provider_options=PROVIDER_OPTIONS,
    allowed_modules=ALLOWED_MODULES,
    root=ROOT
)

face_app.prepare(ctx_id=0, det_size=tuple(DET_SIZE))

http_session = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_session
    # Increase limits for high concurrency
    connector = aiohttp.TCPConnector(limit=HTTP_CONNECTION_LIMIT)
    http_session = aiohttp.ClientSession(connector=connector)
    yield
    await http_session.close()

app = FastAPI(title="Likeness-Detection", lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "This method is not allowed."}


# ── Schema ────────────────────────────────────────────────────
class MasterSchema(BaseModel):
    task: str
    urls: list[str] = []
    path: list[str] = []
    post_id: list[str] = []

class VideoSchema(BaseModel):
    task: str
    sources: list[str] = []
    post_ids: list[str] = []
    fps: int = FPS

async def producer_task(index: int, source: str, post_id: str, q: asyncio.Queue):
    """Downloads an image and instantly pushes it into the queue with its metadata."""
    img = await load_image(source, session=http_session)
    await q.put((index, source, post_id, img))

# ══════════════════════════════════════════════════════════════
# ENDPOINT 1: Master Embedding
# ══════════════════════════════════════════════════════════════
@app.post("/api/v1/gen_master")
async def generate_master(data: MasterSchema):
    if data.task != "GenerateEmbedding":
        raise HTTPException(status_code=400, detail="Invalid action specified")
    sources = (data.path or []) + data.urls
    if not sources:
        raise HTTPException(status_code=400, detail="No images provided")

    n_sources = len(sources)
    ids = (data.post_id or []) + [None] * (n_sources - len(data.post_id or []))

    q = asyncio.Queue(maxsize=DET_CONCURRENCY * 2)
    gpu_queue = asyncio.Queue(maxsize=DET_CONCURRENCY * 2)
    
    source_details = [{"source": sources[i], "post_id": ids[i], "status": "pending"} for i in range(n_sources)]
    
    from insightface.utils import face_align
    rec_model  = face_app.models['recognition']
    loop       = asyncio.get_running_loop()

    # ── Stage 1: Async Producers ──
    # Starts downloading thousands of images instantly and dumping to RAM
    producers = [asyncio.create_task(producer_task(i, sources[i], ids[i], q)) for i in range(n_sources)]

    # ── Stage 2: Concurrent Detection Workers ──
    async def detection_worker():
        while True:
            item = await q.get()
            if item is None:
                q.task_done()
                break
            index, source, p_id, img = item
            
            if img is None:
                source_details[index]["status"] = "load_failed"
                q.task_done()
                continue
                
            try:
                bboxes, kpss = await loop.run_in_executor(None, lambda f=img: face_app.det_model.detect(f, max_num=1, metric='default'))
                if bboxes.shape[0] > 0:
                    kps = kpss[0] if kpss is not None else None
                    aimg = face_align.norm_crop(img, landmark=kps, image_size=rec_model.input_size[0])
                    source_details[index]["status"] = "success"
                    await gpu_queue.put(aimg)
                else:
                    source_details[index]["status"] = "no_face"
            except Exception:
                source_details[index]["status"] = "error"
                
            q.task_done()

    # ── Stage 3: Batched GPU Worker ──
    all_embeddings = []
    
    async def flush_gpu_batch(batch):
        if not batch: return
        chunk_embs = await loop.run_in_executor(None, rec_model.get_feat, batch)
        for emb in chunk_embs:
            all_embeddings.append(emb.flatten())

    async def gpu_worker():
        batch = []
        while True:
            try:
                item = await asyncio.wait_for(gpu_queue.get(), timeout=0.1)
                if item is None:
                    if batch: await flush_gpu_batch(batch)
                    gpu_queue.task_done()
                    break
                batch.append(item)
                if len(batch) >= BATCH_SIZE:
                    await flush_gpu_batch(batch)
                    batch = []
                gpu_queue.task_done()
            except asyncio.TimeoutError:
                if batch:
                    await flush_gpu_batch(batch)
                    batch = []

    num_det_workers = DET_CONCURRENCY
    det_tasks = [asyncio.create_task(detection_worker()) for _ in range(num_det_workers)]
    gpu_task = asyncio.create_task(gpu_worker())

    # Drain pipeline
    await asyncio.gather(*producers)
    
    for _ in range(num_det_workers): await q.put(None)
    await asyncio.gather(*det_tasks)
    
    await gpu_queue.put(None)
    await gpu_task

    if not all_embeddings:
        raise HTTPException(status_code=500, detail="Could not generate embeddings")

    # Average all embeddings → L2 normalize
    minible_batch = np.stack(all_embeddings)
    master_emb = np.mean(minible_batch, axis=0)
    master_emb = master_emb / np.linalg.norm(master_emb)

    return {
        "status": "success",
        "master_embedding": master_emb.tolist(),
        "processed_count": len(all_embeddings),
        "source_details": source_details
    }

# ══════════════════════════════════════════════════════════════
# ENDPOINT 2: Generate Embeddings (all faces)
# ══════════════════════════════════════════════════════════════
@app.post("/api/v1/generate")
async def generate_embeddings(request: Request, data: MasterSchema):
    if data.task != "GenerateEmbedding":
        raise HTTPException(status_code=400, detail="Invalid action specified")
    sources = (data.path or []) + data.urls
    if not sources:
        raise HTTPException(status_code=400, detail="No images provided")

    n_sources = len(sources)
    ids = (data.post_id or []) + [None] * (n_sources - len(data.post_id or []))

    q = asyncio.Queue(maxsize=DET_CONCURRENCY * 2)
    gpu_queue = asyncio.Queue(maxsize=DET_CONCURRENCY * 2)
    
    results = [{"source": sources[i], "post_id": ids[i], "embeddings": [], "faces": 0, "status": "pending"} for i in range(n_sources)]
    total_faces = 0

    from insightface.utils import face_align
    from insightface.app.common import Face
    rec_model  = face_app.models['recognition']
    lm3d_model = face_app.models.get('landmark_3d_68') if ALIGN_3D else None
    loop       = asyncio.get_running_loop()

    # ── Stage 1: Async Producers ──
    producers = [asyncio.create_task(producer_task(i, sources[i], ids[i], q)) for i in range(n_sources)]

    # ── Stage 2: Detection Workers ──
    async def detection_worker():
        while True:
            item = await q.get()
            if item is None:
                q.task_done()
                break
            index, source, p_id, img = item
            
            if img is None:
                results[index]["status"] = "load_failed"
                q.task_done()
                continue
                
            try:
                bboxes, kpss = await loop.run_in_executor(None, lambda f=img: face_app.det_model.detect(f, max_num=0, metric='default'))
                if bboxes.shape[0] > 0:
                    results[index]["faces"] = bboxes.shape[0]
                    results[index]["status"] = "success"
                    
                    for i in range(bboxes.shape[0]):
                        face_item = (img, bboxes[i, :4], kpss[i] if kpss is not None else None, results[index])
                        await gpu_queue.put(face_item)
                else:
                    results[index]["status"] = "no_face"
            except Exception:
                results[index]["status"] = "error"
                
            q.task_done()

    # ── Stage 3: Batched GPU Worker ──
    async def flush_gpu_batch(batch):
        if not batch: return
        
        nonlocal total_faces
        total_faces += len(batch)

        aligned_kps = []
        if lm3d_model is not None:
            face_objs = [Face(bbox=bbox, kps=kps) for (img, bbox, kps, _) in batch]
            chunk_batch = [(img, fo) for (img, _, _, _), fo in zip(batch, face_objs)]
            await loop.run_in_executor(None, lm3d_model.get_batch, chunk_batch)
            
            for j, (img, bbox, kps, _) in enumerate(batch):
                try:
                    lm68 = face_objs[j].landmark_3d_68[:, :2]
                    kps5 = np.array([
                        lm68[36:42].mean(0),
                        lm68[42:48].mean(0),
                        lm68[30],
                        lm68[48],
                        lm68[54],
                    ])
                except Exception:
                    kps5 = kps
                aligned_kps.append(kps5)
        else:
            aligned_kps = [kps for (_, _, kps, _) in batch]

        crops = [face_align.norm_crop(img, landmark=kps, image_size=rec_model.input_size[0]) for (img, _, _, _), kps in zip(batch, aligned_kps)]
        chunk_embs = await loop.run_in_executor(None, rec_model.get_feat, crops)
        
        for j, emb in enumerate(chunk_embs):
            res_ptr = batch[j][3]
            norm = np.linalg.norm(emb)
            if norm > 0: emb = emb / norm
            res_ptr["embeddings"].append(emb.tolist())

    async def gpu_worker():
        batch = []
        while True:
            try:
                item = await asyncio.wait_for(gpu_queue.get(), timeout=0.1)
                if item is None:
                    if batch: await flush_gpu_batch(batch)
                    gpu_queue.task_done()
                    break
                batch.append(item)
                if len(batch) >= BATCH_SIZE:
                    await flush_gpu_batch(batch)
                    batch = []
                gpu_queue.task_done()
            except asyncio.TimeoutError:
                if batch:
                    await flush_gpu_batch(batch)
                    batch = []

    num_det_workers = DET_CONCURRENCY
    det_tasks = [asyncio.create_task(detection_worker()) for _ in range(num_det_workers)]
    gpu_task = asyncio.create_task(gpu_worker())

    await asyncio.gather(*producers)
    
    for _ in range(num_det_workers): await q.put(None)
    await asyncio.gather(*det_tasks)
    
    await gpu_queue.put(None)
    await gpu_task
    payload = {"status": "success", "results": results, "total_faces": total_faces}
    filename = f"{int(time.time())}_{uuid.uuid4()}.jsonl"
    filepath = os.path.join("./embedding/images", filename)

    # Non-blocking write — aiofiles releases the event loop so other
    # requests are never stalled while data is flushed to disk.
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(orjson.dumps(payload))
        await f.write(b"\n")  # newline at the end

    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/api/v1/embeddings/images/{filename}"

    return {
        "status": "success",
        "file_name": filename,
        "download_url": download_url,   # permanent link — valid until file is deleted
        "total_faces": total_faces
    }

# NOTE: the embeddings are pre normalized so the cosine sim is only np.dotproduct(a,b)

@app.post("/api/v1/analyze_video")
async def video_endpoint(request: Request, data: VideoSchema):
    if data.task != "VideoAnalysis":
        raise HTTPException(status_code=400, detail="Invalid action")
    
    sources = data.sources
    if not sources:
        raise HTTPException(status_code=400, detail="No video sources provided")
    
    n_sources = len(sources)
    post_ids = (data.post_ids or []) + [None] * (n_sources - len(data.post_ids or []))
    
    tasks = []
    for i in range(n_sources):
        tasks.append(
            analyze_video(
                video_source=sources[i],
                face_app=face_app,
                frames_per_second=data.fps,
                post_id=post_ids[i]
            )
        )
    
    try:
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                final_results.append({
                    "source": sources[i],
                    "post_id": post_ids[i],
                    "status": "error",
                    "detail": str(res)
                })
            else:
                final_results.append(res)

        payload = {"status": "success", "results": final_results}
        filename = f"{int(time.time())}_{uuid.uuid4()}.jsonl"
        filepath = os.path.join("./embedding/videos", filename)

        # Non-blocking write — keeps the event loop free for other requests.
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(orjson.dumps(payload))
            await f.write(b"\n")  # newline at the end

        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/api/v1/embeddings/videos/{filename}"

        return {
            "status": "success",
            "file_name": filename,
            "download_url": download_url,   # permanent link — valid until file is deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# ENDPOINT: Download embedding file
# ══════════════════════════════════════════════════════════════
@app.get("/api/v1/embeddings/{embed_type}/{filename}")
async def download_embedding(embed_type: str, filename: str):
    """
    Serve a saved embedding file for download.
    The URL is permanent — it is valid as long as the file exists on disk.
    DELETE the file to invalidate the link (returns 404 automatically).

    embed_type : 'images' | 'videos'
    filename   : the file_name value returned by /generate or /analyze_video
    """
    # ── Validate embed_type ──
    if embed_type not in ("images", "videos"):
        raise HTTPException(
            status_code=400,
            detail="Invalid embed_type. Must be 'images' or 'videos'."
        )

    # ── Path-traversal guard ──
    # Reject any filename that tries to escape the embedding directory.
    # e.g. filename='../../config.json' would leak sensitive files without this.
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    filepath = os.path.join(f"./embedding/{embed_type}", filename)

    # ── Check file exists ──
    if not os.path.isfile(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found. It may have been deleted."
        )

    # ── Stream file to client ──
    # FileResponse streams in chunks — the full file is never loaded into RAM.
    # Content-Disposition: attachment forces a download dialog in browsers.
    return FileResponse(
        path=filepath,
        media_type="application/x-ndjson",
        filename=filename,
        headers={"Cache-Control": "no-store"},  # don't let proxies cache embedding data
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)