import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()
TZ = ZoneInfo("Asia/Qatar")


def _context():
    now = datetime.now(TZ)
    return {
        "reference_date": now.date().isoformat(),
        "reference_day": now.strftime("%A"),
        "reference_time": now.time().replace(microsecond=0).isoformat(),
    }


def _load_agent_run():
    try:
        from agents.timetask.timetask_agent import run
        return run, None
    except Exception as e:
        return None, str(e)


def _parse_duration_to_timedelta(value):
    if not value:
        return timedelta(hours=1)
    if isinstance(value, (int, float)):
        # Friend's agent may return minutes or hours depending on prompt; prefer minutes for large values.
        return timedelta(minutes=float(value)) if float(value) > 12 else timedelta(hours=float(value))
    text = str(value).lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b", text)
    if m:
        return timedelta(hours=float(m.group(1)))
    m = re.search(r"(\d+)\s*(minutes?|mins?|m)\b", text)
    if m:
        return timedelta(minutes=int(m.group(1)))
    return timedelta(hours=1)


def parse_timetask(query):
    run, err = _load_agent_run()
    if not run:
        return {"intent": None, "sub_intent": None, "slots": {}, "error": f"TimeTask agent unavailable: {err}"}
    try:
        return run(query, _context())
    except Exception as e:
        return {"intent": None, "sub_intent": None, "slots": {}, "error": f"TimeTask agent failed: {e}"}


def calendar_parse_from_timetask(query, tz=TZ, location_aliases=None):
    """Best-effort event parse for calendar_client.

    Returns the parsed object calendar_client expects, or None if TimeTask is unavailable
    or did not classify the prompt as an add-like calendar command.
    """
    result = parse_timetask(query)
    intent = (result.get("intent") or "").lower()
    slots = result.get("slots") or {}
    if intent not in {"add", "deadline", "reminder"}:
        return None

    date_s = slots.get("date") or slots.get("deadline_date")
    time_s = slots.get("time") or slots.get("deadline_time") or "09:00"
    if not date_s:
        return None

    try:
        hour, minute = [int(x) for x in str(time_s).split(":")[:2]]
    except Exception:
        hour, minute = 9, 0

    try:
        y, m, d = [int(x) for x in str(date_s).split("-")[:3]]
        start = datetime(y, m, d, hour, minute, tzinfo=tz)
    except Exception:
        return None

    duration = _parse_duration_to_timedelta(slots.get("duration"))
    title = slots.get("title") or query.strip()[:80] or "Qaarib event"
    location = slots.get("location") or ""
    if location_aliases and isinstance(location, str):
        location = location_aliases.get(location.lower(), location)
    return {
        "title": str(title)[:80],
        "location": location,
        "start": start,
        "end": start + duration,
        "date_source": "TimeTask agent",
        "time_source": "TimeTask agent",
        "timetask_raw": result,
    }


def _friendly_summary(result):
    intent = result.get("intent") or "Unknown"
    sub = result.get("sub_intent") or "Unclassified"
    slots = result.get("slots") or {}
    if result.get("error"):
        return f"TimeTask could not confidently parse this as a calendar/task command: {result.get('error')}"
    lines = [f"TimeTask parsed this as: {intent} / {sub}."]
    for key, value in slots.items():
        if value not in (None, "", []):
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def time_task(query, num_results=1):
    result = parse_timetask(query)
    final = _friendly_summary(result)
    return [{
        "title": "TimeTask Agent",
        "intent": result.get("intent"),
        "sub_intent": result.get("sub_intent"),
        "slots": result.get("slots", {}),
        "error": result.get("error", ""),
        "raw": result.get("raw", ""),
        "summary": final,
        "final_answer": final,
    }]


if __name__ == "__main__":
    import sys, json
    q = " ".join(sys.argv[1:]) or "schedule Qaarib demo tomorrow at 9am at QCRI"
    print(json.dumps(parse_timetask(q), ensure_ascii=False, indent=2))
