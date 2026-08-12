import os
import sys
import re
import requests
import gdown

VIDEO_URL = os.environ["VIDEO_URL"]
os.makedirs("output", exist_ok=True)
path = "output/source_video.mp4"

def extract_drive_file_id(url):
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

if "dropbox.com" in VIDEO_URL and "dl=1" not in VIDEO_URL and "dl=0" in VIDEO_URL:
    VIDEO_URL = VIDEO_URL.replace("dl=0", "dl=1")
    print(f"Adjusted Dropbox link for direct download: {VIDEO_URL}")

if "drive.google.com" in VIDEO_URL:
    file_id = extract_drive_file_id(VIDEO_URL)
    if not file_id:
        print(f"Could not extract a file ID from this Drive link: {VIDEO_URL}")
        sys.exit(1)

    print(f"Detected Google Drive link, file ID: {file_id}")
    gdown.download(id=file_id, output=path, quiet=False)
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
