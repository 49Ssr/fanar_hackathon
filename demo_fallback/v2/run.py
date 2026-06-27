from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
import webbrowser

PORT = 8765
ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
FRONTEND = REPO_ROOT / "frontend"
MAIN_BACKEND_CHAT = "http://127.0.0.1:5000/chat"

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


def wants_calendar(text):
    t = text.lower()
    return any(x in t for x in ["calendar", "add", "schedule", "remind", "book", "meeting", "event", "tomorrow", "tonight", "today"])


def local_demo_response(text):
    t = " ".join((text or "").strip().split())
    low = t.lower()
    if not t or len(t) < 3 or all(ch in "`~!@#$%^&*()-_=+[]{};:'\",.<>/?\\|" for ch in t):
        return {
            "response": "No worries — I caught a stray keystroke. Presentation mode is still live. Try a route, place, calendar, or Qatar plan prompt.",
            "router": {"tools": [], "reason": "presentation_keystroke_guard", "confidence": 1.0},
            "widgets": [],
        }
    if "shaqab" in low or "lusail" in low or "marina" in low:
        return {
            "response": "Best move: metro plus tram. Start at Al Shaqab on the Green Line, transfer through the metro network toward Legtaifiya, then use Lusail Tram toward Marina. Use live signs for the exact platform.",
            "router": {"tools": ["route_plan"], "reason": "presentation_route_plan", "confidence": 1.0},
            "widgets": [{"type": "route", "origin": "Al Shaqab", "destination": "Lusail Marina", "mode": "Metro + Tram", "legs": ["Green Line", "Metro transfer", "Red Line to Legtaifiya", "Lusail Tram"], "duration": "~45-60 min", "maps_url": "https://www.google.com/maps/dir/Al+Shaqab/Lusail+Marina"}],
        }
    if "airport" in low or "hia" in low or "ras bu" in low:
        return {
            "response": "Best move: metro/public transport. From Ras Bu Aboud, take the Gold Line to Msheireb, switch to the Red Line, then follow the HIA T1 airport branch. Check Qatar Rail signs before tapping in.",
            "router": {"tools": ["route_plan"], "reason": "presentation_route_plan", "confidence": 1.0},
            "widgets": [{"type": "route", "origin": "Ras Bu Aboud", "destination": "Hamad International Airport T1", "mode": "Metro", "legs": ["Gold Line", "Msheireb transfer", "Red Line", "HIA T1 branch"], "duration": "~35-45 min", "maps_url": "https://www.google.com/maps/dir/Ras+Bu+Aboud/Hamad+International+Airport+T1"}],
        }
    if "qcri" in low or "hbku" in low or "education city" in low:
        return {
            "response": "QCRI/HBKU is in Education City. For metro access, use the Green Line side around Qatar National Library / Education City depending the entrance. I won’t guess bus routes without live data.",
            "router": {"tools": ["place_lookup"], "reason": "presentation_location_grounding", "confidence": 1.0},
            "widgets": [{"type": "place", "name": "QCRI / HBKU", "address": "Education City, Doha, Qatar", "maps_url": "https://www.google.com/maps/search/QCRI+HBKU+Education+City"}],
        }
    if wants_calendar(low):
        return {
            "response": "Calendar-ready fallback: I prepared the event card here. If the main backend is running, this same prompt is forwarded to the real Google Calendar integration first.",
            "router": {"tools": ["calendar_event"], "reason": "presentation_calendar_fallback", "confidence": 0.9},
            "widgets": [{"type": "calendar", "title": "Qaarib demo event", "start": "Today / requested time", "end": "Auto-estimated end", "link": ""}],
        }
    return {
        "response": "Qaarib turns the request into an action path: classify intent, keep context, call the right local tool, ground the result in Qatar, then render a widget the user can act on.",
        "router": {"tools": [], "reason": "presentation_general", "confidence": 1.0},
        "widgets": [],
    }


def forward_to_main_backend(payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MAIN_BACKEND_CHAT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))


class DemoHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            html = (ROOT / "index.html").read_text(encoding="utf-8")
            html = html.replace(
                "const API_BASE = window.QAARIB_API_BASE || 'http://localhost:5000';",
                "const API_BASE = window.QAARIB_API_BASE || window.location.origin;",
            )
            html = html.replace(
                "</body>",
                "<script>document.addEventListener('keydown',function(e){if(e.key==='Escape'){var i=document.getElementById('chatInput');if(i){i.value='';i.focus();}}});</script>\n</body>",
            )
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"message": ""}
        text = payload.get("message", "")
        try:
            data = forward_to_main_backend(payload)
            data.setdefault("router", {})["presentation_runtime"] = "forwarded_to_main_backend"
        except Exception as exc:
            data = local_demo_response(text)
            data.setdefault("router", {})["presentation_runtime"] = f"local_fallback: {type(exc).__name__}"
        out = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


if __name__ == "__main__":
    prepare_assets()
    os.chdir(ROOT)
    url = f"http://127.0.0.1:{PORT}/index.html"
    threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
    print("Qaarib presentation runtime v2:", url)
    print("Serving from:", ROOT)
    print("/chat tries the real backend first:", MAIN_BACKEND_CHAT)
    print("If backend/API/calendar fails, v2 stays in presentation mode with local widgets.")
    ThreadingHTTPServer(("127.0.0.1", PORT), DemoHandler).serve_forever()
