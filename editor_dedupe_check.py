import os
import json
import hashlib
import subprocess

SEEN_FILE = "editor_seen_videos.json"
original_link = os.environ.get("ORIGINAL_LINK", "").strip()
link_hash = hashlib.sha256(original_link.encode()).hexdigest()

seen = []
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        seen = json.load(f)

github_output = os.environ.get("GITHUB_OUTPUT")

video_url = os.environ.get("VIDEO_URL", "")

if link_hash in seen:
    print(f"This original video has already been clipped before, skipping: {original_link}")
    if github_output:
        with open(github_output, "a") as f:
            f.write("skip=true\n")
else:
    seen.append(link_hash)
    seen = seen[-200:]
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)
    print(f"New source video, proceeding: {original_link}")
    if github_output:
        with open(github_output, "a") as f:
            f.write("skip=false\n")
