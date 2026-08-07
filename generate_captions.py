import whisper
import json
import os

os.makedirs("output", exist_ok=True)

model = whisper.load_model("base")
result = model.transcribe("output/voiceover_trimmed.mp3", word_timestamps=True)

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
    words = segment.get("words", [])
    for w in words:
        start = format_ass_time(w["start"])
        end = format_ass_time(w["end"])
        text = w["word"].strip().upper()
        # Highlight the active word in yellow, rest hidden (word-by-word pop-in)
        line = f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fscx120\\fscy120}}{text}"
        lines.append(line)

with open("output/captions.ass", "w") as f:
    f.write("\n".join(lines))

print("Word-by-word captions saved to output/captions.ass")
