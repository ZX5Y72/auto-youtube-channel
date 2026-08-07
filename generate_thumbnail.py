import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

with open("output/content.json", "r") as f:
    data = json.load(f)

base = Image.open("output/images/scene_1.png").convert("RGB")
base = base.resize((1280, 720))
draw = ImageDraw.Draw(base)

overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
overlay_draw.rectangle([0, 450, 1280, 720], fill=(0, 0, 0, 150))
base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
draw = ImageDraw.Draw(base)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
except:
    font = ImageFont.load_default()

title_text = data["civilization"].upper()
draw.text((50, 500), title_text, font=font, fill="white")

bordered = ImageOps.expand(base, border=12, fill=(255, 200, 0))
bordered = bordered.resize((1280, 720))
bordered.save("output/thumbnail.jpg", quality=95)
print("Thumbnail saved to output/thumbnail.jpg")
