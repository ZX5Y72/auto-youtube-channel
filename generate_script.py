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

performance_context = ""
if os.path.exists("video_performance.json"):
    with open("video_performance.json", "r") as f:
        perf_data = json.load(f)
    if perf_data:
        top_performers = perf_data[:5]
        performance_lines = "\n".join(
            f"- \"{v['title']}\" ({v['views']} views, {v['avg_view_percentage']:.0f}% avg watched)"
            for v in top_performers
        )
        performance_context = f"""

Here is how your recent videos have performed (best performing first):
{performance_lines}

Use this to inform your topic choice: if certain civilizations, angles, or
