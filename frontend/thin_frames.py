from PIL import Image
import os

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'
FRAMES = ['frame_event.png', 'frame_schedule.png', 'frame_route.png', 'frame_place.png']
CROP_PCT = 0.12
TARGET_SIZE = (800, 500)

for filename in FRAMES:
    path = os.path.join(FRONTEND_DIR, filename)
    if not os.path.exists(path):
        print(f"Skipping (not found): {filename}")
        continue

    img = Image.open(path)
    w, h = img.size
    cx = int(w * CROP_PCT)
    cy = int(h * CROP_PCT)
    cropped = img.crop((cx, cy, w - cx, h - cy))
    resized = cropped.resize(TARGET_SIZE, Image.LANCZOS)
    resized.save(path)
    print(f"{filename}: {w}x{h} -> cropped {cropped.width}x{cropped.height} -> resized {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")

print("Done.")
