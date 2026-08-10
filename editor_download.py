import os
import sys
import requests
import gdown

VIDEO_URL = os.environ["VIDEO_URL"]
os.makedirs("output", exist_ok=True)
path = "output/source_video.mp4"

if "drive.google.com" in VIDEO_URL:
    print("Detected Google Drive link, using gdown...")
    gdown.download(url=VIDEO_URL, output=path, quiet=False, fuzzy=True)
else:
    print(f"Downloading directly from {VIDEO_URL}...")
    with requests.get(VIDEO_URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

if not os.path.exists(path) or os.path.getsize(path) < 10000:
    print("Downloaded file missing or too small, aborting.")
    sys.exit(1)

print(f"Downloaded {os.path.getsize(path)} bytes to {path}")
