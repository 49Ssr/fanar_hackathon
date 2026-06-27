"""Qaarib Sundae Bridge

Thin, safe adapter around the updated Fanar agents repo.

Design goal:
- keep Qaarib's deterministic Qatar tools as the top-level system
- install the useful upstream supervisor/location/timetask code into backend/agents for optional use
- add hard demo guardrails for cases that should never be left to stale history

This file intentionally does not import LangGraph and does not replace app.py's
router. It acts as a last-mile correction layer after apply_local_router_rules().
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

TZ = ZoneInfo("Asia/Qatar")

KNOWN_ORIGIN_HINTS = [
    "Lusail", "Qatar University", "Legtaifiya", "Katara", "Al Qassar", "DECC",
    "West Bay", "Corniche", "Al Bidda", "Msheireb", "Al Doha Al Jadeeda",
    "Umm Ghuwailina", "Al Matar Al Qadeem", "Oqba Ibn Nafie", "Hamad International Airport T1",
    "Free Zone", "Ras Bu Fontas", "Al Wakra", "Al Riffa", "Education City",
    "Qatar National Library", "Al Shaqab", "Al Rayyan Al Qadeem", "Al Mansoura",
    "Souq Waqif", "National Museum", "Ras Bu Aboud", "QCRI", "Minaretein",
    "QNCC", "Doha Exhibition & Convention Center", "Qatar National Convention Centre",
]

SELF_LOCATION_PHRASES = [
    "where am i located", "where am i", "what is my location", "what's my location",
    "my current location", "where exactly am i", "locate me", "find my location",
]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def clean_transit_wording(text: Any) -> Any:
    """Clean rider-facing wording for Red Line branch signage.

    Oqba Ibn Nafie is the split point, not a user-facing final direction for the
    main Red Line in most demo phrasing. After Oqba, users follow either the Al
    Wakra branch or HIA T1 branch signage.
    """
    if not isinstance(text, str):
        return text
    replacements = {
        "southbound toward Msheireb/Oqba Ibn Nafie": "southbound toward Msheireb, then follow the Al Wakra / HIA T1 branch signage if continuing past Oqba Ibn Nafie",
        "toward Msheireb/Oqba Ibn Nafie": "toward Msheireb, then follow Al Wakra / HIA T1 branch signage if continuing past Oqba Ibn Nafie",
    }
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def is_self_location_request(user_prompt: str) -> bool:
    text = _clean(user_prompt)
    return any(phrase in text for phrase in SELF_LOCATION_PHRASES)


def self_location_answer() -> str:
    return (
        "I can resolve named Qatar places, but this CLI does not have live GPS access. "
        "Tell me your area, nearest landmark, or station — for example 'I'm at QCRI' or "
        "'I'm near DECC' — and I can route or resolve it. In the frontend, pass browser "
        "GPS/coordinates or a selected starting point into Qaarib for true current-location support."
    )


def is_decc_qncc_confusion(user_prompt: str) -> bool:
    text = _clean(user_prompt)
    has_decc = (
        "decc" in text
        or "doha exhibition" in text
        or "exhibition centre" in text
        or "exhibition center" in text
    )
    has_qncc = "qncc" in text or "qatar national convention" in text
    confusion = any(
        word in text
        for word in ["confused", "confusing", "difference", "different", "clarify", "right one", "which one"]
    )
    return has_decc and has_qncc and confusion


def _recent_route_origin(user_prompt: str, history: str) -> str:
    current = user_prompt or ""

    # Strongest: origin stated in current message.
    for name in KNOWN_ORIGIN_HINTS:
        if re.search(rf"\b(?:from|at|in)\s+{re.escape(name)}\b", current, flags=re.I):
            return name

    # Then last deterministic route from history.
    starts = re.findall(r"Start at ([A-Za-z0-9' &-]+?)\.", history or "")
    if starts:
        return starts[-1].strip()

    # Safe default: central interchange. Do not inherit stale QNL/QNCC destination.
    return "Msheireb"


def _decc_qncc_plan(user_prompt: str, history: str) -> dict[str, Any]:
    origin = _recent_route_origin(user_prompt, history)
    return {
        "tools": ["route_plan", "place_lookup", "web_search"],
        "queries": {
            "route_plan": f"{origin} to DECC by public transport",
            "place_lookup": "Doha Exhibition & Convention Center DECC West Bay Doha Qatar",
            "web_search": "DECC Doha Exhibition Convention Center QNCC Qatar National Convention Centre difference official Qatar",
        },
        "reason": "local_decc_qncc_clarify_route_rule",
        "confidence": 1.0,
    }


def _queries_mention_qnl(router_data: dict[str, Any]) -> bool:
    queries = router_data.get("queries") or {}
    joined = " ".join(str(v) for v in queries.values()).lower()
    return "qatar national library" in joined or " qnl" in joined


def apply_supervisor_bridge(user_prompt: str, history: str, router_data: dict[str, Any]) -> dict[str, Any]:
    """Last-mile Qaarib guardrails after the normal router.

    This is deliberately deterministic. The upstream supervisor is vendored for
    development/experiments, but these emergency rules avoid adding latency or
    new failure modes to the live demo path.
    """
    text = _clean(user_prompt)

    if is_self_location_request(user_prompt):
        return {
            "tools": [],
            "queries": {},
            "reason": "local_self_location_no_gps_rule",
            "confidence": 1.0,
            "direct_answer": self_location_answer(),
        }

    # Hard lock: DECC/QNCC confusion must never get rewritten to QNL.
    if is_decc_qncc_confusion(user_prompt):
        return _decc_qncc_plan(user_prompt, history)

    # Rescue case: if any previous local rule or model route mentions DECC but
    # the query was rewritten to QNL, force it back to DECC.
    if ("decc" in text or "doha exhibition" in text) and _queries_mention_qnl(router_data):
        return _decc_qncc_plan(user_prompt, history)

    return router_data


def _first_result(tool_results: list[dict[str, Any]], tool: str) -> dict[str, Any] | None:
    for result in tool_results or []:
        if result.get("source_tool") == tool:
            return result
    return None


def _results_for(tool_results: list[dict[str, Any]], tool: str) -> list[dict[str, Any]]:
    return [r for r in (tool_results or []) if r.get("source_tool") == tool]


def compose_decc_qncc_answer(tool_results: list[dict[str, Any]]) -> str:
    route = _first_result(tool_results, "route_plan")
    place = _first_result(tool_results, "place_lookup")
    web_items = _results_for(tool_results, "web_search")

    parts = [
        "Clarification: DECC and QNCC are different places.",
        "- DECC = Doha Exhibition & Convention Center in West Bay. This is the right target for DECC / Doha Exhibition & Convention Center.",
        "- QNCC = Qatar National Convention Centre in Education City. It is separate from DECC and sits on the Education City / Qatar National Library side.",
    ]

    if place:
        title = place.get("title", "DECC")
        address = place.get("address", "")
        maps_url = place.get("maps_url", "")
        line = f"Right destination: {title}"
        if address:
            line += f" — {address}"
        parts.append(line + ".")
        if maps_url:
            parts.append(f"Place map: {maps_url}")

    if route:
        answer = route.get("final_answer") or route.get("summary")
        if answer:
            parts.append(clean_transit_wording(answer).strip())
        elif route.get("maps_url"):
            parts.append(f"Navigation backup: {route.get('maps_url')}")

    if web_items:
        top = web_items[0]
        if top.get("title") or top.get("link"):
            text = "Source check: " + top.get("title", "relevant source")
            if top.get("link"):
                text += f" — {top.get('link')}"
            parts.append(text)

    return "\n".join(parts).strip()


def direct_answer_from_bridge(tool_results: list[dict[str, Any]], router_data: dict[str, Any] | None = None) -> str | None:
    reason = (router_data or {}).get("reason", "")
    if reason == "local_decc_qncc_clarify_route_rule":
        return compose_decc_qncc_answer(tool_results)
    return None


def upstream_supervisor_available() -> bool:
    try:
        from agents.supervisor.supervisor import SuperVisorAgent  # noqa: F401
        return True
    except Exception:
        return False


def run_upstream_supervisor(query: str) -> dict[str, Any]:
    """Optional diagnostic only; not used by the live demo path by default."""
    from agents.supervisor.supervisor import SuperVisorAgent

    model = os.getenv("MODEL_NAME") or os.getenv("FANAR_ROUTER_MODEL") or "Fanar"
    base_url = os.getenv("BASE_URL") or "https://api.fanar.qa/v1"
    api_key = os.getenv("API_KEY") or os.getenv("FANAR_API_KEY")
    agent = SuperVisorAgent(model_name=model, base_url=base_url, api_key=api_key)
    result = agent.run(query)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return dict(result)


if __name__ == "__main__":
    import json
    import sys

    q = " ".join(sys.argv[1:]) or "I am going to DECC but confused between DECC and QNCC"
    print("bridge_plan:")
    print(json.dumps(apply_supervisor_bridge(q, "", {"tools": [], "queries": {}}), indent=2, ensure_ascii=False))
    if os.getenv("QAARIB_RUN_UPSTREAM_SUPERVISOR") == "1":
        print("upstream_supervisor:")
        print(json.dumps(run_upstream_supervisor(q), indent=2, ensure_ascii=False))
