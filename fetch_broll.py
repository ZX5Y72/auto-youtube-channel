import json
import os
import re
import time
import requests

with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/broll", exist_ok=True)

API_KEY = os.environ["PIXABAY_API_KEY"]

def clean_query(text):
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return text.strip()

def search_pixabay(query, retries=3):
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": API_KEY,
        "q": query,
        "video_type": "film",
        "per_page": 6,
        "safesearch": "true",
        "order": "popular",
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=60)
            return response.json().get("hits", [])
        except Exception as e:
            print(f"  Search attempt {attempt+1} failed: {e}")
            time.sleep(10)
    return []

primary_query = clean_query(data["civilization"])
hits = search_pixabay(primary_query)
print(f"Searched '{primary_query}': {len(hits)} results")

if not hits:
    first_word = primary_query.split()[0] if primary_query else ""
    if first_word:
        hits = search_pixabay(first_word)
        print(f"Fallback search '{first_word}': {len(hits)} results")

if not hits:
    hits = search_pixabay("ancient ruins")
    print(f"Fallback search 'ancient ruins': {len(hits)} results")

downloaded = 0
for hit in hits[:2]:
    try:
        video_url = hit["videos"]["medium"]["url"]
        clip_path = f"output/broll/clip_{downloaded+1}.mp4"
        video_data = requests.get(video_url, timeout=90)
        with open(clip_path, "wb") as f:
            f.write(video_data.content)
        downloaded += 1
        print(f"Downloaded {clip_path}")
    except Exception as e:
        print(f"  Download failed for a clip: {e}")

print(f"B-roll fetch complete: {downloaded} clips")
