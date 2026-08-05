import json
import os
import requests
import time

with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/images", exist_ok=True)

ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
API_TOKEN = os.environ["CF_API_TOKEN"]
API_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

for i, prompt in enumerate(data["image_prompts"]):
    print(f"Generating image {i+1}/{len(data['image_prompts'])}...")

    for attempt in range(3):
        response = requests.post(API_URL, headers=headers, json={"prompt": prompt}, timeout=60)
        if response.status_code == 200:
            result = response.json()
            import base64
            image_b64 = result["result"]["image"]
            with open(f"output/images/scene_{i+1}.png", "wb") as f:
                f.write(base64.b64decode(image_b64))
            break
        else:
            print(f"  Attempt {attempt+1} failed ({response.status_code}): {response.text[:200]}")
            time.sleep(10)

print("All images generated.")
