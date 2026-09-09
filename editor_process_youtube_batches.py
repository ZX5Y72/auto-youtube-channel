import os
import json
import subprocess
import whisper
from llm_utils import call_llm, extract_json
from editor_queue_state import load_state, save_state
from youtube_link_utils import download_youtube_video
from editor_batch_prepare import get_source_dimensions, resolve_candidate, MAX_CLIP_DURATION, MIN_CLIP_DURATION, GAP_BETWEEN_CLIPS

os.makedirs("output", exist_ok=True)
os.makedirs("output/clip", exist_ok=True)

state = load_state()
state.setdefault("pending_clips", [])
state.setdefault("video_credits", {})
batches = state.get("youtube_creator_batches", [])

pending_batches = [b for b in batches if b["status"] == "pending"]

if not pending_batches:
    print("No pending YouTube link batches to process.")
    exit(0)

whisper_model = whisper.load_model("base")

for batch in pending_batches:
    creator = batch["creator"]
    print(f"\n=== Processing batch for @{creator} ({len(batch['video_ids'])} videos) ===")
    per_video_clip_lists = []

    for video_id in batch["video_ids"]:
        tag = f"editorqueue-{video_id}"
        video_path = "output/source_video.mp4"

        print(f"\n--- Downloading {video_id} ---")
        try:
            download_youtube_video(video_id, video_path)
        except Exception as e:
            print(f"Download failed for {video_id}: {e}, skipping.")
            continue

        result = whisper_model.transcribe(video_path, word_timestamps=True, verbose=False, language="en")
        all_words = []
        for seg in result["segments"]:
            for w in seg.get("words", []):
                all_words.append({"index": len(all_words), "text": w["word"].strip(), "start": w["start"], "end": w["end"]})

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrapper=1:nokey=1", video_path],
            capture_output=True, text=True
        )
        try:
            video_duration = float(probe.stdout.strip())
        except ValueError:
            video_duration = all_words[-1]["end"] if all_words else 60

        if len(all_words) < 5 or video_duration < 70:
            candidates = [{"start_word_index": 0, "end_word_index": min(150, len(all_words) - 1) if all_words else 0,
                           "reason": "Fallback - insufficient speech for AI selection.", "suggested_title": "Highlight Clip"}]
        else:
            indexed_transcript = " ".join(f"[{w['index']}] {w['text']}" for w in all_words)[:15000]
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

        src_w, src_h = get_source_dimensions(video_path)
        is_already_vertical = (src_h / src_w) >= 1.3 if src_w else False

        resolved_clips = []
        last_end = -GAP_BETWEEN_CLIPS
        for choice in candidates:
            resolved = resolve_candidate(choice, all_words, video_duration, last_end)
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
                "ffmpeg", "-y", "-i", video_path,
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
            c["index"] = i

        resolved_clips = [c for c in resolved_clips if os.path.exists(f"output/clip/clip_{c['index']}.mp4")]
        if not resolved_clips:
            print(f"No clips survived for {video_id}, skipping.")
            os.remove(video_path)
            continue

        with open("output/clips_meta.json", "w") as f:
            json.dump(resolved_clips, f, indent=2)

        subprocess.run(["gh", "release", "create", tag, "--title", tag, "--notes", "Editor clip queue storage"],
                       capture_output=True, text=True)
        subprocess.run(["gh", "release", "upload", tag, "output/clips_meta.json", "--clobber"],
                       capture_output=True, text=True)
        for c in resolved_clips:
            subprocess.run(["gh", "release", "upload", tag, f"output/clip/clip_{c['index']}.mp4", "--clobber"],
                           capture_output=True, text=True)
            os.remove(f"output/clip/clip_{c['index']}.mp4")

        state["video_credits"][video_id] = creator
        per_video_clip_lists.append({
            "video_id": video_id,
            "release_tag": tag,
            "clip_indices": [c["index"] for c in resolved_clips]
        })

        os.remove(video_path)

    round_robin = []
    max_len = max((len(v["clip_indices"]) for v in per_video_clip_lists), default=0)
    for round_num in range(max_len):
        for v in per_video_clip_lists:
            if round_num < len(v["clip_indices"]):
                round_robin.append({
                    "video_id": v["video_id"],
                    "release_tag": v["release_tag"],
                    "clip_index": v["clip_indices"][round_num]
                })

    state["pending_clips"].extend(round_robin)
    batch["status"] = "done"
    print(f"Added {len(round_robin)} clip(s) for @{creator} to the posting queue.")

save_state(state)
print("\nAll pending YouTube batches processed.")
