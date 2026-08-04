import json
import asyncio
import edge_tts
import os

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

script = data["script"]

# Good, natural-sounding free voice. You can browse more with `edge-tts --list-voices`
VOICE = "en-US-GuyNeural"

async def main():
    communicate = edge_tts.Communicate(script, VOICE)
    await communicate.save("output/voiceover.mp3")
    print("Voiceover saved to output/voiceover.mp3")

asyncio.run(main())
