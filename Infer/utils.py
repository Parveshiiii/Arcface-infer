import cv2
import numpy as np
import time
import os
import asyncio
from load_video import load_video

import json
with open("config.json") as f:
    cfg = json.load(f)

BATCH_SIZE = cfg['inference'].get('video_batch_size', cfg['inference']['batch_size'])
DET_CONCURRENCY = cfg['inference'].get('video_detection_concurrency', cfg['inference'].get('detection_concurrency', 4))
MAX_WIDTH = cfg['video']['max_width']
ALIGN_3D = cfg['inference'].get('align_3d', False)

async def analyze_video(
    video_source, 
    face_app, 
    frames_per_second=1,
    post_id: str = None
):
    """
    Ultra-Optimized Video Analysis for Extraction.
    
    Processes video at X FPS, downscaling to 720p.
    Returns ALL embeddings per frame with timestamps for external comparison.
    """
    
    # 1. Download/Load Video
    video_path = await load_video(video_source)
    
    result = {
        "post_id": post_id or "unknown",
        "source": video_source,
        "status": "ok",
        "total_frames_processed": 0,
        "total_faces_detected": 0,
        "frames": []
    }
    
    if not video_path:
        result["status"] = "load_failed"
        return result

    try:
        from insightface.utils import face_align
        from insightface.app.common import Face
        
        # Set up ultra-fast multi-stage pipelining
        loop = asyncio.get_running_loop()
        frame_queue = asyncio.Queue(maxsize=DET_CONCURRENCY * 2) 
        gpu_queue = asyncio.Queue(maxsize=DET_CONCURRENCY * 2)
        rec_model = face_app.models['recognition']
        lm3d_model = face_app.models.get('landmark_3d_68') if ALIGN_3D else None

        async def flush_gpu_batch(batch_to_process):
            if not batch_to_process: return
            
            # Stage A: Optional 3D Alignment (Quality parity with main.py)
            aligned_kps = []
            if lm3d_model is not None:
                # Build Face objects for batch landmarking
                face_objs = [Face(bbox=item[2], kps=item[3]) for item in batch_to_process]
                # item[0] is the frame
                chunk_batch = [(item[0], fo) for item, fo in zip(batch_to_process, face_objs)]
                await loop.run_in_executor(None, lm3d_model.get_batch, chunk_batch)
                
                for j, item in enumerate(batch_to_process):
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
                        kps5 = item[3] # Fallback to 5pt kps
                    aligned_kps.append(kps5)
            else:
                aligned_kps = [item[3] for item in batch_to_process]

            # Stage B: Final Recognition
            chunk_crops = [face_align.norm_crop(item[0], landmark=akps, image_size=rec_model.input_size[0]) 
                           for item, akps in zip(batch_to_process, aligned_kps)]
            
            chunk_embs = await loop.run_in_executor(None, rec_model.get_feat, chunk_crops)
            
            for j, emb in enumerate(chunk_embs):
                meta = batch_to_process[j][1]
                norm = np.linalg.norm(emb)
                if norm > 0: emb = emb / norm
                
                meta["embeddings"].append(emb.tolist())
                meta["faces"] += 1
                result["total_faces_detected"] += 1

        async def gpu_worker():
            batch = []
            while True:
                try:
                    # Frequent timeouts to automatically flush partial batches
                    item = await asyncio.wait_for(gpu_queue.get(), timeout=0.2)
                    if item is None:
                        if batch: await flush_gpu_batch(batch)
                        break
                    batch.append(item)
                    if len(batch) >= BATCH_SIZE:
                        await flush_gpu_batch(batch)
                        batch = []
                except asyncio.TimeoutError:
                    if batch:
                        await flush_gpu_batch(batch)
                        batch = []

        async def detection_worker():
            while True:
                item = await frame_queue.get()
                if item is None:
                    await frame_queue.put(None) # Signal other workers to shut down
                    break
                frame_bgr, time_str, time_sec = item
                
                frame_result = {
                    "time_str": time_str,
                    "time_sec": round(time_sec, 2),
                    "faces": 0,
                    "embeddings": [],
                    "status": "ok"
                }

                try:
                    bboxes, kpss = await loop.run_in_executor(None, lambda f=frame_bgr: face_app.det_model.detect(f, max_num=0, metric='default'))
                    
                    if bboxes.shape[0] > 0:
                        result["frames"].append(frame_result)
                        for i in range(bboxes.shape[0]):
                            kps = kpss[i] if kpss is not None else None
                            # Put full context for GPU worker to handle alignment (if enabled)
                            await gpu_queue.put((frame_bgr, frame_result, bboxes[i, :4], kps))
                    
                    result["total_frames_processed"] += 1
                except Exception as frame_e:
                    frame_result["status"] = "error"
                    frame_result["detail"] = str(frame_e)
                    result["frames"].append(frame_result)
                    result["total_frames_processed"] += 1

        def producer_thread(vid_path, target_fps):
            """Runs completely isolated from the standard asyncio loop for absolute max speed"""
            cap = cv2.VideoCapture(vid_path)
            if not cap.isOpened():
                result["status"] = "open_failed"
                asyncio.run_coroutine_threadsafe(frame_queue.put(None), loop).result()
                return
                
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            step_frames = max(1, int(round(fps / target_fps)))
            frame_idx = 0
            
            while True:
                if frame_idx % step_frames == 0:
                    ret, frame_bgr = cap.read()
                    if not ret: break
                    
                    time_sec = frame_idx / fps
                    time_str = time.strftime('%H:%M:%S', time.gmtime(time_sec))
                    
                    h, w = frame_bgr.shape[:2]
                    if w > MAX_WIDTH:
                        scale = MAX_WIDTH / float(w)
                        processed_frame = cv2.resize(frame_bgr, (MAX_WIDTH, int(h * scale)))
                    else:
                        processed_frame = frame_bgr.copy() # CRITICAL: Copy buffer to prevent race condition

                    # Use loop thread-safety to elegantly suspend if the queue is overloaded
                    asyncio.run_coroutine_threadsafe(frame_queue.put((processed_frame, time_str, time_sec)), loop).result()
                else:
                    # Optimized skip logic: use grab() instead of read() for skipped frames
                    ret = cap.grab()
                    if not ret: break
                    
                frame_idx += 1
                
            cap.release()
            asyncio.run_coroutine_threadsafe(frame_queue.put(None), loop).result()

        # Fire up the massive parallel operations
        prod_future = loop.run_in_executor(None, producer_thread, video_path, frames_per_second)
        det_tasks = [asyncio.create_task(detection_worker()) for _ in range(DET_CONCURRENCY)]
        gpu_task = asyncio.create_task(gpu_worker())
        
        await prod_future # Decoded all frames to RAM queue
        await asyncio.gather(*det_tasks) # Flushed all detections to GPU queue
        
        await gpu_queue.put(None) 
        await gpu_task # Flushed all final embeddings
        
        # Force sort simply because queues operate in non-linear sequences 
        result["frames"] = sorted(result["frames"], key=lambda x: x["time_sec"])
        
        # 4. Clean up temporary downloaded video
        if video_source.startswith('http') and "vid_" in os.path.basename(video_path):
            try: os.remove(video_path)
            except: pass
            
        return result

    except Exception as e:
        print(f"Error analyzing video: {e}")
        if video_path and os.path.exists(video_path) and "vid_" in os.path.basename(video_path):
            try: os.remove(video_path)
            except: pass
        result["status"] = "error"
        return result