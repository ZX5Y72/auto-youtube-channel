import os
import requests
import random

os.makedirs("output/sfx", exist_ok=True)

API_KEY = os.environ["FREESOUND_API_KEY"]

SEARCH_TERMS = ["whoosh", "swoosh transition", "impact hit"]

headers = {"Authorization": f"Token {API_KEY}"}

downloaded = 0
for term in SEARCH_TERMS:
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": term,
        "filter": "duration:[0.1 TO 1.5]",  # keep clips short and punchy
        "fields": "id,name,previews",
        "page_size": 10,
    }
    response = requests.get(url, headers=headers, params=params, timeout=30)
    results = response.json().get("results", [])

    if not results:
        print(f"No results for '{term}'")
        continue

    pick = random.choice(results)
    preview_url = pick["previews"]["preview-hq-mp3"]
    audio_data = requests.get(preview_url, timeout=30)

    clip_path = f"output/sfx/{term.replace(' ', '_')}.mp3"
    with open(clip_path, "wb") as f:
        f.write(audio_data.content)

    downloaded += 1
    print(f"Downloaded: {clip_path} (from '{pick['name']}')")

print(f"SFX fetch complete: {downloaded} clips")
