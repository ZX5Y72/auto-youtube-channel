import os
import json
import subprocess
import whisper
import google.generativeai as genai

os.makedirs("output", exist_ok=True)

VIDEO_PATH = "output/source_video.mp4"

print("Transcribing source video (this may take a while for long videos)...")
model = whisper.load_model("base")
result = model.transcribe(VIDEO_PATH, verbose=False)

segments = result["segments"]
transcript_lines = []
for seg in segments:
    transcript_lines.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text'].strip()}")
full_transcript = "\n".join(transcript_lines)

MAX_CHARS = 15000
if len(full_transcript) > MAX_CHARS:
    full_transcript = full_transcript[:MAX_CHARS] + "\n...[transcript truncated]"

video_duration = segments[-1]["end"] if segments else 0
print(f"Video duration: {video_duration:.1f}s, transcript length: {len(full_transcript)} chars")

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model_g = genai.GenerativeModel("gemini-flash-latest")

prompt = f"""
Here is a timestamped transcript of a video (total duration {video_duration:.0f} seconds):

{full_transcript}

Find the SINGLE most engaging, exciting, funny, or surprising moment in this video that would work well
as a standalone YouTube Short. It must be at least 60 seconds long and ideally under 90 seconds.
Pick a start and end timestamp (in seconds) that captures a complete, self-contained moment - not cut
off mid-sentence or mid-joke. The clip should have a strong hook in its first few seconds.

Respond with ONLY a JSON object with these exact keys:
- "start": start time in seconds (number)
- "end": end time in seconds (number, must be at least 60 seconds after start)
- "reason": one sentence on why this moment is engaging
- "suggested_title": a punchy short-form title for this clip, under 60 characters

No markdown, no backticks, just the JSON object.
"""

response = model_g.generate_content(prompt)
text = response.text.strip().replace("```json", "").replace("```", "").strip()
choice = json.loads(text)

start = float(choice["start"])
end = float(choice["end"])

if end - start < 60:
    end = start + 60
if end > video_duration:
    end = video_duration
    start = max(0, end - 60)

print(f"Selected clip: {start:.1f}s to {end:.1f}s - {choice.get('reason', '')}")

with open("output/clip_selection.json", "w") as f:
    json.dump({"start": start, "end": end, "reason": choice.get("reason", ""),
               "suggested_title": choice.get("suggested_title", "")}, f, indent=2)

probe = subprocess.run(
    ["ffmpeg", "-i", VIDEO_PATH, "-ss", str(start), "-t", str(end - start),
     "-af", "volumedetect", "-f", "null", "-"],
    capture_output=True, text=True
)
print("Audio level check:")
for line in probe.stderr.splitlines():
    if "mean_volume" in line or "max_volume" in line:
        print(" ", line.strip())

os.makedirs("output/clip", exist_ok=True)
cmd = [
    "ffmpeg", "-y", "-i", VIDEO_PATH,
    "-ss", str(start), "-t", str(end - start),
    "-vf", "scale=-2:1920,crop=1080:1920",
    "-c:v", "libx264", "-c:a", "aac",
    "output/clip/raw_clip.mp4"
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FFMPEG STDERR:", result.stderr[-3000:])
    raise RuntimeError("Failed to cut clip.")

print("Clip cut and saved to output/clip/raw_clip.mp4")
