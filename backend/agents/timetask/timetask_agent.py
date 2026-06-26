import json
import os
import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Keep imports package-safe for Qaarib.
# Ahmed's original standalone agent used sys.path insertion to import
# datetime/resolve_datetime.py, which works at runtime in some folders but
# breaks Pylance and is fragile inside a larger backend.
from .datetime.resolve_datetime import resolve_datetime

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

client = OpenAI(
    base_url="https://api.fanar.qa/v1",
    api_key=os.getenv("FANAR_API_KEY"),
)
model_name = "Fanar"


def get_system_prompt(reference_date=None, reference_day=None):
    if reference_date is None:
        today = datetime.date.today()
        reference_date = today.strftime("%Y-%m-%d")
        reference_day = today.strftime("%A")
    return f"""You are a calendar assistant for the Fanar Arabic AI platform.
Extract the intent, sub-intent, and slots from the user message.
Return ONLY a JSON object with no explanation, no markdown, nothing else.
Always use HH:MM 24-hour format for time slots (e.g. 15:00, 09:30).
For date slots, output the date expression exactly as the user said it (e.g. "next Monday", "tomorrow", "August 5th"). Do NOT convert to YYYY-MM-DD format.
Set missing optional slots to null.
remind_before is always in minutes. Convert days/hours to minutes (e.g. "2 days before" = 2880, "1 hour before" = 60).
Today's date is {reference_date}. Today is {reference_day}.

## Intents and slot schemas

### Add
Use when the user wants to create a new event, meeting, or task.
Sub-intents: Meeting, Event, Task/To-do, Recurring
Slots: title, date, time, duration, location, attendees, action
Action value: ADD

Example:
User: "Schedule a meeting with Sara next Monday at 3pm"
Output: {{"intent":"Add","sub_intent":"Meeting","slots":{{"title":"Meeting with Sara","date":"next Monday","time":"15:00","duration":null,"location":null,"attendees":["Sara"],"action":"ADD"}}}}

### Reschedule
Use when the user wants to move or change an existing event.
Sub-intents: Move time, Move date, Change venue
Slots: title, new_date, new_time, new_location, reason, action
Action value: UPDATE

Example:
User: "Move my team meeting to next Wednesday at 10am"
Output: {{"intent":"Reschedule","sub_intent":"Move date","slots":{{"title":"Team meeting","new_date":"next Wednesday","new_time":"10:00","new_location":null,"reason":null,"action":"UPDATE"}}}}

### Delete
Use when the user wants to cancel or remove an event or task.
Sub-intents: Cancel event, Remove task
Slots: title, date, confirm, action
Action value: DELETE

Example:
User: "Cancel my dentist appointment tomorrow"
Output: {{"intent":"Delete","sub_intent":"Cancel event","slots":{{"title":"Dentist appointment","date":"tomorrow","confirm":true,"action":"DELETE"}}}}

### Deadline
Use when the user wants to set or update a deadline.
Sub-intents: Set deadline, Update deadline
Slots: title, deadline_date, deadline_time, remind_before, action
Action value: SET_DEADLINE
remind_before is in minutes. Convert days/hours to minutes (e.g. "2 days before" = 2880).

Example:
User: "My report is due next Sunday, remind me 2 days before"
Output: {{"intent":"Deadline","sub_intent":"Set deadline","slots":{{"title":"Report","deadline_date":"next Sunday","deadline_time":null,"remind_before":2880,"action":"SET_DEADLINE"}}}}

### Reminder
Use when the user wants to set a reminder for an existing event.
Sub-intents: Before event, Alert approaching
Slots: title, remind_before, repeat, action
Action value: SET_REMINDER
remind_before is in minutes. Convert days/hours to minutes (e.g. "1 hour before" = 60).

Example:
User: "Remind me 30 minutes before the team call"
Output: {{"intent":"Reminder","sub_intent":"Before event","slots":{{"title":"Team call","remind_before":30,"repeat":false,"action":"SET_REMINDER"}}}}

### Query
Use when the user wants to see or list their schedule.
Sub-intents: Today's tasks, Daily summary, This week, Specific event, This month
Slots: title, date, action
Action value: QUERY
If the user asks about a range like "this week" or "next week", set date to null.

Example:
User: "What do I have this week?"
Output: {{"intent":"Query","sub_intent":"This week","slots":{{"title":null,"date":null,"action":"QUERY"}}}}

### Check Availability
Use when the user wants to know if they are free at a certain time.
Sub-intents: Free slot, Conflict check
Slots: title, date, time, duration, action
Action value: CHECK

Example:
User: "Am I free next Friday afternoon?"
Output: {{"intent":"Check Availability","sub_intent":"Free slot","slots":{{"title":null,"date":"next Friday","time":null,"duration":null,"action":"CHECK"}}}}
"""


def _resolve_slots(slots: dict, ref_date: datetime.date, ref_time: datetime.time) -> dict:
    """
    Finds all temporal slots in the Fanar output and resolves them using resolve_datetime.
    Date and time slots are combined before resolving when both are present.
    """
    DATE_SLOT_PAIRS = [
        ("date", "time"),
        ("new_date", "new_time"),
        ("deadline_date", "deadline_time"),
    ]

    resolved = dict(slots)

    for date_key, time_key in DATE_SLOT_PAIRS:
        date_val = resolved.get(date_key)
        time_val = resolved.get(time_key)

        if date_val is None and time_val is None:
            continue

        # Combine into one expression if both present
        if date_val and time_val:
            expression = f"{date_val} at {time_val}"
        elif date_val:
            expression = date_val
        else:
            expression = time_val

        result = resolve_datetime(expression, ref_date, ref_time)

        if result["status"] == "ok":
            if date_key in resolved:
                resolved[date_key] = result["date_start"]
            if time_key in resolved:
                resolved[time_key] = result["time"]

    return resolved


def run(utterance: str, context: dict = None) -> dict:
    """
    Accepts a user utterance and optional context from the supervisor.

    context format:
        {
            "reference_date": "2026-06-16",
            "reference_day": "TUESDAY",
            "reference_time": "09:00:00"
        }

    Returns structured JSON with all temporal slots resolved to ISO format.
    """
    if context is None:
        ref_date = datetime.date.today()
        ref_time = datetime.datetime.now().time().replace(microsecond=0)
        ref_date_str = ref_date.strftime("%Y-%m-%d")
        ref_day_str = ref_date.strftime("%A")
    else:
        ref_date = datetime.date.fromisoformat(context["reference_date"])
        ref_time = datetime.time.fromisoformat(context["reference_time"])
        ref_date_str = context["reference_date"]
        ref_day_str = context.get("reference_day", ref_date.strftime("%A"))

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": get_system_prompt(ref_date_str, ref_day_str)},
            {"role": "user", "content": utterance},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps output
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except Exception:
        return {
            "intent": None,
            "sub_intent": None,
            "slots": {},
            "error": "Could not parse response. Query may be outside calendar domain.",
            "raw": raw
        }

    # Resolve all temporal slots
    result["slots"] = _resolve_slots(result["slots"], ref_date, ref_time)

    return result
