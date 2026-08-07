import json
import asyncio
import edge_tts
import os
import requests

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

script = data["script"]

def try_elevenlabs(text, path):
    API_KEY = os.environ.get("ELEVENLABS_API_KEY")
    if not API_KEY:
        print("No ElevenLabs key found, skipping.")
        return False

    # Rachel - a natural, versatile narration voice on the free tier
    VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"ElevenLabs failed ({response.status_code}): {response.text[:200]}")
            return False
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return False

def use_edge_tts(text, path):
    VOICE = "en-US-GuyNeural"

    async def generate():
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)

    asyncio.run(generate())

output_path = "output/voiceover.mp3"

print("Trying ElevenLabs...")
success = try_elevenlabs(script, output_path)

if not success:
    print("Falling back to edge-tts...")
    use_edge_tts(script, output_path)

print(f"Voiceover saved to {output_path}")
