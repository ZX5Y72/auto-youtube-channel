import os
import json
from groq import Groq

with open("output/clip_selection.json", "r") as f:
    clip_info = json.load(f)

creator_handle = os.environ.get("CREATOR_HANDLE", "").strip()
original_link = os.environ.get("ORIGINAL_LINK", "").strip()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

prompt = f"""
This is a short clip taken from a longer video by creator {creator_handle}.
The clip is about: {clip_info.get('reason', '')}
Suggested angle: {clip_info.get('suggested_title', '')}

Generate a JSON object with:
- "title": a punchy YouTube Shorts title under 70 characters that includes "{creator_handle}" naturally in it
- "description": 2-3 sentences describing the clip, must credit {creator_handle} as the original creator
- "hashtags": array of 6 relevant hashtags (no # symbol), include "shorts"

Return ONLY the JSON object, no markdown, no backticks.
"""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}],
)
text = response.choices[0].message.content.strip()
text = text.replace("```json", "").replace("```", "").strip()
meta = json.loads(text)

meta["creator_handle"] = creator_handle
meta["original_link"] = original_link

with open("output/clip_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print(json.dumps(meta, indent=2))
