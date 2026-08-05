import whisper
import json
import os

os.makedirs("output", exist_ok=True)

model = whisper.load_model("base")
result = model.transcribe("output/voiceover.mp3", word_timestamps=False)

# Write an SRT subtitle file
def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"

with open("output/captions.srt", "w") as f:
    for i, segment in enumerate(result["segments"], start=1):
        start = format_timestamp(segment["start"])
        end = format_timestamp(segment["end"])
        text = segment["text"].strip()
        f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

print("Captions saved to output/captions.srt")
