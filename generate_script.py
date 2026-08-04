import google.generativeai as genai
import os
import json

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-flash-latest")

TOPIC_PROMPT = """
You create scripts for a YouTube Shorts channel about ancient history and civilizations
(e.g. Ancient Egypt, Rome, Greece, Mesopotamia, the Maya, etc).

Pick ONE specific, interesting, and historically ACCURATE fact or story from a civilization
that hasn't gotten overused/clickbaited-to-death. Prefer specific, verifiable details over vague claims.

Generate a single JSON object with these exact keys:

- "civilization": the civilization this is about
- "topic": the specific fact/story you picked
- "script": a spoken voiceover script, 100-140 words (must fit in ~45-55 seconds spoken), hook in the first line, conversational tone, no stage directions
- "title": a catchy YouTube Shorts title, under 60 characters
- "description": a 2-3 sentence description, mention it's part of a history series
- "hashtags": an array of 6 relevant hashtags (no # symbol), mix broad (history, ancienthistory) and specific (e.g. ancientegypt, romanempire)
- "image_prompts": an array of 4-6 image generation prompts, one per key visual beat of the script, EACH prompt must end with this exact style suffix: ", digital illustration, painterly animated style, warm muted color palette, dramatic lighting, detailed historical accuracy, no text, no watermark"

Return ONLY the JSON object, no markdown formatting, no backticks, no extra text.
"""

response = model.generate_content(TOPIC_PROMPT)
text = response.text.strip()
text = text.replace("```json", "").replace("```", "").strip()

data = json.loads(text)

with open("output/content.json", "w") as f:
    json.dump(data, f, indent=2)

print("Generated content:")
print(json.dumps(data, indent=2))
