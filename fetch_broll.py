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
        "key": API_KEY, "q": query, "video_type": "film",
        "per_page": 6, "safesearch": "true", "order": "popular",
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=60)
            return response.json().get("hits", [])
        except Exception as e:
            print(f"  Search attempt {attempt+1} failed: {e}")
            time.sleep(10)
    return []

civilization_q = clean_query(data["civilization"])
topic_words = clean_query(data.get("topic", "")).split()
topic_q = " ".join(topic_words[:3])

hits = search_pixabay(f"{civilization_q} {topic_q}".strip())
print(f"Searched '{civilization_q} {topic_q}': {len(hits)} results")

if not hits:
    hits = search_pixabay(civilization_q)
    print(f"Fallback '{civilization_q}': {len(hits)} results")

if not hits:
    first_word = civilization_q.split()[0] if civilization_q else ""
    if first_word:
        hits = search_pixabay(first_word)
        print(f"Fallback '{first_word}': {len(hits)} results")

if not hits:
    hits = search_pixabay("ancient ruins")
    print(f"Fallback 'ancient ruins': {len(hits)} results")

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
        print(f"  Download failed: {e}")

print(f"B-roll fetch complete: {downloaded} clips")
