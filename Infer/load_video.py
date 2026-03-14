# essentials
import cv2
import numpy as np
import aiohttp
import asyncio
import os
import tempfile
import uuid
import simdjson

parser = simdjson.Parser()

with open("config.json", "rb") as f:   # open in binary mode
    cfg = parser.parse(f.read())       # parse entire file


MAX_RETRIES = cfg['network']['max_retries']
INITIAL_WAIT = cfg['network']['initial_wait_sec']
VIDEO_TIMEOUT = cfg['network']['video_timeout_sec']

async def load_video(source: str, session: aiohttp.ClientSession = None):
    try:
        # Check if URL
        if source.startswith('http') or source.startswith('https'):
            wait = INITIAL_WAIT
            
            # Use provided session or create an ad-hoc one
            own_session = False
            if session is None:
                session = aiohttp.ClientSession()
                own_session = True
            try:
                for attempt in range(MAX_RETRIES):
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                        # Give it a slightly higher timeout since videos are larger than images
                        async with session.get(source, timeout=aiohttp.ClientTimeout(total=VIDEO_TIMEOUT), headers=headers) as resp:
                            # rate limited — exponential backoff
                            if resp.status == 429:
                                print(f"Rate limited on {source}, waiting {wait}s (attempt {attempt+1}/{MAX_RETRIES})")
                                await asyncio.sleep(wait)
                                wait *= 2
                                continue

                            # non-retryable HTTP error (403, 404, etc.)
                            if resp.status >= 400:
                                print(f"HTTP {resp.status} for {source}")
                                return None

                            # Sanity Check: Ensure it's actually a video and not an HTML error page
                            ctype = resp.headers.get('Content-Type', '').lower()
                            if 'video' not in ctype and 'application/octet-stream' not in ctype:
                                print(f"Invalid content type {ctype} for {source}")
                                return None

                            tmp_path = os.path.join(tempfile.gettempdir(), f"vid_{uuid.uuid4().hex}.mp4")
                            
                            # Stream the video directly to disk in chunks to save RAM
                            with open(tmp_path, "wb") as f:
                                async for chunk in resp.content.iter_chunked(256 * 1024): # 256KB chunks
                                    f.write(chunk)

                            # Sanity Check: If it's less than 10KB, it's likely a corrupted file or error page
                            if os.path.getsize(tmp_path) < 10240:
                                print(f"Video file too small ({os.path.getsize(tmp_path)} bytes) for {source}")
                                if os.path.exists(tmp_path): os.remove(tmp_path)
                                return None

                            return tmp_path

                    except (asyncio.TimeoutError, aiohttp.ClientError):
                        # network error — exponential backoff and retry
                        print(f"Network error on {source}, retrying in {wait}s (attempt {attempt+1}/{MAX_RETRIES})")
                        await asyncio.sleep(wait)
                        wait *= 2
                        continue

                # all retries exhausted
                print(f"Failed after {MAX_RETRIES} retries: {source}")
                return None
            finally:
                if own_session:
                    await session.close()
        else:
            # local path
            if os.path.exists(source):
                return source
            else:
                raise ValueError(f"Could not find local video file: {source}")
            
    except Exception as e:
        print(f"Error loading video {source}: {e}")
        return None
# IMP: returns path to local video file or None on failure
