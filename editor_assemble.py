import os
import subprocess
import whisper

os.makedirs("output", exist_ok=True)

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

cmd = [
    "ffmpeg", "-y",
    "-i", "output/clip/raw_clip.mp4",
    "-i", "branding/editor_watermark.png",
    "-filter_complex",
    "[0:v]ass=output/clip_captions.ass[captioned];"
    "[captioned][1:v]overlay=x=main_w-overlay_w-30:y=40[vout]",
    "-map", "[vout]", "-map", "0:a",
    "-c:v", "libx264", "-c:a", "aac",
    "output/final_clip.mp4"
]
result_run = subprocess.run(cmd, capture_output=True, text=True)
if result_run.returncode != 0:
    print("FFMPEG STDERR:", result_run.stderr[-3000:])
    raise RuntimeError("Failed to assemble final clip.")

print("Final clip assembled: output/final_clip.mp4")
