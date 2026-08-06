import json
import os
import re
import requests

with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/broll", exist_ok=True)

API_KEY = os.environ["PIXABAY_API_KEY"]

def clean_query(text):
    # Strip parentheticals and non-letter characters, keep it simple
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return text.strip()

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

primary_query = clean_query(data["civilization"])
hits = search_pixabay(primary_query)
print(f"Searched '{primary_query}': {len(hits)} results")

# Fallback: try just the first word (e.g. "Achaemenid Empire" -> "Achaemenid"), then a generic term
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
    video_url = hit["videos"]["medium"]["url"]
    clip_path = f"output/broll/clip_{downloaded+1}.mp4"
    video_data = requests.get(video_url, timeout=60)
    with open(clip_path, "wb") as f:
        f.write(video_data.content)
    downloaded += 1
    print(f"Downloaded {clip_path}")

print(f"B-roll fetch complete: {downloaded} clips")
