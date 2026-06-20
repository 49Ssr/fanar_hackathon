import sys
import io
import os
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from timetask_agent import run

# ── Test cases ────────────────────────────────────────────────────────────────
# Each test has:
#   lang, intent, sub_intent, utterance, expected_slots (None = should be null, "ANY" = any non-null value)

tests = [
    # English
    {
        "lang": "EN", "intent": "Add", "sub_intent": "Meeting",
        "utterance": "Schedule a meeting with Sara next Monday at 3pm",
        "expected_slots": {
            "title": "ANY", "date": "ANY", "time": "15:00",
            "duration": None, "location": None, "attendees": "ANY", "action": "ADD"
        }
    },
    {
        "lang": "EN", "intent": "Reschedule", "sub_intent": "Move date",
        "utterance": "Move my team meeting to Friday at 10am",
        "expected_slots": {
            "title": "ANY", "new_date": "ANY", "new_time": "10:00",
            "new_location": None, "reason": None, "action": "UPDATE"
        }
    },
    {
        "lang": "EN", "intent": "Delete", "sub_intent": "Cancel event",
        "utterance": "Cancel my dentist appointment on Monday",
        "expected_slots": {
            "title": "ANY", "date": "ANY", "confirm": True, "action": "DELETE"
        }
    },
    {
        "lang": "EN", "intent": "Deadline", "sub_intent": "Set deadline",
        "utterance": "My report is due next Sunday, remind me 2 days before",
        "expected_slots": {
            "title": "ANY", "deadline_date": "ANY", "deadline_time": None,
            "remind_before": 2880, "action": "SET_DEADLINE"
        }
    },
    {
        "lang": "EN", "intent": "Reminder", "sub_intent": "Before event",
        "utterance": "Remind me 30 minutes before the team call",
        "expected_slots": {
            "title": "ANY", "remind_before": 30, "repeat": False, "action": "SET_REMINDER"
        }
    },
    {
        "lang": "EN", "intent": "Query", "sub_intent": "This week",
        "utterance": "What do I have this week?",
        "expected_slots": {
            "title": None, "date": None, "action": "QUERY"
        }
    },
    {
        "lang": "EN", "intent": "Check Availability", "sub_intent": "Free slot",
        "utterance": "Am I free on Thursday afternoon?",
        "expected_slots": {
            "title": None, "date": "ANY", "time": None, "duration": None, "action": "CHECK"
        }
    },
    # Arabic
    {
        "lang": "AR", "intent": "Add", "sub_intent": "Meeting",
        "utterance": "حدد اجتماعاً مع سارة الاثنين القادم الساعة الثالثة",
        "expected_slots": {
            "title": "ANY", "date": "ANY", "time": "15:00",
            "duration": None, "location": None, "attendees": "ANY", "action": "ADD"
        }
    },
    {
        "lang": "AR", "intent": "Reschedule", "sub_intent": "Move date",
        "utterance": "حوّل اجتماع الفريق إلى يوم الجمعة الساعة العاشرة",
        "expected_slots": {
            "title": "ANY", "new_date": "ANY", "new_time": "10:00",
            "new_location": None, "reason": None, "action": "UPDATE"
        }
    },
    {
        "lang": "AR", "intent": "Delete", "sub_intent": "Cancel event",
        "utterance": "ألغِ موعد طبيب الأسنان يوم الاثنين",
        "expected_slots": {
            "title": "ANY", "date": "ANY", "confirm": True, "action": "DELETE"
        }
    },
    {
        "lang": "AR", "intent": "Deadline", "sub_intent": "Set deadline",
        "utterance": "تقريري يُسلَّم الأحد القادم، ذكّرني قبلها بيومين",
        "expected_slots": {
            "title": "ANY", "deadline_date": "ANY", "deadline_time": None,
            "remind_before": 2880, "action": "SET_DEADLINE"
        }
    },
    {
        "lang": "AR", "intent": "Reminder", "sub_intent": "Before event",
        "utterance": "ذكّرني قبل نصف ساعة من اجتماع الفريق",
        "expected_slots": {
            "title": "ANY", "remind_before": 30, "repeat": False, "action": "SET_REMINDER"
        }
    },
    {
        "lang": "AR", "intent": "Query", "sub_intent": "This week",
        "utterance": "ماذا عندي هذا الأسبوع؟",
        "expected_slots": {
            "title": None, "date": None, "action": "QUERY"
        }
    },
    {
        "lang": "AR", "intent": "Check Availability", "sub_intent": "Free slot",
        "utterance": "هل أنا حر يوم الخميس بعد الظهر؟",
        "expected_slots": {
            "title": None, "date": "ANY", "time": None, "duration": None, "action": "CHECK"
        }
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
import re

def is_valid_date(val):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(val))) if val else False

def is_valid_time(val):
    return bool(re.match(r"^\d{2}:\d{2}$", str(val))) if val else False

DATE_SLOT_NAMES = {"date", "new_date", "deadline_date"}
TIME_SLOT_NAMES = {"time", "new_time", "deadline_time"}

def check_slot(key, expected, actual):
    issues = []
    if expected == "ANY":
        if actual is None:
            issues.append(f"❌ {key}: null (expected a value)")
        else:
            if key in DATE_SLOT_NAMES:
                if not is_valid_date(actual):
                    issues.append(f"❌ {key}: '{actual}' (invalid date format, expected YYYY-MM-DD)")
                else:
                    issues.append(f"⬜ {key}: \"{actual}\" (format ok — value not verified, date resolution pending)")
            elif key in TIME_SLOT_NAMES:
                if not is_valid_time(actual):
                    issues.append(f"❌ {key}: '{actual}' (invalid time format, expected HH:MM)")
                else:
                    issues.append(f"⬜ {key}: \"{actual}\" (format ok — value not verified, date resolution pending)")
            else:
                issues.append(f"✅ {key}: {json.dumps(actual, ensure_ascii=False)}")
    elif expected is None:
        if actual is not None:
            issues.append(f"❌ {key}: '{actual}' (expected null)")
        else:
            issues.append(f"✅ {key}: null")
    else:
        if actual != expected:
            issues.append(f"❌ {key}: '{actual}' (expected '{expected}')")
        else:
            issues.append(f"✅ {key}: {json.dumps(actual, ensure_ascii=False)}")
    return issues

# ── Run tests ─────────────────────────────────────────────────────────────────
total_tests = len(tests)
total_passed = 0
total_failed = 0

print(f"Running {total_tests} tests — 7 English + 7 Arabic")
print("=" * 60)

for t in tests:
    print(f"\n[{t['lang']}] {t['intent']} — {t['utterance']}")
    test_passed = True
    try:
        result = run(t["utterance"])
        actual_intent = result.get("intent", "MISSING")
        actual_sub = result.get("sub_intent", "MISSING")
        actual_slots = result.get("slots", {})

        lines = []

        # Check intent
        if actual_intent == t["intent"]:
            lines.append(f"  ✅ intent: {actual_intent}")
        else:
            lines.append(f"  ❌ intent: '{actual_intent}' (expected '{t['intent']}')")
            test_passed = False

        # Check sub_intent
        if actual_sub == t["sub_intent"]:
            lines.append(f"  ✅ sub_intent: {actual_sub}")
        else:
            lines.append(f"  ❌ sub_intent: '{actual_sub}' (expected '{t['sub_intent']}')")
            test_passed = False

        # Check slots
        for key, expected_val in t["expected_slots"].items():
            actual_val = actual_slots.get(key, "MISSING")
            if actual_val == "MISSING":
                lines.append(f"  ❌ {key}: MISSING from output")
                test_passed = False
            else:
                slot_lines = check_slot(key, expected_val, actual_val)
                for sl in slot_lines:
                    lines.append(f"  {sl}")
                    if sl.startswith("  ❌") or sl.startswith("❌"):
                        test_passed = False

        for l in lines:
            print(l)

        if test_passed:
            total_passed += 1
            print(f"  → PASS")
        else:
            total_failed += 1
            print(f"  → FAIL")

    except Exception as e:
        total_failed += 1
        print(f"  ERROR: {e}")
        print(f"  → FAIL")

    print("-" * 60)

print(f"\nFinal Results: {total_passed}/{total_tests} passed")
if total_failed > 0:
    print(f"  {total_failed} test(s) need attention — review ❌ lines above")
else:
    print(f"  All tests passed ✅")
