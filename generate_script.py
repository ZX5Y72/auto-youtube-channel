import google.generativeai as genai
import os
import json
import random

os.makedirs("output", exist_ok=True)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-flash-latest")

HISTORY_FILE = "topic_history.json"
HASHTAG_FILE = "hashtag_history.json"

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
else:
    history = []

if os.path.exists(HASHTAG_FILE):
    with open(HASHTAG_FILE, "r") as f:
        hashtag_history = json.load(f)
else:
    hashtag_history = []

recent_topics = history[-30:]
avoid_list = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "None yet"

HASHTAG_POOL = [
    "history", "ancienthistory", "ancientcivilizations", "historyfacts", "didyouknow",
    "shorts", "learnontiktok", "historylover", "worldhistory", "ancientworld",
    "civilization", "historybuff", "historytok", "factsdaily", "interestingfacts",
    "historicalfacts", "ancientegypt", "romanempire", "greekhistory", "mesopotamia",
    "mayanhistory", "aztechistory", "persianhistory", "chinesehistory", "historyshorts",
    "educational", "learnhistory", "historynerd", "historychannel", "archaeology",
]

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
- "script": a spoken voiceover script. STRICT REQUIREMENT: 100-140 words. The first sentence must be a strong hook (a surprising fact, a question, or a bold claim) - not a generic intro. End with ONE short natural sentence encouraging the viewer to follow for more history content. Conversational tone, no stage directions.
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

# --- Fact-check pass ---
fact_check_prompt = (
    "Review this short history script for factual accuracy about the topic: "
    + data["topic"] + "\n\nScript: \"" + data["script"] + "\"\n\n"
    "If everything is accurate, respond with exactly the word NONE.\n"
    "If there are factual errors, respond with ONLY a corrected version of the "
    "full script (100-140 words, same tone, same structure), nothing else."
)
fact_check_response = model.generate_content(fact_check_prompt)
fact_check_text = fact_check_response.text.strip()
if fact_check_text.upper() != "NONE" and len(fact_check_text) > 20:
    data["script"] = fact_check_text
    print("Fact-check made a correction to the script.")

# --- Multi-candidate hook selection ---
first_sentence = data["script"].split(".")[0]
hook_gen_prompt = (
    "Here is the topic: " + data["topic"] + "\n"
    "Here is the current opening line: \"" + first_sentence + ".\"\n\n"
    "Write 3 alternative opening lines for this script, each under 15 words, "
    "each a different style (a question, a bold claim, a surprising number/fact). "
    "Historically accurate. Number them 1, 2, 3, one per line, no other text."
)
hook_candidates_response = model.generate_content(hook_gen_prompt)
candidates_text = hook_candidates_response.text.strip()

pick_prompt = (
    "Here are 3 candidate opening lines for a history YouTube Short:\n"
    + candidates_text +
    "\n\nWhich one is the most scroll-stopping and curiosity-inducing? "
    "Respond with ONLY the number (1, 2, or 3), nothing else."
)
pick_response = model.generate_content(pick_prompt)
pick_text = pick_response.text.strip()

chosen_hook = None
for line in candidates_text.split("\n"):
    line = line.strip()
    if line.startswith(pick_text[:1]) and len(line) > 2:
        chosen_hook = line.split(".", 1)[-1].strip() if "." in line[:3] else line[2:].strip()
        break

if chosen_hook:
    sentences = data["script"].split(".")
    sentences[0] = chosen_hook.rstrip(".")
    data["script"] = ".".join(sentences).strip()

word_count = len(data["script"].split())
if word_count > 160:
    words = data["script"].split()
    trimmed = " ".join(words[:150])
    last_period = trimmed.rfind(".")
    if last_period > 0:
        trimmed = trimmed[:last_period + 1]
    data["script"] = trimmed
    print(f"Warning: script was {word_count} words, trimmed to fit Shorts length.")

# --- Hashtag rotation ---
recent_used = set(hashtag_history[-18:])
final_hashtags = []
available_pool = [h for h in HASHTAG_POOL if h not in recent_used]
for tag in data.get("hashtags", []):
    if tag in recent_used and available_pool:
        replacement = random.choice(available_pool)
        available_pool.remove(replacement)
        final_hashtags.append(replacement)
    else:
        final_hashtags.append(tag)
data["hashtags"] = final_hashtags[:6]

hashtag_history.extend(data["hashtags"])
hashtag_history = hashtag_history[-60:]
with open(HASHTAG_FILE, "w") as f:
    json.dump(hashtag_history, f, indent=2)

with open("output/content.json", "w") as f:
    json.dump(data, f, indent=2)

history.append(f"{data['civilization']}: {data['topic']}")
with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)

print("Generated content:")
print(json.dumps(data, indent=2))
