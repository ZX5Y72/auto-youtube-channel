import json
import os
import requests
import time
import base64
import urllib.parse
 from PIL import Image, ImageEnhance

def fix_brightness_if_dark(path):
    img = Image.open(path).convert("RGB")
    grayscale = img.convert("L")
    avg_brightness = sum(grayscale.getdata()) / (grayscale.width * grayscale.height)
    if avg_brightness < 80:
        boost = 1.6
        img = ImageEnhance.Brightness(img).enhance(boost)
        img.save(path)
        print(f"  Image was too dark (avg {avg_brightness:.0f}), brightened.")
        
with open("output/content.json", "r") as f:
    data = json.load(f)

os.makedirs("output/images", exist_ok=True)

ACCOUNT_ID = os.environ["CF_ACCOUNT_ID"]
API_TOKEN = os.environ["CF_API_TOKEN"]
CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

def try_cloudflare(prompt, path):
    response = requests.post(CF_URL, headers=headers, json={"prompt": prompt}, timeout=60)
    if response.status_code == 200:
        result = response.json()
        image_b64 = result["result"]["image"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(image_b64))
        return True
    else:
        print(f"  Cloudflare failed ({response.status_code}): {response.text[:150]}")
        return False

def try_pollinations(prompt, path):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=90)
    if response.status_code == 200 and len(response.content) > 1000:
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    return False

for i, prompt in enumerate(data["image_prompts"]):
    print(f"Generating image {i+1}/{len(data['image_prompts'])}...")
    path = f"output/images/scene_{i+1}.png"

        success = try_cloudflare(prompt, path)
    if not success:
        print("  Falling back to Pollinations...")
        for attempt in range(3):
            if try_pollinations(prompt, path):
                success = True
                break
            time.sleep(15)
    if success:
        fix_brightness_if_dark(path)
    else:
        print(f"  Both sources failed for image {i+1}, skipping.")

print("All images generated.")
