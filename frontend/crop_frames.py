from PIL import Image
import numpy as np
import os

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'
FRAMES = ['frame_event.png', 'frame_schedule.png', 'frame_route.png', 'frame_place.png']

THRESHOLD = 20  # pixels with any channel above this are considered non-black

for filename in FRAMES:
    path = os.path.join(FRONTEND_DIR, filename)
    if not os.path.exists(path):
        print(f"Skipping (not found): {filename}")
        continue

    img = Image.open(path).convert('RGB')
    arr = np.array(img)

    # Mask: pixels where any channel exceeds threshold
    mask = arr.max(axis=2) > THRESHOLD

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any():
        print(f"No non-black pixels found in {filename}, skipping.")
        continue

    top    = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left   = int(np.argmax(cols))
    right  = int(len(cols) - np.argmax(cols[::-1]))

    cropped = img.crop((left, top, right, bottom))
    cropped.save(path)
    print(f"{filename}: ({img.width}x{img.height}) -> cropped to ({cropped.width}x{cropped.height}), box=({left},{top},{right},{bottom})")

print("Done.")
