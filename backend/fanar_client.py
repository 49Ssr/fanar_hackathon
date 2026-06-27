import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

API_KEY = os.getenv("FANAR_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FANAR_BACKUP_MODEL = os.getenv("FANAR_BACKUP_MODEL", "Fanar-C-1-8.7B")
ALLOW_BIG_MODELS = os.getenv("FANAR_ALLOW_BIG_MODELS", "0") == "1"
GEMINI_FALLBACK_ENABLED = os.getenv("GEMINI_FALLBACK_ENABLED", "1") == "1"
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.5-flash"))

ROUTER_TIMEOUT = int(os.getenv("FANAR_ROUTER_TIMEOUT", "6"))
RESPONDER_TIMEOUT = int(os.getenv("FANAR_RESPONDER_TIMEOUT", "14"))
GEMINI_TIMEOUT = int(os.getenv("GEMINI_FALLBACK_TIMEOUT", "10"))

SLOW_MODELS = {"Fanar", "Fanar-C-2-27B"}
EXTRA_FALLBACK_MODELS = [m.strip() for m in os.getenv("FANAR_EXTRA_FALLBACK_MODELS", "Fanar-S-1-7B").split(",") if m.strip()]

FANAR_URL = "https://api.fanar.qa/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


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
    response = requests.post(
        FANAR_URL,
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def ask_gemini(prompt, max_tokens=500, timeout=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY missing")
    payload = {
        "model": GEMINI_FALLBACK_MODEL,
        "system_instruction": "You are Qaarib, a Qatar-focused assistant. Answer concisely and practically. If a strict JSON schema is requested, return only that schema.",
        "input": prompt,
        "generation_config": {"temperature": 0.2, "max_output_tokens": max_tokens, "thinking_level": "low"},
    }
    response = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=timeout or GEMINI_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return (data.get("output_text") or str(data)).strip()


def ask_fanar(prompt, model=None, max_tokens=500, timeout=None, allow_gemini_fallback=True):
    if timeout is None:
        timeout = ROUTER_TIMEOUT if max_tokens <= 350 else RESPONDER_TIMEOUT

    last_error = None
    if API_KEY:
        for candidate in candidate_models(model):
            try:
                return post_once(prompt, candidate, max_tokens=max_tokens, timeout=timeout)
            except Exception as e:
                last_error = e
                print(f"Fanar call failed on model={candidate}: {str(e)[:180]}")
                continue

    if GEMINI_FALLBACK_ENABLED and allow_gemini_fallback:
        try:
            print("Fanar unavailable; using Gemini fallback")
            return ask_gemini(prompt, max_tokens=max_tokens, timeout=GEMINI_TIMEOUT)
        except Exception as e:
            last_error = e
            print(f"Gemini fallback failed: {str(e)[:180]}")

    if not API_KEY:
        raise RuntimeError("FANAR_API_KEY is missing. Put it in backend/.env")
    raise last_error or RuntimeError("Model call failed")


def ask_fanar_timed(prompt, model=None, max_tokens=500, timeout=None, allow_gemini_fallback=True):
    start = time.perf_counter()
    response = ask_fanar(prompt, model, max_tokens, timeout=timeout, allow_gemini_fallback=allow_gemini_fallback)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    return response, elapsed_ms
