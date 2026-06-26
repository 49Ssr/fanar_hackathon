"""
Comprehensive test for resolve_datetime() across all expression categories.

Reference used: today's date + real current time (no-microsecond).
Seconds, minutes, and hours expressions are therefore calculated from
the actual time the test is run.

Run:
    python test_resolve_datetime.py
"""

import datetime
from resolve_datetime import resolve_datetime

# ── Reference values ──────────────────────────────────────────────────────────
REF_DATE = datetime.date.today()
NOW      = datetime.datetime.now().replace(microsecond=0)
REF_TIME = NOW.time()   # passed to resolve_datetime for accurate time-relative results

# ── Test data ─────────────────────────────────────────────────────────────────
CATEGORIES = [
    ("1. Seconds", [
        "in 30 seconds",
        "in 5 seconds",
        "30 seconds from now",
        "5 seconds from now",
        "5 seconds ago",
        "thirty seconds from now",
        "a second from now",
        "in 1 second",
    ]),
    ("2. Minutes", [
        "in 5 minutes",
        "in 30 minutes",
        "5 minutes from now",
        "30 minutes from now",
        "30 minutes ago",
        "five minutes from now",
        "in a minute",
        "1 minute ago",
    ]),
    ("3. Hours", [
        "in 1 hour",
        "in 3 hours",
        "1 hour from now",
        "3 hours from now",
        "3 hours ago",
        "in half an hour",
        "one hour from now",
        "in 2 hours",
    ]),
    ("4. Days", [
        "today",
        "tomorrow",
        "yesterday",
        "in 3 days",
        "in 7 days",
        "3 days ago",
        "5 days from now",
        "next day",
    ]),
    ("5. Weeks", [
        "next week",
        "last week",
        "in 1 week",
        "in 2 weeks",
        "1 week from now",
        "2 weeks from now",
        "2 weeks ago",
        "1 week ago",
    ]),
    ("6. All 7 Weekdays — next [weekday]", [
        "next Monday",
        "next Tuesday",
        "next Wednesday",
        "next Thursday",
        "next Friday",
        "next Saturday",
        "next Sunday",
    ]),
    ("7. Weekdays with Time", [
        "next Friday at 3pm",
        "next Monday at 9am",
        "next Wednesday at 14:30",
        "next Sunday at noon",
        "next Thursday at 8:00",
        "next Tuesday at 11am",
        "next Saturday at 18:00",
    ]),
    ("8. End of Period", [
        "eod",
        "eom",
        "end of day",
        "end of month",
        "end of week",
        "right now",
        "now",
    ]),
    ("9. Specific Dates", [
        "June 28",
        "June 28 2026",
        "December 31",
        "January 1",
        "July 4",
        "August 15",
        "September 1 2026",
    ]),
    ("10. Chained / Offset Expressions", [
        "3 days before June 28",
        "2 weeks after June 14",
        "1 day before July 4",
        "one week after June 28",
        "5 days after July 1",
        "2 days before August 1",
    ]),
    ("11. Natural Time Language", [
        "tomorrow morning",
        "tomorrow noon",
        "tomorrow night",
        "this evening",
        "tonight",
        "this morning",
        "this afternoon",
    ]),
    ("12. Time Only", [
        "at 3pm",
        "at 9am",
        "at 15:00",
        "at 00:00",
        "at noon",
        "at midnight",
        "at 7:30",
        "at 22:00",
    ]),
    ("13. Date + Time Combined", [
        "tomorrow at 9am",
        "today at 3pm",
        "next Monday at 10am",
        "in 2 days at 2pm",
        "this Friday at 15:00",
        "yesterday at 8am",
        "today at midnight",
    ]),
]

# ── Runner ────────────────────────────────────────────────────────────────────
COL_EXPR   = 38
COL_DATE   = 14
COL_TIME   = 8
COL_STATUS = 6
LINE_WIDTH = COL_EXPR + COL_DATE + COL_TIME + COL_STATUS + 6


def run_category(title, expressions):
    print(f"\n{'=' * LINE_WIDTH}")
    print(f"  {title}")
    print(f"{'=' * LINE_WIDTH}")
    print(f"{'Expression':<{COL_EXPR}} {'Date':<{COL_DATE}} {'Time':<{COL_TIME}} Status")
    print(f"{'-' * LINE_WIDTH}")

    passed = 0
    failed = 0
    for expr in expressions:
        r = resolve_datetime(expr, REF_DATE, REF_TIME)
        if r["status"] == "ok":
            passed += 1
            marker = ""
        else:
            failed += 1
            marker = " !"
        date_val = r["date_start"] or "-"
        time_val = r["time"] or "-"
        print(f"{expr:<{COL_EXPR}} {date_val:<{COL_DATE}} {time_val:<{COL_TIME}} {r['status']}{marker}")

    return passed, failed


def main():
    print("=" * LINE_WIDTH)
    print("  resolve_datetime — Comprehensive Test Suite")
    print("=" * LINE_WIDTH)
    print(f"  Reference date : {REF_DATE}  ({REF_DATE.strftime('%A')})")
    print(f"  Reference time : {REF_TIME}  (real current time — no microseconds)")
    print(f"  Note           : seconds/minutes/hours expressions are calculated")
    print(f"                   from the actual time shown above, not midnight")
    print("=" * LINE_WIDTH)

    totals_passed = 0
    totals_failed = 0
    summary_rows  = []

    for title, expressions in CATEGORIES:
        p, f = run_category(title, expressions)
        totals_passed += p
        totals_failed += f
        summary_rows.append((title, p, f, len(expressions)))

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n\n{'=' * LINE_WIDTH}")
    print("  SUMMARY")
    print(f"{'=' * LINE_WIDTH}")
    print(f"{'Category':<45} {'Pass':>5} {'Fail':>5} {'Total':>6}")
    print(f"{'-' * LINE_WIDTH}")
    for title, p, f, total in summary_rows:
        flag = "  <-- has failures" if f > 0 else ""
        print(f"{title:<45} {p:>5} {f:>5} {total:>6}{flag}")
    print(f"{'-' * LINE_WIDTH}")
    grand_total = totals_passed + totals_failed
    print(f"{'TOTAL':<45} {totals_passed:>5} {totals_failed:>5} {grand_total:>6}")
    print(f"{'=' * LINE_WIDTH}")
    pct = (totals_passed / grand_total * 100) if grand_total else 0
    print(f"\n  Pass rate: {totals_passed}/{grand_total} ({pct:.1f}%)")
    if totals_failed == 0:
        print("  All expressions resolved successfully.")
    else:
        print(f"  {totals_failed} expression(s) failed to resolve (marked with !).")
    print()


if __name__ == "__main__":
    main()
