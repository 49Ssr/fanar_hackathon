from pathlib import Path
import os
import requests
from dotenv import load_dotenv

ROOT = Path.cwd()
env_candidates = [
    ROOT / "backend" / ".env",
    ROOT / ".env",
]
for env in env_candidates:
    if env.exists():
        load_dotenv(env)

api_key = os.getenv("FANAR_API_KEY") or os.getenv("API_KEY")
if not api_key:
    raise SystemExit("No FANAR_API_KEY/API_KEY found. Put it in backend/.env or .env first.")

out_dir = ROOT / "backend" / "generated_audio"
if not out_dir.exists():
    out_dir = ROOT / "generated_audio"
out_dir.mkdir(parents=True, exist_ok=True)

out_file = out_dir / "qaarib_aura_smoke.mp3"

url = "https://api.fanar.qa/v1/audio/speech"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": "Fanar-Aura-TTS-2",
    "input": "السلام عليكم، أنا قارب. أقدر أساعدك في الأماكن والمواصلات داخل قطر.",
    "voice": "Hamad",
    "response_format": "mp3",
    "stream": False,
}

print("Testing Fanar Aura TTS authorization...")
try:
    response = requests.post(url, headers=headers, json=payload, timeout=18)
except requests.exceptions.Timeout:
    print("TTS_SMOKE_RESULT=TIMEOUT")
    print("Skip Fanar Aura in the demo. Core Qaarib can still work.")
    raise SystemExit(0)
except Exception as e:
    print("TTS_SMOKE_RESULT=REQUEST_FAILED")
    print(str(e))
    print("Skip Fanar Aura in the demo. Core Qaarib can still work.")
    raise SystemExit(0)

content_type = response.headers.get("content-type", "")
print("status:", response.status_code)
print("content-type:", content_type)

if response.status_code != 200:
    print("TTS_SMOKE_RESULT=NOT_AVAILABLE")
    print(response.text[:800])
    print("Skip Fanar Aura in the demo. Core Qaarib can still work.")
    raise SystemExit(0)

if "audio" not in content_type.lower() and not response.content.startswith((b"ID3", b"RIFF")):
    print("TTS_SMOKE_RESULT=UNEXPECTED_200")
    print(response.text[:800])
    print("Do not demo TTS unless this is clearly an audio file.")
    raise SystemExit(0)

out_file.write_bytes(response.content)
print("TTS_SMOKE_RESULT=SUCCESS")
print("saved:", out_file.resolve())
print("You can demo this as optional Fanar Aura polish.")
