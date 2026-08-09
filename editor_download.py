import os
import requests
import sys

VIDEO_URL = os.environ["VIDEO_URL"]

os.makedirs("output", exist_ok=True)
path = "output/source_video.mp4"

print(f"Downloading source video from {VIDEO_URL}...")
with requests.get(VIDEO_URL, stream=True, timeout=300) as r:
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

size = os.path.getsize(path)
print(f"Downloaded {size} bytes to {path}")
if size < 10000:
    print("Downloaded file looks too small, aborting.")
    sys.exit(1)
