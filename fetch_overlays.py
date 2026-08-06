import os
import requests
import random

os.makedirs("output/overlays_fetched", exist_ok=True)

API_KEY = os.environ["PIXABAY_API_KEY"]

SEARCH_TERMS = ["dust particles", "embers fire", "fog atmosphere"]

def search_pixabay(query):
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": API_KEY,
        "q": query,
        "video_type": "film",
        "per_page": 6,
        "safesearch": "true",
        "order": "popular",
    }
    response = requests.get(url, params=params, timeout=30)
    return response.json().get("hits", [])

term = random.choice(SEARCH_TERMS)
hits = search_pixabay(term)
print(f"Searched '{term}': {len(hits)} results")

if not hits:
    hits = search_pixabay("particles")
    print(f"Fallback 'particles': {len(hits)} results")

downloaded = 0
if hits:
    pick = random.choice(hits[:5])
    video_url = pick["videos"]["medium"]["url"]
    clip_path = "output/overlays_fetched/overlay.mp4"
    video_data = requests.get(video_url, timeout=60)
    with open(clip_path, "wb") as f:
        f.write(video_data.content)
    downloaded = 1
    print(f"Downloaded overlay: {clip_path}")

print(f"Overlay fetch complete: {downloaded} clip")
