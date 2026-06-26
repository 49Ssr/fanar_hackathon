"""Gemini judge for Qaarib evaluation.

Uses Google's REST Interactions API through requests; no Google SDK dependency.
The API key must live in backend/.env or repo-root .env as GEMINI_API_KEY.
"""

from __future__ import annotations

import json
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

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_JUDGE_MODEL = os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


@dataclass
class JudgeResult:
    ok: bool
    latency_ms: float
    raw: str
    parsed: dict[str, Any]
    error: str = ""


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first balanced JSON object from a judge response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Gemini judge response")

    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])

    raise ValueError("Unbalanced JSON object in Gemini judge response")


def judge(case: dict[str, Any], candidate_model: str, candidate_output: str) -> JudgeResult:
    """Ask Gemini to grade one Fanar output."""
    if not GEMINI_API_KEY:
        return JudgeResult(
            ok=False,
            latency_ms=0.0,
            raw="",
            parsed={},
            error="GEMINI_API_KEY missing",
        )

    system_instruction = (
        "You are a strict evaluator for Qaarib, a Qatar-focused assistant. "
        "Judge the candidate output against the expected behaviour and rubric. "
        "Penalize hallucinated places, routes, prices, prayer facilities, timings, unsupported confidence, and bad follow-up handling. "
        "Reward concise practical answers, continuity, correct tool use, and safe uncertainty. "
        "Return valid JSON only."
    )

    input_text = f"""
CASE ID: {case.get('id')}
CASE TYPE: {case.get('type')}

USER PROMPT:
{case.get('prompt')}

HISTORY / STATE:
{case.get('history', '')}

FAKE TOOL RESULTS OR CONTEXT:
{json.dumps(case.get('tool_results', []), ensure_ascii=False, indent=2)}

EXPECTED BEHAVIOUR:
{case.get('expected', '')}

RUBRIC:
{case.get('rubric', '')}

FORBIDDEN TERMS / CLAIMS:
{json.dumps(case.get('forbidden_terms', []), ensure_ascii=False)}

REQUIRED TERMS / IDEAS:
{json.dumps(case.get('required_terms', []), ensure_ascii=False)}

CANDIDATE MODEL: {candidate_model}
CANDIDATE OUTPUT:
{candidate_output}

Return JSON only with this schema:
{{
  "overall": 0-10,
  "groundedness": 0-10,
  "usefulness": 0-10,
  "tone": 0-10,
  "latency_risk": "low|medium|high",
  "pass": true/false,
  "major_issues": ["..."],
  "notes": "short reason"
}}
""".strip()

    payload = {
        "model": GEMINI_JUDGE_MODEL,
        "system_instruction": system_instruction,
        "input": input_text,
        "generation_config": {
            "temperature": 0,
            "thinking_level": "low",
        },
    }

    started = time.perf_counter()
    try:
        response = requests.post(
            GEMINI_URL,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=80,
        )
        response.raise_for_status()
        data = response.json()

        # Interactions API exposes output_text. Keep fallbacks for safety.
        raw = data.get("output_text", "")
        if not raw:
            raw = json.dumps(data, ensure_ascii=False)

        parsed = extract_json(raw)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return JudgeResult(ok=True, latency_ms=latency_ms, raw=raw, parsed=parsed)
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return JudgeResult(
            ok=False,
            latency_ms=latency_ms,
            raw="",
            parsed={},
            error=str(exc),
        )
