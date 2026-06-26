"""Deterministic scoring helpers for Qaarib eval.

Gemini judge gives qualitative scoring. These helpers catch obvious failures
without needing another LLM.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    if start == -1:
        return None

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
                try:
                    return json.loads(text[start : i + 1])
                except Exception:
                    return None
    return None


def normalize_tools(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = {"web_search", "place_lookup", "route_plan"}
    return [str(x) for x in value if str(x) in allowed]


def router_static_score(
    output: str,
    expected_tools: list[str],
    required_query_terms: list[str] | None = None,
) -> dict[str, Any]:
    data = extract_json_object(output)
    if data is None:
        return {
            "router_parse_ok": False,
            "router_tools_match": False,
            "router_query_terms_ok": False,
            "router_static_pass": False,
            "router_actual_tools": [],
            "router_expected_tools": sorted(expected_tools or []),
            "router_query_blob": "",
            "router_reason": "Could not parse JSON object",
        }

    actual_tools = sorted(normalize_tools(data.get("tools", [])))
    expected_sorted = sorted(expected_tools or [])
    tools_match = actual_tools == expected_sorted

    queries = data.get("queries", {}) if isinstance(data.get("queries", {}), dict) else {}
    query_blob = " ".join(str(v) for v in queries.values()).lower()
    required_query_terms = required_query_terms or []
    terms_ok = all(term.lower() in query_blob for term in required_query_terms)

    return {
        "router_parse_ok": True,
        "router_tools_match": tools_match,
        "router_query_terms_ok": terms_ok,
        "router_static_pass": tools_match and terms_ok,
        "router_actual_tools": actual_tools,
        "router_expected_tools": expected_sorted,
        "router_query_blob": query_blob,
        "router_reason": data.get("reason", ""),
    }


def responder_static_checks(
    output: str,
    forbidden_terms: list[str] | None = None,
    required_terms: list[str] | None = None,
) -> dict[str, Any]:
    lower = output.lower()
    forbidden_terms = forbidden_terms or []
    required_terms = required_terms or []

    forbidden_hits = [term for term in forbidden_terms if term.lower() in lower]
    missing_required = [term for term in required_terms if term.lower() not in lower]

    return {
        "forbidden_hits": forbidden_hits,
        "missing_required": missing_required,
        "responder_static_pass": not forbidden_hits and not missing_required,
    }
