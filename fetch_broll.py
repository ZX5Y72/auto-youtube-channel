import json
import os
import requests

with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/broll", exist_ok=True)

API_KEY = os.environ["PIXABAY_API_KEY"]
query = data["civilization"]

url = "https://pixabay.com/api/videos/"
params = {
    "key": API_KEY,
    "q": query,
    "video_type": "film",
    "per_page": 6,
    "safesearch": "true",
}

response = requests.get(url, params=params, timeout=30)
results = response.json()

hits = results.get("hits", [])
print(f"Found {len(hits)} clips for '{query}'")

# Grab up to 2 clips, medium quality (keeps file size reasonable)
downloaded = 0
for hit in hits[:2]:
    video_url = hit["videos"]["medium"]["url"]
    clip_path = f"output/broll/clip_{downloaded+1}.mp4"
    video_data = requests.get(video_url, timeout=60)
    with open(clip_path, "wb") as f:
        f.write(video_data.content)
    downloaded += 1
    print(f"Downloaded {clip_path}")

print(f"B-roll fetch complete: {downloaded} clips")
