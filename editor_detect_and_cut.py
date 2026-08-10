import os
import json
import subprocess
import random
import whisper
import cv2
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

def get_source_dimensions():
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", VIDEO_PATH],
        capture_output=True, text=True
    )
    try:
        w, h = probe.stdout.strip().split("x")
        return int(w), int(h)
    except Exception:
        return 1920, 1080

def detect_face_crop_x(start, end):
    """Sample a few frames, look for a face, return a 0-1 fraction for horizontal crop center."""
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    sample_times = [start + (end - start) * frac for frac in (0.25, 0.5, 0.75)]
    x_fractions = []

    for i, t in enumerate(sample_times):
        frame_path = f"output/sample_{i}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(t), "-i", VIDEO_PATH, "-frames:v", "1", frame_path],
            capture_output=True
        )
        if not os.path.exists(frame_path):
            continue
        img = cv2.imread(frame_path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) > 0:
            largest = max(faces, key=lambda f: f[2] * f[3])
            face_x_center = largest[0] + largest[2] / 2
            x_fractions.append(face_x_center / img.shape[1])
        os.remove(frame_path)

    if not x_fractions:
        return None
    return sum(x_fractions) / len(x_fractions)

def finalize_clip(start, end, reason, suggested_title):
    with open("output/clip_selection.json", "w") as f:
        json.dump({"start": start, "end": end, "reason": reason, "suggested_title": suggested_title}, f, indent=2)
    os.makedirs("output/clip", exist_ok=True)

    src_w, src_h = get_source_dimensions()
    is_already_vertical = (src_h / src_w) >= 1.3 if src_w else False

    if is_already_vertical:
        print("Source is already vertical, using a direct scale/crop (no blur-pad needed).")
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        face_x_frac = detect_face_crop_x(start, end)
        if face_x_frac is not None:
            print(f"Face detected, framing tightly around it (x fraction: {face_x_frac:.2f}).")
            crop_x_expr = f"iw*{max(0.0, min(1.0, face_x_frac)):.3f}-ow/2"
            vf = (
                f"scale=-2:1920,crop=1080:1920:x='{crop_x_expr}':y=0"
            )
        else:
            print("No face detected, using blurred-background pad to show the full frame.")
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
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
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

Find the 3 most engaging, exciting, funny, or surprising moments in this video that would each work well
as a standalone YouTube Short. Each should span roughly 100-140 words of speech (about 40-55 seconds) and
capture a complete, self-contained moment with a strong hook near the start, ending on a finished
sentence or complete thought - never cut off mid-sentence.

Respond with ONLY a JSON object with this exact key:
- "candidates": an array of exactly 3 objects, each with "start_word_index", "end_word_index", "reason", "suggested_title", ordered from BEST to worst (best first)

No markdown, no backticks, just the JSON object.
"""

raw_response = call_llm(prompt)

try:
    parsed = extract_json(raw_response)
    candidates = parsed["candidates"]
except Exception as e:
    print(f"Could not parse candidates from the model ({e}), using fallback.")
    finalize_clip(0, min(45, video_duration), "Model response could not be parsed; used fallback.", "Highlight Clip")
    exit(0)

def resolve_candidate(choice):
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

    return start, end

chosen = None
for choice in candidates:
    start, end = resolve_candidate(choice)
    probe = subprocess.run(
        ["ffmpeg", "-i", VIDEO_PATH, "-ss", str(start), "-t", str(end - start),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True
    )
    mean_volume = -100
    for line in probe.stderr.splitlines():
        if "mean_volume" in line:
            try:
                mean_volume = float(line.split(":")[1].replace("dB", "").strip())
            except ValueError:
                pass
    if mean_volume > -40:
        chosen = (start, end, choice)
        break
    else:
        print(f"Candidate rejected (too quiet: {mean_volume}dB), trying next...")

if chosen is None:
    start, end = resolve_candidate(candidates[0])
    chosen = (start, end, candidates[0])

start, end, choice = chosen
print(f"Selected clip: {start:.1f}s to {end:.1f}s - {choice.get('reason', '')}")

finalize_clip(start, end, choice.get("reason", ""), choice.get("suggested_title", ""))
