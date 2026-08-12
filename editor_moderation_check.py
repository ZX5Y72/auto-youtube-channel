import os
import json
import sys
from llm_utils import call_llm, extract_json

with open("output/clip_selection.json", "r") as f:
    clip_info = json.load(f)

prompt = f"""
A short video clip was selected with this description: "{clip_info.get('reason', '')}"
Title idea: "{clip_info.get('suggested_title', '')}"

Is there anything here suggesting graphic violence, hate speech, sexual content, self-harm,
dangerous acts, or other content clearly inappropriate for a general-audience YouTube channel?

Respond with ONLY a JSON object: {{"safe": true or false, "reason": "brief explanation"}}
No markdown, no backticks.
"""

try:
    raw = call_llm(prompt)
    result = extract_json(raw)
except Exception as e:
    print(f"Moderation check failed to run ({e}), defaulting to safe (fail-open with logging).")
    result = {"safe": True, "reason": "check unavailable"}

print(f"Moderation result: {result}")

github_output = os.environ.get("GITHUB_OUTPUT")
if not result.get("safe", True):
    print(f"FLAGGED: {result.get('reason', '')}")
    if github_output:
        with open(github_output, "a") as f:
            f.write("flagged=true\n")
else:
    if github_output:
        with open(github_output, "a") as f:
            f.write("flagged=false\n")
