from PIL import Image
import numpy as np
import os

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'
path = os.path.join(FRONTEND_DIR, 'frame_schedule.png')

img = Image.open(path).convert('RGBA')
arr = np.array(img, dtype=np.uint8)

# Mask: pixels where all RGB channels are below 30
black_mask = (arr[:, :, 0] < 30) & (arr[:, :, 1] < 30) & (arr[:, :, 2] < 30)

arr[black_mask, 3] = 0  # set alpha to 0

result = Image.fromarray(arr, 'RGBA')
result.save(path)

total = arr.shape[0] * arr.shape[1]
made_transparent = int(black_mask.sum())
print(f"Made {made_transparent:,} / {total:,} pixels transparent ({made_transparent/total*100:.1f}%)")
print(f"Saved: {path}")
