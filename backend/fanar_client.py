import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")
load_dotenv()

API_KEY=os.getenv("FANAR_API_KEY")


# Demo-safe defaults. Long 27B generations can stall the live UI; the backend now
# prefers one shorter Fanar call for composition and deterministic tools for routing.
ROUTER_TIMEOUT = int(os.getenv("FANAR_ROUTER_TIMEOUT", "8"))
RESPONDER_TIMEOUT = int(os.getenv("FANAR_RESPONDER_TIMEOUT", "18"))


def ask_fanar(prompt:str, model:str, max_tokens=700, timeout=None):
    if not API_KEY:
        raise RuntimeError("FANAR_API_KEY is missing. Put it in backend/.env")

    if timeout is None:
        # Infer from max_tokens: short router calls get the faster timeout.
        timeout = ROUTER_TIMEOUT if max_tokens <= 400 else RESPONDER_TIMEOUT

    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    response=requests.post(
        "https://api.fanar.qa/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout,
    )

    response.raise_for_status()
    data=response.json()
    return data["choices"][0]["message"]["content"]


def ask_fanar_timed(prompt:str, model:str, max_tokens=700, timeout=None):
    start=time.perf_counter()
    response=ask_fanar(prompt, model, max_tokens, timeout=timeout)
    elapsed_ms=round((time.perf_counter()-start)*1000,2)
    return response, elapsed_ms
