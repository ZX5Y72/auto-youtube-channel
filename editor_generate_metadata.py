import os
import json
import random
from llm_utils import call_llm, extract_json

with open("output/clip_selection.json", "r") as f:
    clip_info = json.load(f)

EDITOR_HASHTAG_FILE = "editor_hashtag_history.json"
if os.path.exists(EDITOR_HASHTAG_FILE):
    with open(EDITOR_HASHTAG_FILE, "r") as f:
        editor_hashtag_history = json.load(f)
else:
    editor_hashtag_history = []

EDITOR_HASHTAG_POOL = [
    "shorts", "viral", "trending", "clips", "highlights", "funny", "gaming",
    "entertainment", "viralvideo", "shortsvideo", "reels", "fyp", "epic", "clutch",
]
creator_handle = os.environ.get("CREATOR_HANDLE", "").strip()
original_link = os.environ.get("ORIGINAL_LINK", "").strip()

prompt = f"""
This is a short clip taken from a longer video by creator {creator_handle}.
The clip is about: {clip_info.get('reason', '')}
Suggested angle: {clip_info.get('suggested_title', '')}

Generate a JSON object with:
- "title": a punchy YouTube Shorts title under 70 characters that includes "{creator_handle}" naturally in it. You may optionally include ONE relevant emoji if it genuinely fits - don't force it
- "description": 2-3 sentences describing the clip, must credit {creator_handle} as the original creator
- "hashtags": array of 6 relevant hashtags (no # symbol), include "shorts"

Return ONLY the JSON object, no markdown, no backticks.
"""

raw_response = call_llm(prompt)
meta = extract_json(raw_response)

recent_used = set(editor_hashtag_history[-14:])
final_hashtags = []
available_pool = [h for h in EDITOR_HASHTAG_POOL if h not in recent_used]
for tag in meta.get("hashtags", []):
    if tag in recent_used and available_pool:
        replacement = random.choice(available_pool)
        available_pool.remove(replacement)
        final_hashtags.append(replacement)
    else:
        final_hashtags.append(tag)
meta["hashtags"] = final_hashtags[:6]

editor_hashtag_history.extend(meta["hashtags"])
editor_hashtag_history = editor_hashtag_history[-50:]
with open(EDITOR_HASHTAG_FILE, "w") as f:
    json.dump(editor_hashtag_history, f, indent=2)

meta["creator_handle"] = creator_handle
meta["original_link"] = original_link

with open("output/clip_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print(json.dumps(meta, indent=2))
