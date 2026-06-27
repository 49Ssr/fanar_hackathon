from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser, threading, time, os

PORT = 8765
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/index.html"
    threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
    print("Qaarib presentation runtime v2:", url)
    ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler).serve_forever()
