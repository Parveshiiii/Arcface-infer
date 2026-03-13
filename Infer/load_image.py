# essentials
import cv2
import numpy as np
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image

#config
import json
with open("config.json") as f:
    cfg = json.load(f)

MAX_RETRIES = cfg['network']['max_retries']
INITIAL_WAIT = cfg['network']['initial_wait_sec']
IMAGE_TIMEOUT = cfg['network']['image_timeout_sec']

async def load_image(source: str, session: aiohttp.ClientSession = None):
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
                        async with session.get(source, timeout=IMAGE_TIMEOUT, headers=headers) as resp:
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

                            content = await resp.read()
                            
                            # Run PIL decoding in thread pool to avoid blocking async event loop
                            loop = asyncio.get_running_loop()
                            def decode_img():
                                img = Image.open(BytesIO(content)).convert("RGB")
                                return np.array(img)[:, :, ::-1]  # RGB to BGR for insightface
                                
                            img = await loop.run_in_executor(None, decode_img)
                            return img

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
            # local path (read in thread pool)
            loop = asyncio.get_running_loop()
            def read_local():
                img = cv2.imread(source)
                if img is None:
                    raise ValueError(f"Could not read image from path: {source}")
                return img
            return await loop.run_in_executor(None, read_local)
            
    except Exception as e:
        print(f"Error loading image {source}: {e}")
        return None
# IMP: returns None on failure
