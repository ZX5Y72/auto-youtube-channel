import json
import os
import requests
import time
import urllib.parse

with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/images", exist_ok=True)

for i, prompt in enumerate(data["image_prompts"]):
    print(f"Generating image {i+1}/{len(data['image_prompts'])}...")

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    for attempt in range(3):
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            with open(f"output/images/scene_{i+1}.png", "wb") as f:
                f.write(response.content)
            break
        else:
            print(f"  Attempt {attempt+1} failed ({response.status_code}), retrying in 15s...")
            time.sleep(15)

    time.sleep(15)  # respect the ~1 request per 15s anonymous rate limit

print("All images generated.")
