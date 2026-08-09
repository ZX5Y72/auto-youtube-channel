import os
import json
import subprocess
import whisper
import google.generativeai as genai

os.makedirs("output", exist_ok=True)

VIDEO_PATH = "output/source_video.mp4"

print("Transcribing source video (this may take a while for long videos)...")
model = whisper.load_model("base")
result = model.transcribe(VIDEO_PATH, word_timestamps=True, verbose=False)

all_words = []
for seg in result["segments"]:
    for w in seg.get("words", []):
        all_words.append({"index": len(all_words), "text": w["word"].strip(), "start": w["start"], "end": w["end"]})

video_duration = all_words[-1]["end"] if all_words else 0
print(f"Video duration: {video_duration:.1f}s, total words: {len(all_words)}")

indexed_transcript = " ".join(f"[{w['index']}] {w['text']}" for w in all_words)
MAX_CHARS = 15000
if len(indexed_transcript) > MAX_CHARS:
    indexed_transcript = indexed_transcript[:MAX_CHARS]

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model_g = genai.GenerativeModel("gemini-flash-latest")

prompt = f"""
Here is a transcript of a video, with each word tagged by its index number in brackets:

{indexed_transcript}

Find the SINGLE most engaging, exciting, funny, or surprising moment in this video that would work well
as a standalone YouTube Short. It should span at least 150 words of speech (roughly 60+ seconds) and
capture a complete, self-contained moment with a strong hook near the start - not cut off mid-sentence.

Respond with ONLY a JSON object with these exact keys:
- "start_word_index": the index number of the first word of the clip (integer, copy it exactly from the brackets)
- "end_word_index": the index number of the last word of the clip (integer, copy it exactly from the brackets)
- "reason": one sentence on why this moment is engaging
- "suggested_title": a punchy short-form title for this clip, under 60 characters

No markdown, no backticks, just the JSON object.
"""

response = model_g.generate_content(prompt)
text = response.text.strip().replace("```json", "").replace("```", "").strip()
choice = json.loads(text)

start_idx = max(0, min(int(choice["start_word_index"]), len(all_words) - 1))
end_idx = max(0, min(int(choice["end_word_index"]), len(all_words) - 1))
if end_idx <= start_idx:
    end_idx = min(start_idx + 150, len(all_words) - 1)

start = all_words[start_idx]["start"]
end = all_words[end_idx]["end"]

if end - start < 60:
    end = min(start + 60, video_duration)
if end - start < 60:
    start = max(0, end - 60)

print(f"Selected clip: {start:.1f}s to {end:.1f}s (words {start_idx}-{end_idx}) - {choice.get('reason', '')}")

with open("output/clip_selection.json", "w") as f:
    json.dump({"start": start, "end": end, "reason": choice.get("reason", ""),
               "suggested_title": choice.get("suggested_title", "")}, f, indent=2)

os.makedirs("output/clip", exist_ok=True)

# Proper vertical reframe: show the WHOLE original frame, fill empty space with a
# blurred zoomed copy of itself - instead of destructively cropping away content.
vf = (
    "split[bg][fg];"
    "[bg]scale=1080:1920,gblur=sigma=30[bg];"
    "[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
    "[bg][fg]overlay=(W-w)/2:(H-h)/2"
)

cmd = [
    "ffmpeg", "-y", "-i", VIDEO_PATH,
    "-ss", str(start), "-t", str(end - start),
    "-vf", vf,
    "-c:v", "libx264", "-c:a", "aac",
    "output/clip/raw_clip.mp4"
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FFMPEG STDERR:", result.stderr[-3000:])
    raise RuntimeError("Failed to cut clip.")

print("Clip cut and saved to output/clip/raw_clip.mp4")
