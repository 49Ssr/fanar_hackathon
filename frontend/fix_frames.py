from PIL import Image, ImageDraw
import os

FRONTEND_DIR = r'C:\Users\uniou\OneDrive - University of Brighton\Desktop\hackathon\frontend'

# ── frame_route.png: flood-fill light center with dark green ──
route_path = os.path.join(FRONTEND_DIR, 'frame_route.png')
img = Image.open(route_path).convert('RGB')
cx, cy = img.width // 2, img.height // 2
center_pixel = img.getpixel((cx, cy))
print(f"frame_route.png center pixel at ({cx},{cy}): {center_pixel}")

# Fill from center outward with dark green, tolerance 80
ImageDraw.floodfill(img, (cx, cy), (10, 30, 10), thresh=80)

# Also try a few other interior points in case center didn't catch everything
for offset in [(0, -50), (0, 50), (-50, 0), (50, 0), (-80, -80), (80, 80), (-80, 80), (80, -80)]:
    px, py = cx + offset[0], cy + offset[1]
    if 0 <= px < img.width and 0 <= py < img.height:
        p = img.getpixel((px, py))
        # Only fill if still light (not already dark green or part of the frame)
        if p[0] > 60 or p[1] > 60 or p[2] > 60:
            ImageDraw.floodfill(img, (px, py), (10, 30, 10), thresh=80)

img.save(route_path)
print(f"Saved: {route_path}")

# ── frame_schedule.png: flood-fill white/light areas with black ──
sched_path = os.path.join(FRONTEND_DIR, 'frame_schedule.png')
img2 = Image.open(sched_path).convert('RGB')
cx2, cy2 = img2.width // 2, img2.height // 2
center_pixel2 = img2.getpixel((cx2, cy2))
print(f"frame_schedule.png center pixel at ({cx2},{cy2}): {center_pixel2}")

# Fill center interior
ImageDraw.floodfill(img2, (cx2, cy2), (0, 0, 0), thresh=60)

# Fill from corners to catch exterior white areas
corners = [(2, 2), (img2.width - 3, 2), (2, img2.height - 3), (img2.width - 3, img2.height - 3)]
for cx_c, cy_c in corners:
    p = img2.getpixel((cx_c, cy_c))
    if p[0] > 60 or p[1] > 60 or p[2] > 60:
        ImageDraw.floodfill(img2, (cx_c, cy_c), (0, 0, 0), thresh=60)

img2.save(sched_path)
print(f"Saved: {sched_path}")

print("Done.")
