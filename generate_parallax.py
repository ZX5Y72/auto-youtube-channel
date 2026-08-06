import os
from rembg import remove
from PIL import Image

IMAGES_DIR = "output/images"
OUT_DIR = "output/images_parallax"
os.makedirs(OUT_DIR, exist_ok=True)

image_files = sorted(f for f in os.listdir(IMAGES_DIR) if f.endswith(".png"))

for fname in image_files:
    path = os.path.join(IMAGES_DIR, fname)
    base = os.path.splitext(fname)[0]

    try:
        with open(path, "rb") as f:
            input_bytes = f.read()

        fg_bytes = remove(input_bytes)
        fg_path = os.path.join(OUT_DIR, f"{base}_fg.png")
        with open(fg_path, "wb") as f:
            f.write(fg_bytes)

        bg_img = Image.open(path).convert("RGB")
        bg_path = os.path.join(OUT_DIR, f"{base}_bg.png")
        bg_img.save(bg_path)

        print(f"Parallax layers created for {fname}")
    except Exception as e:
        print(f"Parallax failed for {fname}: {e}")

print("Parallax processing complete.")
