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
