import google.generativeai as genai
import os
import json

os.makedirs("output", exist_ok=True)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-flash-latest")

HISTORY_FILE = "topic_history.json"

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = []

# Only show the last 30 to keep the prompt from growing forever
recent_topics = history[-30:]
avoid_list = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "None yet"

TOPIC_PROMPT = f"""
You create scripts for a YouTube Shorts channel about ancient history and civilizations
(e.g. Ancient Egypt, Rome, Greece, Mesopotamia, the Maya, etc).

Pick ONE specific, interesting, and historically ACCURATE fact or story from a civilization
that hasn't gotten overused/clickbaited-to-death. Prefer specific, verifiable details over vague claims.

IMPORTANT: Do NOT repeat or closely resemble any of these already-used topics:
{avoid_list}

Pick something genuinely different from all of the above — a different civilization, era, or angle.

Generate a single JSON object with these exact keys:

- "civilization": the civilization this is about
- "topic": the specific fact/story you picked
- "script": a spoken voiceover script. STRICT REQUIREMENT: it must be between 100 and 140 words, no more, no less. Count your words before responding. This is for a 45-55 second YouTube Short and going over will break the video. Hook in the first line, conversational tone, no stage directions.
- "title": a catchy YouTube Shorts title, under 60 characters
- "description": a 2-3 sentence description, mention it's part of a history series
- "hashtags": an array of 6 relevant hashtags (no # symbol), mix broad (history, ancienthistory) and specific (e.g. ancientegypt, romanempire)
- "image_prompts": an array of 8-10 image generation prompts, one for roughly every 1.5-2 seconds of the script (a new visual should appear on almost every sentence or major phrase, not one image per whole idea). Make each prompt visually distinct from the others — different camera angle, different moment, different character/detail — so consecutive images don't look repetitive. EACH prompt must end with this exact style suffix: ", digital illustration, painterly animated style, warm muted color palette, dramatic lighting, detailed historical accuracy, no text, no watermark"

Return ONLY the JSON object, no markdown formatting, no backticks, no extra text.
"""

response = model.generate_content(TOPIC_PROMPT)
text = response.text.strip()
text = text.replace("```json", "").replace("```", "").strip()

data = json.loads(text)

word_count = len(data["script"].split())
if word_count > 160:
    words = data["script"].split()
    trimmed = " ".join(words[:150])
    last_period = trimmed.rfind(".")
    if last_period > 0:
        trimmed = trimmed[:last_period + 1]
    data["script"] = trimmed
    print(f"Warning: script was {word_count} words, trimmed to fit Shorts length.")

with open("output/content.json", "w") as f:
    json.dump(data, f, indent=2)

# Add this topic to history for next time
history.append(f"{data['civilization']}: {data['topic']}")
with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)

print("Generated content:")
print(json.dumps(data, indent=2))
