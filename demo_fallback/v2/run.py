from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import shutil
import webbrowser
import threading
import time
import os

PORT = 8765
ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
FRONTEND = REPO_ROOT / "frontend"

ASSET_FILES = [
    "rqtnbrel.png",
    "fanar-badge-charcoal.svg",
    "frame_event.png",
    "frame_schedule.png",
    "frame_route.png",
    "frame_place.png",
]
ASSET_DIRS = ["UI_video"]


def copy_asset(src: Path, dst: Path):
    if not src.exists():
        print(f"asset missing, skipped: {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            return
        shutil.copytree(src, dst)
    elif not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)


def prepare_assets():
    for name in ASSET_FILES:
        copy_asset(FRONTEND / name, ROOT / name)
    for name in ASSET_DIRS:
        copy_asset(FRONTEND / name, ROOT / name)


if __name__ == "__main__":
    prepare_assets()
    os.chdir(ROOT)
    url = f"http://127.0.0.1:{PORT}/index.html"
    threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
    print("Qaarib presentation runtime v2:", url)
    print("Serving from:", ROOT)
    ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler).serve_forever()
