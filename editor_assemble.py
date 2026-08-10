import os
import json
import subprocess
import whisper

os.makedirs("output", exist_ok=True)

with open("output/clip_selection.json", "r") as f:
    clip_info = json.load(f)
clip_duration = clip_info["end"] - clip_info["start"]

model = whisper.load_model("base")
result = model.transcribe("output/clip/raw_clip.mp4", word_timestamps=True)

def format_ass_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:01}:{mins:02}:{secs:05.2f}"

ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,90,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [ass_header]
for segment in result["segments"]:
    for w in segment.get("words", []):
        start = format_ass_time(w["start"])
        end = format_ass_time(w["end"])
        text = w["word"].strip().upper()
        line = f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fscx120\\fscy120}}{text}"
        lines.append(line)

with open("output/clip_captions.ass", "w") as f:
    f.write("\n".join(lines))

import random as rnd

CTA_PAIRS = [
    ("Full video linked below!", "Follow for more clips!"),
    ("Watch the full clip below!", "Subscribe for daily highlights!"),
    ("Link to the full video below!", "Follow for more like this!"),
]
cta_line1, cta_line2 = rnd.choice(CTA_PAIRS)

cta_start = max(0, clip_duration - 3)
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

drawtext_cta = (
    f"drawtext=fontfile={font_path}:text='{cta_line1}\\!':"
    f"fontsize=48:fontcolor=white:borderw=3:bordercolor=black:"
    f"x=(w-text_w)/2:y=150:enable='between(t\\,{cta_start}\\,{clip_duration})',"
    f"drawtext=fontfile={font_path}:text='{cta_line2}\\!':"
    f"fontsize=48:fontcolor=yellow:borderw=3:bordercolor=black:"
    f"x=(w-text_w)/2:y=220:enable='between(t\\,{cta_start}\\,{clip_duration})'"
)
cmd = [
    "ffmpeg", "-y",
    "-i", "output/clip/raw_clip.mp4",
    "-i", "branding/editor_watermark.png",
    "-filter_complex",
    f"[0:v]ass=output/clip_captions.ass,{drawtext_cta}[captioned];"
    "[captioned][1:v]overlay=x=main_w-overlay_w-30:y=40,scale=1080:1920:force_original_aspect_ratio=disable,setsar=1[vout]",
    "-map", "[vout]", "-map", "0:a",
    "-metadata:s:v:0", "rotate=0",
    "-c:v", "libx264", "-c:a", "aac",
    "output/final_clip.mp4"
]
result_run = subprocess.run(cmd, capture_output=True, text=True)
if result_run.returncode != 0:
    print("FFMPEG STDERR:", result_run.stderr[-3000:])
    raise RuntimeError("Failed to assemble final clip.")

print("Final clip assembled: output/final_clip.mp4")
