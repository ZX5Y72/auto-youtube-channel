import os
import json
import subprocess
import whisper
from llm_utils import call_llm, extract_json
from editor_queue_state import load_state, save_state

VIDEO_PATH = "output/source_video.mp4"
MAX_CLIP_DURATION = int(os.environ.get("MAX_CLIP_DURATION", "59"))
MIN_CLIP_DURATION = 20
GAP_BETWEEN_CLIPS = 5

with open("output/queue_context.json", "r") as f:
    ctx = json.load(f)

if ctx["mode"] != "new_video":
    print("Not a new video run, skipping multi-cut.")
    exit(0)

os.makedirs("output/clip", exist_ok=True)

print("Transcribing full source video...")
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
    video_duration = float(probe.stdout.strip())
except ValueError:
    video_duration = all_words[-1]["end"] if all_words else 60

print(f"Video duration: {video_duration:.1f}s, total words: {len(all_words)}")

if len(all_words) < 5 or video_duration < 70:
    print("Too little speech or too short, cutting a single fallback clip.")
    candidates = [{"start_word_index": 0, "end_word_index": min(150, len(all_words) - 1) if all_words else 0,
                   "reason": "Fallback - insufficient speech for AI selection.", "suggested_title": "Highlight Clip"}]
else:
    indexed_transcript = " ".join(f"[{w['index']}] {w['text']}" for w in all_words)
    MAX_CHARS = 15000
    if len(indexed_transcript) > MAX_CHARS:
        indexed_transcript = indexed_transcript[:MAX_CHARS]

    max_possible_clips = max(1, int(video_duration // (MAX_CLIP_DURATION + GAP_BETWEEN_CLIPS)))

    prompt = f"""
Here is a transcript of a video, with each word tagged by its index number in brackets:

{indexed_transcript}

Find up to {max_possible_clips} of the most engaging, exciting, funny, or surprising moments in this video
that would each work well as a standalone YouTube Short. Each should span roughly 100-140 words of speech
(about 40-55 seconds), capture a complete self-contained moment with a strong hook near the start, end on
a finished sentence, and NOT overlap with any other chosen moment. Order candidates by their position in
the video (earliest first).

Respond with ONLY a JSON object with this exact key:
- "candidates": an array of objects, each with "start_word_index", "end_word_index", "reason", "suggested_title"

No markdown, no backticks, just the JSON object.
"""
    raw_response = call_llm(prompt)
    try:
        parsed = extract_json(raw_response)
        candidates = parsed["candidates"]
    except Exception as e:
        print(f"Could not parse candidates ({e}), using single fallback clip.")
        candidates = [{"start_word_index": 0, "end_word_index": min(150, len(all_words) - 1),
                       "reason": "Fallback - could not parse model response.", "suggested_title": "Highlight Clip"}]


def resolve_candidate(choice, last_end):
    start_idx = max(0, min(int(choice["start_word_index"]), len(all_words) - 1))
    end_idx = max(0, min(int(choice["end_word_index"]), len(all_words) - 1))
    if end_idx <= start_idx:
        end_idx = min(start_idx + 150, len(all_words) - 1)

    start = all_words[start_idx]["start"]
    if start < last_end + GAP_BETWEEN_CLIPS:
        start = last_end + GAP_BETWEEN_CLIPS

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
    max_end_time = start + MAX_CLIP_DURATION
    boundary_idx = find_sentence_boundary(end_idx, all_words, min_end_time, max_end_time)
    end = all_words[boundary_idx]["end"]

    if end - start > MAX_CLIP_DURATION:
        end = start + MAX_CLIP_DURATION
    if end > video_duration:
        end = video_duration
    if end - start < MIN_CLIP_DURATION:
        return None

    return start, end


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


src_w, src_h = get_source_dimensions()
is_already_vertical = (src_h / src_w) >= 1.3 if src_w else False

resolved_clips = []
last_end = -GAP_BETWEEN_CLIPS
for choice in candidates:
    resolved = resolve_candidate(choice, last_end)
    if resolved is None:
        continue
    start, end = resolved
    if start >= video_duration - MIN_CLIP_DURATION:
        continue
    resolved_clips.append({"start": start, "end": end, "reason": choice.get("reason", ""),
                            "suggested_title": choice.get("suggested_title", "")})
    last_end = end

if not resolved_clips:
    resolved_clips = [{"start": 0, "end": min(45, video_duration),
                        "reason": "Fallback clip.", "suggested_title": "Highlight Clip"}]

print(f"Cutting {len(resolved_clips)} clip(s)...")

for i, c in enumerate(resolved_clips):
    start, end = c["start"], c["end"]
    out_path = f"output/clip/clip_{i}.mp4"

    if is_already_vertical:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
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
        "-af", "silenceremove=start_periods=1:start_duration=0:start_threshold=-40dB:detection=peak,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-c:a", "aac",
        out_path
    ]
    result_run = subprocess.run(cmd, capture_output=True, text=True)
    if result_run.returncode != 0:
        print(f"FFMPEG STDERR (clip {i}):", result_run.stderr[-2000:])
        continue
    print(f"Cut clip {i}: {start:.1f}s - {end:.1f}s")
    c["index"] = i

resolved_clips = [c for c in resolved_clips if os.path.exists(f"output/clip/clip_{c['index']}.mp4")]

with open("output/clips_meta.json", "w") as f:
    json.dump(resolved_clips, f, indent=2)

os.replace("output/clip/clip_0.mp4", "output/clip/raw_clip.mp4")
with open("output/clip_selection.json", "w") as f:
    json.dump(resolved_clips[0], f, indent=2)

state = load_state()
tag = state["release_tag"]

subprocess.run(["gh", "release", "create", tag, "--title", tag, "--notes", "Editor clip queue storage"],
               capture_output=True, text=True)

subprocess.run(["gh", "release", "upload", tag, "output/clips_meta.json", "--clobber"],
               capture_output=True, text=True)

pending = []
for c in resolved_clips[1:]:
    idx = c["index"]
    subprocess.run(["gh", "release", "upload", tag, f"output/clip/clip_{idx}.mp4", "--clobber"],
                   capture_output=True, text=True)
    pending.append(idx)

state["pending_clip_indices"] = pending
save_state(state)

print(f"Uploaded {len(pending)} clip(s) to release '{tag}' for future days.")
