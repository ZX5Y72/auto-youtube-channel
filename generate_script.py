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

recent_topics = history[-30:]
avoid_list = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "None yet"

TOPIC_PROMPT = f"""
You create scripts for a YouTube Shorts channel about ancient history and civilizations
(e.g. Ancient Egypt, Rome, Greece, Mesopotamia, the Maya, etc).

Pick ONE specific, interesting, and historically ACCURATE fact or story from a civilization
that hasn't gotten overused/clickbaited-to-death. Prefer specific, verifiable details over vague claims.

IMPORTANT: Do NOT repeat or closely resemble any of these already-used topics:
{avoid_list}

Generate a single JSON object with these exact keys:

- "civilization": the civilization this is about
- "topic": the specific fact/story you picked
- "hook_text": a SHORT punchy on-screen text (3-6 words, no punctuation needed), a bold statement or question that creates instant curiosity, shown as a flash graphic before the video even starts talking
- "script": a spoken voiceover script. STRICT REQUIREMENT: 100-140 words. The first sentence must be a strong hook (a surprising fact, a question, or a bold claim) - not a generic intro. End with ONE short natural sentence encouraging the viewer to follow for more history content (e.g. "Follow for more forgotten history" - vary the phrasing, keep it casual not salesy). Conversational tone, no stage directions.
- "title": a catchy YouTube Shorts title, under 60 characters
- "description": a 2-3 sentence description, mention it's part of a history series
- "hashtags": an array of 6 relevant hashtags (no # symbol)
- "image_prompts": an array of 8-10 image generation prompts, one for roughly every 1.5-2 seconds of the script, visually distinct from each other. EACH prompt must end with this exact style suffix: ", digital illustration, painterly animated style, warm muted color palette, dramatic lighting, detailed historical accuracy, no text, no watermark"

Return ONLY the JSON object, no markdown formatting, no backticks, no extra text.
"""

response = model.generate_content(TOPIC_PROMPT)
text = response.text.strip()
text = text.replace("```json", "").replace("```", "").strip()
data = json.loads(text)

# Self-critique pass: rewrite the hook specifically for maximum punch
CRITIQUE_PROMPT = f"""
Here is the opening line of a YouTube Shorts script: "{data['script'].split('.')[0]}."

Rewrite ONLY this opening line to be as scroll-stopping and curiosity-inducing as possible.
Rules: under 15 words, no generic phrases like "did you know", must create an open question in the viewer's mind, historically accurate, matches this topic: {data['topic']}.

Return ONLY the rewritten sentence, nothing else, no quotation marks.
"""
critique_response = model.generate_content(CRITIQUE_PROMPT)
new_hook = critique_response.text.strip().strip('"')

original_sentences = data["script"].split(".")
original_sentences[0] = new_hook.rstrip(".")
data["script"] = ".".join(original_sentences).strip()

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

history.append(f"{data['civilization']}: {data['topic']}")
with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)

print("Generated content:")
print(json.dumps(data, indent=2))
