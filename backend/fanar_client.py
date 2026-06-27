import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

API_KEY = os.getenv("FANAR_API_KEY")

# Emergency hackathon default: organisers recommended the smaller chat model
# while the main Fanar endpoints are overloaded.
FANAR_BACKUP_MODEL = os.getenv("FANAR_BACKUP_MODEL", "Fanar-C-1-8.7B")
ALLOW_BIG_MODELS = os.getenv("FANAR_ALLOW_BIG_MODELS", "0") == "1"

ROUTER_TIMEOUT = int(os.getenv("FANAR_ROUTER_TIMEOUT", "6"))
RESPONDER_TIMEOUT = int(os.getenv("FANAR_RESPONDER_TIMEOUT", "14"))

SLOW_MODELS = {"Fanar", "Fanar-C-2-27B"}
EXTRA_FALLBACK_MODELS = [m.strip() for m in os.getenv("FANAR_EXTRA_FALLBACK_MODELS", "Fanar-S-1-7B").split(",") if m.strip()]


def normalize_model(model):
    requested = (model or "").strip() or FANAR_BACKUP_MODEL
    if not ALLOW_BIG_MODELS and requested in SLOW_MODELS:
        return FANAR_BACKUP_MODEL
    return requested


def candidate_models(model):
    first = normalize_model(model)
    out = []
    for item in [first, FANAR_BACKUP_MODEL] + EXTRA_FALLBACK_MODELS:
        if item and item not in out:
            out.append(item)
    return out


def post_once(prompt, model, max_tokens, timeout):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    response = requests.post(
        "https://api.fanar.qa/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def ask_fanar(prompt, model=None, max_tokens=500, timeout=None):
    if not API_KEY:
        raise RuntimeError("FANAR_API_KEY is missing. Put it in backend/.env")

    if timeout is None:
        timeout = ROUTER_TIMEOUT if max_tokens <= 350 else RESPONDER_TIMEOUT

    last_error = None
    for candidate in candidate_models(model):
        try:
            return post_once(prompt, candidate, max_tokens=max_tokens, timeout=timeout)
        except Exception as e:
            last_error = e
            print(f"Fanar call failed on model={candidate}: {str(e)[:180]}")
            continue

    raise last_error or RuntimeError("Fanar call failed")


def ask_fanar_timed(prompt, model=None, max_tokens=500, timeout=None):
    start = time.perf_counter()
    response = ask_fanar(prompt, model, max_tokens, timeout=timeout)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return response, elapsed_ms
