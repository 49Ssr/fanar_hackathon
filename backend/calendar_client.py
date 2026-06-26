import os
import re
import uuid
from pathlib import Path
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "generated_calendar"
TZ = ZoneInfo("Asia/Qatar")

# Minimal write scope: enough to create/edit events through events.insert.
# Keep it narrower than full calendar scope for the demo.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

LOCATION_ALIASES = {
    "qcri": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "education city": "Education City, Doha, Qatar",
    "minaretein": "Minaretein Center, Education City, Doha, Qatar",
    "msheireb": "Msheireb Downtown Doha, Qatar",
    "downtown": "Msheireb Downtown Doha, Qatar",
    "lusail marina": "Lusail Marina, Qatar",
    "hia": "Hamad International Airport Terminal 1, Doha, Qatar",
}


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _ics_escape(text):
    text = str(text or "")
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def _calendar_env_path(var_name, default_filename):
    raw = os.getenv(var_name, default_filename).strip()
    p = Path(raw)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


def _google_calendar_enabled():
    value = os.getenv("GOOGLE_CALENDAR_ENABLED", "auto").strip().lower()
    return value not in {"0", "false", "no", "off", "ics"}


def _parse_date(text, now):
    lower = text.lower()
    today = now.date()

    if "day after tomorrow" in lower:
        return today + timedelta(days=2), "day after tomorrow"
    if "tomorrow" in lower:
        return today + timedelta(days=1), "tomorrow"
    if "today" in lower:
        return today, "today"

    for name, idx in WEEKDAYS.items():
        if re.search(rf"\b{name}\b", lower):
            delta = (idx - today.weekday()) % 7
            if delta == 0:
                delta = 7
            return today + timedelta(days=delta), name

    # 28 June / 28th June
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+(\d{4}))?\b", lower)
    if m:
        day = int(m.group(1)); month = MONTHS[m.group(2)]; year = int(m.group(3) or today.year)
        candidate = date(year, month, day)
        if candidate < today and not m.group(3):
            candidate = date(year + 1, month, day)
        return candidate, m.group(0)

    # June 28 / June 28th
    m = re.search(r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\b", lower)
    if m:
        month = MONTHS[m.group(1)]; day = int(m.group(2)); year = int(m.group(3) or today.year)
        candidate = date(year, month, day)
        if candidate < today and not m.group(3):
            candidate = date(year + 1, month, day)
        return candidate, m.group(0)

    # 28/6 or 28-6. Qatar/UK style day/month.
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", lower)
    if m:
        day = int(m.group(1)); month = int(m.group(2)); year_s = m.group(3)
        year = int(year_s) if year_s else today.year
        if year < 100:
            year += 2000
        candidate = date(year, month, day)
        if candidate < today and not year_s:
            candidate = date(year + 1, month, day)
        return candidate, m.group(0)

    return today, "today(default)"


def _parse_time(text):
    lower = text.lower()

    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower)
    if m:
        hour = int(m.group(1)); minute = int(m.group(2) or 0); ampm = m.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return time(hour, minute), m.group(0)

    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", lower)
    if m:
        return time(int(m.group(1)), int(m.group(2))), m.group(0)

    if "morning" in lower:
        return time(9, 0), "morning(default 9am)"
    if "afternoon" in lower:
        return time(15, 0), "afternoon(default 3pm)"
    if "evening" in lower or "night" in lower:
        return time(19, 0), "evening(default 7pm)"

    return time(9, 0), "9am(default)"


def _parse_duration(text):
    lower = text.lower()
    m = re.search(r"\bfor\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?|h)\b", lower)
    if m:
        return timedelta(hours=float(m.group(1)))
    m = re.search(r"\bfor\s+(\d+)\s*(minutes?|mins?|m)\b", lower)
    if m:
        return timedelta(minutes=int(m.group(1)))
    return timedelta(hours=1)


def _parse_location(text):
    m = re.search(r"\b(?:at|in|near)\s+([^,.]+(?:,\s*[^,.]+)?)(?:\s+(?:on|tomorrow|today|at|for)\b|$)", text, flags=re.I)
    if not m:
        return ""
    loc = _clean(m.group(1)).strip(" .")
    if re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)?\b", loc.lower()):
        return ""
    key = loc.lower()
    return LOCATION_ALIASES.get(key, loc)


def _parse_title(text):
    title = _clean(text)
    title = re.sub(r"https?://\S+", "", title)

    replacements = [
        (r"\b(add|put|create|make|schedule|save|book)\b", ""),
        (r"\b(to|in|into)\s+my\s+google\s+calendar\b", ""),
        (r"\b(to|in|into)\s+google\s+calendar\b", ""),
        (r"\b(to|in|into)\s+my\s+calendar\b", ""),
        (r"\b(to|in|into)\s+the\s+calendar\b", ""),
        (r"\bgoogle\s+calendar\b", ""),
        (r"\bcalendar\s+event\s+for\b", ""),
        (r"\bevent\s+for\b", ""),
        (r"\breminder\s+for\b", ""),
        (r"\bcalendar\b", ""),
        (r"\bevent\b", ""),
        (r"\breminder\b", ""),
    ]
    for pat, repl in replacements:
        title = re.sub(pat, repl, title, flags=re.I)

    title = re.sub(r"\b(today|tomorrow|day after tomorrow|morning|afternoon|evening|night)\b", "", title, flags=re.I)
    title = re.sub(r"\b(on\s+)?\d{1,2}(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?\b", "", title, flags=re.I)
    title = re.sub(r"\b(on\s+)?(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?\b", "", title, flags=re.I)
    title = re.sub(r"\b(on|at|for)\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b", "", title, flags=re.I)
    title = re.sub(r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", "", title, flags=re.I)
    title = re.sub(r"\bfor\s+\d+(?:\.\d+)?\s*(hours?|hrs?|h|minutes?|mins?|m)\b", "", title, flags=re.I)
    title = re.sub(r"\b(at|in|near)\s+[^,.]+$", "", title, flags=re.I)
    title = _clean(title).strip(" .,-")
    if len(title) < 3:
        return "Qaarib event"
    return title[:80]


def _parse_event_basic(query):
    now = datetime.now(TZ)
    text = _clean(query)
    event_date, date_source = _parse_date(text, now)
    event_time, time_source = _parse_time(text)
    duration = _parse_duration(text)
    start = datetime.combine(event_date, event_time, TZ)
    end = start + duration
    return {
        "title": _parse_title(text),
        "location": _parse_location(text),
        "start": start,
        "end": end,
        "date_source": date_source,
        "time_source": time_source,
    }


def _create_ics(parsed):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    start = parsed["start"]
    end = parsed["end"]
    uid = f"qaarib-{uuid.uuid4()}@local"
    filename = f"qaarib_event_{start.strftime('%Y%m%d_%H%M')}_{uuid.uuid4().hex[:6]}.ics"
    path = OUT_DIR / filename
    now = datetime.now(TZ)

    ics = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Qaarib//Hackathon Calendar//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_format_dt(now)}",
        f"DTSTART;TZID=Asia/Qatar:{_format_dt(start)}",
        f"DTEND;TZID=Asia/Qatar:{_format_dt(end)}",
        f"SUMMARY:{_ics_escape(parsed['title'])}",
        f"LOCATION:{_ics_escape(parsed['location'])}" if parsed.get("location") else "LOCATION:",
        "DESCRIPTION:Created by Qaarib. Verify event details before relying on it.",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])
    path.write_text(ics, encoding="utf-8")
    return path, filename



def _parse_event(query):
    # Prefer the polished TimeTask agent for natural calendar/task language.
    # Fall back to the old deterministic parser if the agent is unavailable or unsure.
    try:
        from time_task_client import calendar_parse_from_timetask
        parsed = calendar_parse_from_timetask(query, TZ, LOCATION_ALIASES)
        if parsed:
            return parsed
    except Exception:
        pass
    return _parse_event_basic(query)


def _google_service():
    if not _google_calendar_enabled():
        return None, "Google Calendar API is disabled by GOOGLE_CALENDAR_ENABLED."

    credentials_path = _calendar_env_path("GOOGLE_CALENDAR_CREDENTIALS", "google_credentials.json")
    token_path = _calendar_env_path("GOOGLE_CALENDAR_TOKEN", "google_calendar_token.json")

    if not credentials_path.exists():
        return None, f"Google Calendar credentials missing: {credentials_path}"

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except Exception as e:
        return None, f"Google Calendar libraries missing: {e}. Run: pip install -r requirements.txt"

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                authorization_prompt_message="Open this URL to connect Google Calendar: {url}",
                success_message="Qaarib Google Calendar connected. You can close this tab.",
            )
        token_path.write_text(creds.to_json(), encoding="utf-8")

    service = build("calendar", "v3", credentials=creds)
    return service, "connected"


def _insert_google_event(parsed):
    service, status = _google_service()
    if not service:
        return None, status

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip() or "primary"
    send_updates = os.getenv("GOOGLE_CALENDAR_SEND_UPDATES", "none").strip() or "none"

    event_body = {
        "summary": parsed["title"],
        "location": parsed.get("location", ""),
        "description": "Created by Qaarib during the Fanar Hackathon demo. Verify details before relying on it.",
        "start": {
            "dateTime": parsed["start"].isoformat(),
            "timeZone": "Asia/Qatar",
        },
        "end": {
            "dateTime": parsed["end"].isoformat(),
            "timeZone": "Asia/Qatar",
        },
    }

    created = service.events().insert(
        calendarId=calendar_id,
        body=event_body,
        sendUpdates=send_updates,
    ).execute()
    return created, "connected"


def _is_list_calendar_request(text):
    lower = text.lower()
    return any(phrase in lower for phrase in [
        "what's on my calendar", "whats on my calendar", "what do i have", "what events do i have",
        "am i free", "am i busy", "check my calendar", "show my calendar", "my schedule"
    ])


def _list_google_events(query):
    now = datetime.now(TZ)
    event_date, date_source = _parse_date(query, now)
    start = datetime.combine(event_date, time(0, 0), TZ)
    end = start + timedelta(days=1)

    service, status = _google_service()
    if not service:
        return [{
            "title": "Google Calendar not connected",
            "summary": status,
            "final_answer": f"Google Calendar is not connected yet: {status}",
        }]

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip() or "primary"
    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=10,
    ).execute().get("items", [])

    day_label = start.strftime("%a %d %b %Y")
    if not events:
        final = f"Your Google Calendar looks clear for {day_label} (Asia/Qatar)."
    else:
        lines = [f"Your Google Calendar for {day_label}:"]
        for i, ev in enumerate(events, start=1):
            title = ev.get("summary", "Untitled event")
            raw_start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
            if "T" in raw_start:
                try:
                    dt = datetime.fromisoformat(raw_start.replace("Z", "+00:00")).astimezone(TZ)
                    when = dt.strftime("%I:%M %p").replace(" 0", " ")
                except Exception:
                    when = raw_start
            else:
                when = "all day"
            loc = ev.get("location", "")
            extra = f" — {loc}" if loc else ""
            lines.append(f"{i}. {when}: {title}{extra}")
        final = "\n".join(lines)

    return [{
        "title": "Google Calendar events",
        "date": event_date.isoformat(),
        "timezone": "Asia/Qatar",
        "summary": f"Listed events for {day_label}. Date source: {date_source}.",
        "final_answer": final,
    }]


def calendar_event(query, num_results=1):
    text = _clean(query)
    if not text:
        return [{
            "title": "Calendar unavailable",
            "summary": "No calendar details provided.",
            "final_answer": "Tell me the event name, date/time, and location, and I’ll add it to Google Calendar."
        }]

    if _is_list_calendar_request(text):
        return _list_google_events(text)

    parsed = _parse_event(text)
    ics_path, ics_filename = _create_ics(parsed)

    google_event = None
    google_status = "not attempted"
    try:
        google_event, google_status = _insert_google_event(parsed)
    except Exception as e:
        google_status = f"Google Calendar insert failed: {e}"

    start = parsed["start"]
    end = parsed["end"]
    when = start.strftime("%a %d %b %Y, %I:%M %p").replace(" 0", " ")
    until = end.strftime("%I:%M %p").replace(" 0", " ")
    loc_text = f" at {parsed['location']}" if parsed.get("location") else ""

    if google_event:
        link = google_event.get("htmlLink", "")
        final = (
            f"Added to Google Calendar: {parsed['title']}{loc_text}.\n"
            f"Time: {when}–{until} (Asia/Qatar)."
        )
        if link:
            final += f"\nCalendar link: {link}"
        final += f"\nBackup ICS file: {ics_path}"
    else:
        final = (
            f"Calendar draft ready, but Google Calendar was not updated.\n"
            f"Reason: {google_status}\n"
            f"Event: {parsed['title']}{loc_text}.\n"
            f"Time: {when}–{until} (Asia/Qatar).\n"
            f"Backup ICS file: {ics_path}\n"
            f"To enable real Google Calendar insertion, put OAuth desktop credentials at backend/google_credentials.json and rerun."
        )

    return [{
        "title": "Google Calendar event" if google_event else "Calendar draft ready",
        "event_title": parsed["title"],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "Asia/Qatar",
        "location": parsed.get("location", ""),
        "google_status": google_status,
        "google_event_id": google_event.get("id", "") if google_event else "",
        "google_html_link": google_event.get("htmlLink", "") if google_event else "",
        "ics_path": str(ics_path),
        "ics_filename": ics_filename,
        "summary": f"{parsed['title']} on {when} Asia/Qatar. Date source: {parsed['date_source']}; time source: {parsed['time_source']}.",
        "final_answer": final,
    }]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "add hackathon demo tomorrow at 9am at QCRI to my calendar"
    for r in calendar_event(q):
        print(r.get("final_answer"))
