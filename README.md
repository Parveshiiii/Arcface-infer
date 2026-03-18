Library: https://github.com/Parveshiiii/Insighface-updated


# Arcface-Infer API Documentation

This document outlines the API endpoints available in the inference server and the structure of the JSON results saved on disk.

## 🚀 API Endpoints

---
### 1. Generate Master Embedding
**Endpoint:** `POST /api/v1/gen_master`  
**Purpose:** Combines multiple images of the same person into a single "Master" profile.

**Request Body:**
```json
{
  "task": "GenerateEmbedding",
  "urls": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
  "post_id": ["id_1", "id_2"]
}
```

**Response:**
```json
{
  "status": "success",
  "master_embedding": [0.023, -0.011, "... 512 values"],
  "processed_count": 5,
  "source_details": [
     {"source": "url1", "post_id": "id_1", "status": "success"},
     {"source": "url2", "post_id": "id_2", "status": "no_face"}
  ]
}
```

---

### 2. Bulk Image Embedding Generation
**Endpoint:** `POST /api/v1/generate`  
**Purpose:** Scans images for ALL faces and generates individual embeddings for each. Saves results to a file.

**Request Body:**
```json
{
  "task": "GenerateEmbedding",
  "urls": ["https://example.com/photo.jpg"],
  "post_id": ["photo_1"]
}
```

**Response:**
```json
{
  "status": "success",
  "file_name": "1710580000_uuid.jsonl",
  "download_url": "http://api.link/api/v1/embeddings/images/1710580000_uuid.jsonl",
  "total_faces": 12
}
```

---

### 3. Video Analysis
**Endpoint:** `POST /api/v1/analyze_video`  
**Purpose:** Processes videos frame-by-frame (at specified FPS) to extract all faces and their timestamps.

**Request Body:**
```json
{
  "task": "VideoAnalysis",
  "sources": ["https://example.com/video.mp4"],
  "post_ids": ["vid_101"],
  "fps": 1
}
```

**Response:**
```json
{
  "status": "success",
  "file_name": "1710580000_uuid.jsonl",
  "download_url": "http://api.link/api/v1/embeddings/videos/1710580000_uuid.jsonl"
}
```


---

### 4. Download Results
**Endpoint:** `GET /api/v1/embeddings/{type}/{filename}`  
**Purpose:** Downloads the saved results from disk. `{type}` is either `images` or `videos`.

---

## 📂 File Formats (Saved in `/embedding`)

### Image Result Format (`/embedding/images/*.jsonl`)
Contains the results of the bulk image generation.

```json
{
  "status": "success",
  "total_faces": 2,
  "results": [
    {
      "source": "https://example.com/photo.jpg",
      "post_id": "photo_1",
      "status": "success",
      "faces": 2,
      "embeddings": [
        [0.012, -0.045, "... 512 values"],
        [0.056, 0.088, "... 512 values"]
      ]
    }
  ]
}
```

### Video Result Format (`/embedding/videos/*.jsonl`)
Contains frame-by-frame analysis with timestamps.

```json
{
  "status": "success",
  "results": [
    {
      "post_id": "vid_101",
      "source": "https://example.com/video.mp4",
      "status": "ok",
      "total_frames_processed": 100,
      "total_faces_detected": 15,
      "frames": [
        {
          "time_str": "00:00:05",
          "time_sec": 5.0,
          "faces": 1,
          "embeddings": [
            [0.123, -0.011, "... 512 values"]
          ],
          "status": "ok"
        }
      ]
    }
  ]
}
```

## 💡 Important Notes
- **Normalization:** All embeddings are pre-normalized. Use **Dot Product** for similarity comparison.
- **Batched Processing:** The server utilizes a high-speed producer-consumer queue to maximize GPU throughput.
- **Storage:** Results are stored as `.jsonl` files (NDJSON) for efficient streaming and access.
