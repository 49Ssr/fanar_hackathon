# TimeTask Agent

Bilingual Arabic/English calendar subagent for the Fanar national AI platform.  
Developed at QCRI (Qatar Computing Research Institute), Summer 2026.  
Developers: Ouaisse Lkherba, Rahaf Sabra, Mohamed Altaf

---

## What it does

Takes a user utterance in English and returns structured JSON containing:

- **Intent** (Add, Reschedule, Delete, Deadline, Reminder, Query, Check Availability)
- **Sub-intent** (Meeting, Event, Task/To-do, Recurring, etc.)
- **Slots** (title, date, time, location, attendees, etc.)
- All dates resolved dynamically to ISO format (YYYY-MM-DD)
- All times in 24-hour format (HH:MM)

---

## How to integrate

This agent is called by the supervisor agent, not run standalone.

```python
from timetask_agent import run

context = {
    "reference_date": "2026-06-17",
    "reference_day": "Wednesday",
    "reference_time": "09:00:00"
}

result = run("Schedule a meeting with Sara next Monday at 3pm", context)
```

The `context` object is required. It tells the agent what the current date and time are, so all relative expressions ("next Monday", "in 3 days") resolve correctly.

If `context` is omitted, the agent falls back to the machine's current date and time.

---

## Output format

### Successful request

```json
{
  "intent": "Add",
  "sub_intent": "Meeting",
  "slots": {
    "title": "Meeting with Sara",
    "date": "2026-06-22",
    "time": "15:00",
    "duration": null,
    "location": null,
    "attendees": ["Sara"],
    "action": "ADD"
  }
}
```

### Out-of-domain request

If the user query is not a calendar request, the agent returns a clean error instead of crashing:

```json
{
  "intent": null,
  "sub_intent": null,
  "slots": {},
  "error": "Could not parse response. Query may be outside calendar domain.",
  "raw": "Today is Wednesday, June 17, 2026."
}
```

---

## Taxonomy

| Intent | Sub-intents |
|---|---|
| Add | Meeting, Event, Task/To-do, Recurring |
| Reschedule | Move time, Move date, Change venue |
| Delete | Cancel event, Remove task |
| Deadline | Set deadline, Update deadline |
| Reminder | Before event, Alert approaching |
| Query | Today's tasks, Daily summary, This week, Specific event, This month |
| Check Availability | Free slot, Conflict check |

---

## Setup
```
pip install -r requirements.txt
```

Create a `.env` file in this folder:
```
FANAR_API_KEY=your_key_here
```

---

## Folder structure
```
timetask_agent/
├── README.md                        ← you are here
├── timetask_agent.py                ← main agent, called by supervisor
├── requirements.txt                 ← dependencies
├── datetime/
│   ├── resolve_datetime.py          ← converts natural language dates to ISO format
│   └── test_resolve_datetime.py     ← 96/96 test cases passing
└── dataset/
    ├── timetask_combined_v3.json    ← 1507 bilingual training examples
    └── README.md                    ← explains the dataset
```

---

## Dependencies

- `openai` — Fanar API client
- `parsedatetime` — natural language date parsing
- `word2number` — converts written numbers to digits ("thirty minutes" → 30)
- `python-dotenv` — loads API key from `.env` file
