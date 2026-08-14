import json
import os
import random

os.makedirs("output", exist_ok=True)

def format_ass_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:01}:{mins:02}:{secs:05.2f}"

COLOR_STYLES = ["&H0000FFFF", "&H00FFFFFF", "&H00FFFF00"]
chosen_color = random.choice(COLOR_STYLES)

FONT_CHOICES = ["Liberation Sans Bold", "DejaVu Sans Bold"]
chosen_font = random.choice(FONT_CHOICES)

ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,90,{chosen_color},{chosen_color},&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

word_boundaries_path = "output/edge_tts_words.json"

if os.path.exists(word_boundaries_path):
    print("Using edge-tts's own word timing, skipping Whisper.")
    with open(word_boundaries_path, "r") as f:
        words = json.load(f)

    lines = [ass_header]
    for w in words:
        start = format_ass_time(w["start"])
        end = format_ass_time(w["end"])
        text = w["text"].strip().upper()
        line = f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fscx120\\fscy120}}{text}"
        lines.append(line)

    with open("output/captions.ass", "w") as f:
        f.write("\n".join(lines))

    with open("output/captions_en.srt", "w") as f:
        f.write("")

    print(f"Word-by-word captions saved from edge-tts timing (color: {chosen_color}).")
else:
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe("output/voiceover_trimmed.mp3", word_timestamps=True)

    lines = [ass_header]
    for segment in result["segments"]:
        for w in segment.get("words", []):
            start = format_ass_time(w["start"])
            end = format_ass_time(w["end"])
            text = w["word"].strip().upper()
            line = f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fscx120\\fscy120}}{text}"
            lines.append(line)

    with open("output/captions.ass", "w") as f:
        f.write("\n".join(lines))

    def format_srt_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

    srt_lines = []
    for i, segment in enumerate(result["segments"], start=1):
        start = format_srt_time(segment["start"])
        end = format_srt_time(segment["end"])
        text = segment["text"].strip()
        srt_lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    with open("output/captions_en.srt", "w") as f:
        f.write("\n".join(srt_lines))

    print(f"Word-by-word captions saved via Whisper (color: {chosen_color}).")
