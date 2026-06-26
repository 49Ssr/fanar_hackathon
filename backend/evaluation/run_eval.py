"""Run Qaarib model evaluation.

Recommended from repo root:
    cd backend
    python evaluation/run_eval.py

Or from repo root directly:
    python backend/evaluation/run_eval.py

Key env vars in backend/.env:
    FANAR_API_KEY=...
    GEMINI_API_KEY=...
    FANAR_EVAL_MODELS=Fanar,Fanar-C-1-8.7B,Fanar-C-2-27B
    GEMINI_JUDGE_MODEL=gemini-3.5-flash
    EVAL_TIME_LIMIT_MINUTES=60

Time-limit behaviour:
    The runner checks the clock only between cases.
    Once a case starts, it finishes that same prompt for every selected Fanar
    model and Gemini judge call, then stops before the next case if time expired.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

# Make backend imports work from either repo root or backend/.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from fanar_client_eval import ask_fanar
from gemini_judge import judge
from scoring import router_static_score, responder_static_checks

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv()
except Exception:
    pass

# Import current backend prompts/parsers. This means the evaluator tests the
# same prompt surface you are demoing.
try:
    from router import build_router_prompt
except Exception:
    build_router_prompt = None

try:
    from chat_session import SYSTEM_INSTRUCTIONS, format_tool_results
except Exception:
    SYSTEM_INSTRUCTIONS = "You are Qaarib, a Qatar-focused assistant."

    def format_tool_results(results):
        return json.dumps(results, ensure_ascii=False, indent=2)


CASES_PATH = EVAL_DIR / "eval_cases.jsonl"
OUTPUT_DIR = EVAL_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_cases() -> list[dict[str, Any]]:
    cases = []
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))
    return cases


def model_list() -> list[str]:
    raw = os.getenv("FANAR_EVAL_MODELS", "Fanar,Fanar-C-1-8.7B,Fanar-C-2-27B")
    return [model.strip() for model in raw.split(",") if model.strip()]


def time_limit_seconds() -> float | None:
    raw = os.getenv("EVAL_TIME_LIMIT_MINUTES", "").strip()
    if not raw:
        return None
    try:
        minutes = float(raw)
    except ValueError:
        raise ValueError("EVAL_TIME_LIMIT_MINUTES must be a number, e.g. 60 or 120")
    if minutes <= 0:
        return None
    return minutes * 60


def build_responder_eval_prompt(case: dict[str, Any]) -> str:
    tool_block = format_tool_results(case.get("tool_results", []))
    history = case.get("history") or "No previous conversation."
    return f"""
[HIDDEN SYSTEM INSTRUCTIONS]
{SYSTEM_INSTRUCTIONS}

[SESSION HISTORY]
{history}

[FRESH TOOL OUTPUT]
{tool_block}

[CURRENT USER MESSAGE]
{case.get('prompt')}

[ASSISTANT INSTRUCTIONS]
Answer the current user message in Qaarib's voice.
Use the tool output as factual context.
Do not invent places, prices, routes, menus, timings, or facilities.
If evidence is missing, say so briefly and give the safest practical next step.
Keep it concise and demo-ready.
""".strip()


def build_prompt_for_case(case: dict[str, Any]) -> str:
    if case["type"] == "router":
        if build_router_prompt is None:
            raise RuntimeError("Could not import backend.router.build_router_prompt")
        return build_router_prompt(case.get("prompt", ""), case.get("history", ""))

    if case["type"] == "responder":
        return build_responder_eval_prompt(case)

    raise ValueError(f"Unknown case type: {case.get('type')}")


def evaluate_one(case: dict[str, Any], model: str) -> dict[str, Any]:
    prompt = build_prompt_for_case(case)
    max_tokens = 380 if case["type"] == "router" else 650
    result = ask_fanar(prompt, model=model, max_tokens=max_tokens, temperature=0)

    row: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "case_id": case.get("id"),
        "case_type": case.get("type"),
        "model": model,
        "fanar_ok": result.ok,
        "fanar_latency_ms": result.latency_ms,
        "fanar_error": result.error,
        "output": result.output,
    }

    if not result.ok:
        row.update({"static_pass": False, "gemini_pass": False, "overall": 0})
        return row

    if case["type"] == "router":
        static = router_static_score(
            result.output,
            expected_tools=case.get("expected_tools", []),
            required_query_terms=case.get("required_query_terms", []),
        )
        row.update(static)
        row["static_pass"] = static["router_static_pass"]
    else:
        static = responder_static_checks(
            result.output,
            forbidden_terms=case.get("forbidden_terms", []),
            required_terms=case.get("required_terms", []),
        )
        row.update(static)
        row["static_pass"] = static["responder_static_pass"]

    judged = judge(case, model, result.output)
    row["gemini_ok"] = judged.ok
    row["gemini_latency_ms"] = judged.latency_ms
    row["gemini_error"] = judged.error
    row["gemini_raw"] = judged.raw

    if judged.ok:
        parsed = judged.parsed
        row["overall"] = parsed.get("overall")
        row["groundedness"] = parsed.get("groundedness")
        row["usefulness"] = parsed.get("usefulness")
        row["tone"] = parsed.get("tone")
        row["latency_risk"] = parsed.get("latency_risk")
        row["gemini_pass"] = parsed.get("pass")
        issues = parsed.get("major_issues", [])
        row["major_issues"] = " | ".join(issues) if isinstance(issues, list) else str(issues)
        row["gemini_notes"] = parsed.get("notes", "")
    else:
        row["gemini_pass"] = False
        row["overall"] = 0
        row["gemini_notes"] = judged.error

    return row


def write_outputs(rows: list[dict[str, Any]]) -> None:
    jsonl_path = OUTPUT_DIR / "latest_results.jsonl"
    csv_path = OUTPUT_DIR / "latest_results.csv"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    fieldnames = sorted({key for row in rows for key in row.keys() if key not in {"output", "gemini_raw"}})
    preferred = [
        "case_id",
        "case_type",
        "model",
        "static_pass",
        "gemini_pass",
        "overall",
        "groundedness",
        "usefulness",
        "tone",
        "fanar_latency_ms",
        "gemini_latency_ms",
        "fanar_ok",
        "fanar_error",
        "gemini_error",
        "major_issues",
        "gemini_notes",
    ]
    fieldnames = [f for f in preferred if f in fieldnames] + [f for f in fieldnames if f not in preferred]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    print(f"\nWrote {jsonl_path}")
    print(f"Wrote {csv_path}")


def print_summary(rows: list[dict[str, Any]]) -> None:
    print("\n=== SUMMARY ===")
    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)

    for model, items in by_model.items():
        static_passes = sum(1 for row in items if row.get("static_pass") is True)
        gemini_passes = sum(1 for row in items if row.get("gemini_pass") is True)
        scored = [row.get("overall") for row in items if isinstance(row.get("overall"), (int, float))]
        avg = round(sum(scored) / len(scored), 2) if scored else "n/a"
        avg_latency = round(sum(float(row.get("fanar_latency_ms") or 0) for row in items) / len(items), 2)
        print(
            f"{model}: static {static_passes}/{len(items)} | "
            f"gemini {gemini_passes}/{len(items)} | avg {avg}/10 | fanar avg {avg_latency} ms"
        )

    print("\nWorst cases:")
    bad = [row for row in rows if row.get("static_pass") is False or row.get("gemini_pass") is False]
    for row in bad[:12]:
        print(
            f"- {row.get('case_id')} | {row.get('model')} | "
            f"static={row.get('static_pass')} gemini={row.get('gemini_pass')} | "
            f"{row.get('gemini_notes') or row.get('fanar_error')}"
        )


def main() -> None:
    cases = load_cases()
    models = model_list()
    limit_s = time_limit_seconds()
    started = time.perf_counter()

    print(f"Loaded {len(cases)} cases")
    print(f"Models: {', '.join(models)}")
    if limit_s:
        print(f"Time limit: {round(limit_s / 60, 2)} minutes")
        print("Limit rule: finish the current case for all selected models, then stop before the next case.")
    else:
        print("Time limit: none")

    rows: list[dict[str, Any]] = []
    total = len(cases) * len(models)
    n = 0
    stopped_by_time = False

    for case_index, case in enumerate(cases, start=1):
        elapsed = time.perf_counter() - started
        if limit_s and elapsed >= limit_s and rows:
            stopped_by_time = True
            print(f"\nTime limit reached before case {case_index}. Stopping cleanly.")
            break

        print(f"\n=== CASE {case_index}/{len(cases)}: {case.get('id')} ===")
        for model in models:
            n += 1
            elapsed_min = round((time.perf_counter() - started) / 60, 2)
            print(f"[{n}/{total}] +{elapsed_min}m :: {case.get('id')} :: {model}")
            row = evaluate_one(case, model)
            rows.append(row)
            print(
                f"    static={row.get('static_pass')} "
                f"gemini={row.get('gemini_pass')} "
                f"overall={row.get('overall')} "
                f"latency={row.get('fanar_latency_ms')}ms"
            )

            # Write after every model so a crash or Ctrl+C still leaves usable output.
            write_outputs(rows)

    if not rows:
        print("No rows produced. Check eval_cases.jsonl and API keys.")
        return

    write_outputs(rows)
    print_summary(rows)

    if stopped_by_time:
        print("\nStopped because EVAL_TIME_LIMIT_MINUTES expired after finishing a full case.")


if __name__ == "__main__":
    main()
