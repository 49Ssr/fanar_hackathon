"""Small Fanar client used only by the evaluation runner.

This is intentionally separate from backend/fanar_client.py so benchmarking
changes never touch the demo runtime.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

# Prefer backend/.env, but allow repo-root .env for local convenience.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")
load_dotenv()

FANAR_API_KEY = os.getenv("FANAR_API_KEY")
FANAR_BASE_URL = os.getenv("FANAR_BASE_URL", "https://api.fanar.qa/v1")


@dataclass
class FanarResult:
    model: str
    output: str
    latency_ms: float
    ok: bool
    error: str = ""


def ask_fanar(
    prompt: str,
    model: str,
    max_tokens: int = 700,
    temperature: float | None = None,
) -> FanarResult:
    """Call Fanar chat completions and return output + latency."""
    if not FANAR_API_KEY:
        return FanarResult(model=model, output="", latency_ms=0.0, ok=False, error="FANAR_API_KEY missing")

    headers = {
        "Authorization": f"Bearer {FANAR_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    started = time.perf_counter()
    try:
        response = requests.post(
            f"{FANAR_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=80,
        )
        response.raise_for_status()
        data = response.json()
        output = data["choices"][0]["message"]["content"]
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return FanarResult(model=model, output=output, latency_ms=latency_ms, ok=True)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return FanarResult(model=model, output="", latency_ms=latency_ms, ok=False, error=str(exc))
