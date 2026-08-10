import os
import json
import subprocess
import whisper
from llm_utils import call_llm, extract_json

os.makedirs("output", exist_ok=True)

VIDEO_PATH = "output/source_video.mp4"

print("Transcribing source video (this may take a while for long videos)...")
model = whisper.load_model("base")
result = model.transcribe(VIDEO_PATH, word_timestamps=True, verbose=False, language="en")

all_words = []
for seg in result["segments"]:
    for w in seg.get("words", []):
        all_words.append({"index": len(all_words), "text": w["word"].strip(), "start": w["start"], "end": w["end"]})

probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrapper=1:nokey=1", VIDEO_PATH],
    capture_output=True, text=True
)
try:
    actual_duration = float(probe.stdout.strip())
except ValueError:
    actual_duration = all_words[-1]["end"] if all_words else 60

video_duration = actual_duration
print(f"Video duration: {video_duration:.1f}s, total words: {len(all_words)}")

def finalize_clip(start, end, reason, suggested_title):
    with open("output/clip_selection.json", "w") as f:
        json.dump({"start": start, "end": end, "reason": reason, "suggested_title": suggested_title}, f, indent=2)
    os.makedirs("output/clip", exist_ok=True)
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
    result_run = subprocess.run(cmd, capture_output=True, text=True)
    if result_run.returncode != 0:
        print("FFMPEG STDERR:", result_run.stderr[-3000:])
        raise RuntimeError("Failed to cut clip.")
    print("Clip cut and saved to output/clip/raw_clip.mp4")

if len(all_words) < 5:
    print("Very little or no speech detected - using a simple fallback clip instead of AI selection.")
    finalize_clip(0, min(45, video_duration), "No clear speech detected; used the start of the video as a fallback.", "Highlight Clip")
    exit(0)

indexed_transcript = " ".join(f"[{w['index']}] {w['text']}" for w in all_words)
MAX_CHARS = 15000
if len(indexed_transcript) > MAX_CHARS:
    indexed_transcript = indexed_transcript[:MAX_CHARS]

prompt = f"""
Here is a transcript of a video, with each word tagged by its index number in brackets:

{indexed_transcript}

Find the SINGLE most engaging, exciting, funny, or surprising moment in this video that would work well
as a standalone YouTube Short. It should span roughly 100-140 words of speech (about 40-55 seconds) and
capture a complete, self-contained moment with a strong hook near the start, ending on a finished
sentence or complete thought - never cut off mid-sentence.

Respond with ONLY a JSON object with these exact keys:
- "start_word_index": the index number of the first word of the clip (integer, copy it exactly from the brackets)
- "end_word_index": the index number of the last word of the clip (integer, copy it exactly from the brackets)
- "reason": one sentence on why this moment is engaging
- "suggested_title": a punchy short-form title for this clip, under 60 characters

No markdown, no backticks, just the JSON object.
"""

raw_response = call_llm(prompt)

try:
    choice = extract_json(raw_response)
except Exception as e:
    print(f"Could not parse a clip selection from the model ({e}), using fallback.")
    finalize_clip(0, min(45, video_duration), "Model response could not be parsed; used fallback.", "Highlight Clip")
    exit(0)

start_idx = max(0, min(int(choice["start_word_index"]), len(all_words) - 1))
end_idx = max(0, min(int(choice["end_word_index"]), len(all_words) - 1))
if end_idx <= start_idx:
    end_idx = min(start_idx + 150, len(all_words) - 1)

start = all_words[start_idx]["start"]

def find_sentence_boundary(idx, words, min_time, max_time):
    for i in range(idx, len(words)):
        w = words[i]
        if w["end"] < min_time:
            continue
        if w["end"] > max_time:
            break
        if w["text"].rstrip().endswith((".", "!", "?")):
            return i
    return idx

min_end_time = start + 35
max_end_time = start + 55
boundary_idx = find_sentence_boundary(end_idx, all_words, min_end_time, max_end_time)
end = all_words[boundary_idx]["end"]

if end - start > 57:
    end = start + 57
if end > video_duration:
    end = video_duration
if end - start < 20:
    end = min(start + 45, video_duration)

print(f"Selected clip: {start:.1f}s to {end:.1f}s (words {start_idx}-{end_idx}) - {choice.get('reason', '')}")

finalize_clip(start, end, choice.get("reason", ""), choice.get("suggested_title", ""))
