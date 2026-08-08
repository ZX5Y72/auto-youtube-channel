import json
import asyncio
import edge_tts
import os
import requests
import random

os.makedirs("output", exist_ok=True)

with open("output/content.json", "r") as f:
    data = json.load(f)

script = data["script"]

def get_available_voice_id(api_key):
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": api_key}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return None
        voices = response.json().get("voices", [])
        for v in voices:
            if v.get("category") in ("premade", "cloned", "generated_by_user"):
                return v["voice_id"]
        return voices[0]["voice_id"] if voices else None
    except Exception as e:
        print(f"Voice list fetch failed: {e}")
        return None

def try_elevenlabs(text, path):
    API_KEY = os.environ.get("ELEVENLABS_API_KEY")
    if not API_KEY:
        print("No ElevenLabs key found, skipping.")
        return False
    voice_id = get_available_voice_id(API_KEY)
    if not voice_id:
        print("No usable ElevenLabs voice found on this account.")
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text, "model_id": "eleven_multilingual_v2",
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
    rate = random.choice(["-5%", "+0%", "+5%", "+8%"])
    pitch = random.choice(["-3Hz", "+0Hz", "+3Hz"])

    async def generate():
        communicate = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch)
        await communicate.save(path)

    asyncio.run(generate())
    print(f"edge-tts used rate={rate}, pitch={pitch}")

output_path = "output/voiceover.mp3"

print("Trying ElevenLabs...")
success = try_elevenlabs(script, output_path)

if not success:
    print("Falling back to edge-tts...")
    use_edge_tts(script, output_path)

print(f"Voiceover saved to {output_path}")
