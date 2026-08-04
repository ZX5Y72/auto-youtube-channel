import json
import os
import requests
import time

with open("output/content.json", "r") as f:
    data = json.load(f)

# Free Hugging Face inference API for Stable Diffusion
API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {os.environ['HF_API_KEY']}"}

os.makedirs("output/images", exist_ok=True)

for i, prompt in enumerate(data["image_prompts"]):
    print(f"Generating image {i+1}/{len(data['image_prompts'])}...")

    for attempt in range(3):
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            with open(f"output/images/scene_{i+1}.png", "wb") as f:
                f.write(response.content)
            break
        else:
            print(f"  Attempt {attempt+1} failed ({response.status_code}), retrying in 20s...")
            time.sleep(20)

print("All images generated.")
