"""
Expanded test suite for resolve_datetime()
Covers every realistic expression a user might type.
"""
import datetime
from resolve_datetime import resolve_datetime

REF_DATE = datetime.date.today()
NOW      = datetime.datetime.now().replace(microsecond=0)
REF_TIME = NOW.time()

CATEGORIES = [
    # ── SECONDS ──────────────────────────────────────────────────────────────
    ("SECONDS", [
        "in 1 second",
        "in 5 seconds",
        "in 10 seconds",
        "in 30 seconds",
        "in 45 seconds",
        "in 60 seconds",
        "1 second from now",
        "5 seconds from now",
        "10 seconds from now",
        "30 seconds from now",
        "45 seconds from now",
        "a second from now",
        "one second from now",
        "5 seconds ago",
        "10 seconds ago",
        "30 seconds ago",
        "sixty seconds from now",
        "thirty seconds from now",
        "fifteen seconds from now",
    ]),

    # ── MINUTES ──────────────────────────────────────────────────────────────
    ("MINUTES", [
        "in 1 minute",
        "in 5 minutes",
        "in 10 minutes",
        "in 15 minutes",
        "in 20 minutes",
        "in 30 minutes",
        "in 45 minutes",
        "in 60 minutes",
        "in 90 minutes",
        "in 120 minutes",
        "1 minute from now",
        "5 minutes from now",
        "15 minutes from now",
        "30 minutes from now",
        "45 minutes from now",
        "60 minutes from now",
        "in a minute",
        "in half an hour",
        "a minute from now",
        "five minutes from now",
        "ten minutes from now",
        "fifteen minutes from now",
        "thirty two minutes from now",
        "one hundred twenty five minutes",
        "1 minute ago",
        "5 minutes ago",
        "10 minutes ago",
        "30 minutes ago",
        "45 minutes ago",
    ]),

    # ── HOURS ─────────────────────────────────────────────────────────────────
    ("HOURS", [
        "in 1 hour",
        "in 2 hours",
        "in 3 hours",
        "in 4 hours",
        "in 6 hours",
        "in 8 hours",
        "in 12 hours",
        "in 24 hours",
        "in 48 hours",
        "in 72 hours",
        "1 hour from now",
        "2 hours from now",
        "3 hours from now",
        "6 hours from now",
        "12 hours from now",
        "24 hours from now",
        "48 hours from now",
        "one hour from now",
        "two hours from now",
        "three hours from now",
        "in half a day",
        "1 hour ago",
        "2 hours ago",
        "3 hours ago",
        "6 hours ago",
        "12 hours ago",
        "24 hours ago",
        "one hundred twenty five hours",

    ]),

    # ── DAYS ──────────────────────────────────────────────────────────────────
    ("DAYS", [
        "today",
        "tomorrow",
        "yesterday",
        "in 1 day",
        "in 2 days",
        "in 3 days",
        "in 4 days",
        "in 5 days",
        "in 6 days",
        "in 7 days",
        "in 10 days",
        "in 14 days",
        "in 30 days",
        "in 60 days",
        "in 90 days",
        "1 day from now",
        "2 days from now",
        "3 days from now",
        "7 days from now",
        "10 days from now",
        "14 days from now",
        "30 days from now",
        "1 day ago",
        "2 days ago",
        "3 days ago",
        "5 days ago",
        "7 days ago",
        "10 days ago",
        "next day",
        "day after tomorrow",
        "day before yesterday",
        "in a day",
        "one day from now",
        "two days from now",
        "five days from now",
        "one hundred twenty five days",

    ]),

    # ── WEEKS ─────────────────────────────────────────────────────────────────
    ("WEEKS", [
        "next week",
        "last week",
        "this week",
        "in 1 week",
        "in 2 weeks",
        "in 3 weeks",
        "in 4 weeks",
        "in 6 weeks",
        "in 8 weeks",
        "in 12 weeks",
        "1 week from now",
        "2 weeks from now",
        "3 weeks from now",
        "4 weeks from now",
        "1 week ago",
        "2 weeks ago",
        "3 weeks ago",
        "4 weeks ago",
        "one week from now",
        "two weeks from now",
        "three weeks from now",
        "a week from now",
        "a week ago",
    ]),

    # ── MONTHS ────────────────────────────────────────────────────────────────
    ("MONTHS", [
        "next month",
        "last month",
        "this month",
        "in 1 month",
        "in 2 months",
        "in 3 months",
        "in 6 months",
        "in 12 months",
        "1 month from now",
        "2 months from now",
        "3 months from now",
        "6 months from now",
        "1 month ago",
        "2 months ago",
        "3 months ago",
        "one month from now",
        "two months from now",
        "a month from now",
    ]),

    # ── YEARS ─────────────────────────────────────────────────────────────────
    ("YEARS", [
        "next year",
        "last year",
        "in 1 year",
        "in 2 years",
        "in 5 years",
        "1 year from now",
        "2 years from now",
        "1 year ago",
        "2 years ago",
        "one year from now",
        "a year from now",
    ]),

    # ── WEEKDAYS (next) ───────────────────────────────────────────────────────
    ("NEXT WEEKDAY", [
        "next Monday",
        "next Tuesday",
        "next Wednesday",
        "next Thursday",
        "next Friday",
        "next Saturday",
        "next Sunday",
    ]),

    # ── WEEKDAYS + TIME ───────────────────────────────────────────────────────
    ("WEEKDAY + TIME", [
        "next Monday at 9am",
        "next Tuesday at 10:30",
        "next Wednesday at noon",
        "next Thursday at 2pm",
        "next Friday at 3pm",
        "next Saturday at 18:00",
        "next Sunday at midnight",
        "next Friday at 15:30",
        "next Monday at 8:00",
    ]),

    # ── TIME OF DAY ───────────────────────────────────────────────────────────
    ("TIME OF DAY", [
        "now",
        "right now",
        "this morning",
        "this afternoon",
        "this evening",
        "tonight",
        "eod",
        "end of day",
        "eom",
        "end of month",
        "end of week",
    ]),

    # ── TIME ONLY ─────────────────────────────────────────────────────────────
    ("TIME ONLY", [
        "at 6am",
        "at 7am",
        "at 8am",
        "at 9am",
        "at 10am",
        "at 11am",
        "at noon",
        "at 12pm",
        "at 1pm",
        "at 2pm",
        "at 3pm",
        "at 4pm",
        "at 5pm",
        "at 6pm",
        "at 9pm",
        "at 10pm",
        "at midnight",
        "at 00:00",
        "at 7:30",
        "at 14:00",
        "at 15:30",
        "at 22:00",
        "at 23:59",
    ]),

    # ── SPECIFIC DATES ────────────────────────────────────────────────────────
    ("SPECIFIC DATES", [
        "June 10",
        "June 28",
        "July 4",
        "August 15",
        "September 1",
        "October 31",
        "November 11",
        "December 25",
        "December 31",
        "January 1",
        "February 14",
        "March 21",
        "June 28 2026",
        "July 4 2026",
        "December 25 2026",
        "January 1 2027",
    ]),

    # ── CHAINED / OFFSET ─────────────────────────────────────────────────────
    ("CHAINED / OFFSET", [
        "1 day before July 4",
        "2 days before July 4",
        "3 days before June 28",
        "1 week before December 25",
        "2 weeks before December 25",
        "1 day after July 4",
        "2 days after July 4",
        "1 week after June 14",
        "2 weeks after June 14",
        "5 days after July 1",
        "3 days before August 1",
        "one week before Christmas",
    ]),

    # ── DATE + TIME COMBINED ─────────────────────────────────────────────────
    ("DATE + TIME", [
        "today at 9am",
        "today at noon",
        "today at 3pm",
        "today at midnight",
        "tomorrow at 8am",
        "tomorrow at 9am",
        "tomorrow at noon",
        "tomorrow at 3pm",
        "tomorrow at 9pm",
        "yesterday at 8am",
        "yesterday at noon",
        "in 2 days at 2pm",
        "in 3 days at 10am",
        "in 1 week at 9am",
        "next Monday at 10am",
        "tomorrow morning",
        "tomorrow afternoon",
        "tomorrow evening",
        "tomorrow noon",
        "tomorrow night",
        "tomorrow at 10:30AM",
        "today at 15:30",
        "in 5 days at 14:00",
    ]),

    # ── EDGE / TRICKY CASES ───────────────────────────────────────────────────
    ("EDGE CASES", [
        "in half an hour",
        "half an hour from now",
        "in half a day",
        "a minute from now",
        "a second from now",
        "a week from now",
        "a month from now",
        "a year from now",
        "day after tomorrow",
        "day before yesterday",
        "one day from now",
        "two days from now",
        "three weeks from now",
        "four months from now",
    ]),
        # ── ALIASES / INFORMAL SPELLING ───────────────────────────────────────────
    ("ALIASES / INFORMAL", [
        "tmr",
        "tmrw",
        "tmw",
        "yest",
        "tomoro",
        "tmr at 9am",
        "tmrw at noon",
        "tmw at 3pm",
        "a couple of days",
        "a couple of days from now",
        "christmas",
        "xmas",
        "one week before christmas",
        "one week before xmas",
        "new year",
        "new years",
    ]),

    # ── FRACTIONAL TIME ───────────────────────────────────────────────────────
    ("FRACTIONAL TIME", [
        "in half an hour",
        "half an hour from now",
        "in half a day",
        "half a day from now",
        "one and a half hours",
        "one and a half hours from now",
        "two and a half hours",
        "two and a half hours from now",
        "quarter past 3",
        "half past 9",
        "half past 12",
    ]),

    # ── LARGE NUMBERS (word + digit) ──────────────────────────────────────────
    ("LARGE NUMBERS", [
        "one hundred days from now",
        "one hundred twenty five days from now",
        "one hundred hours from now",
        "one hundred twenty five hours",
        "one hundred twenty five minutes",
        "one hundred days from now",
        "thirty one days from now",
        "fifty one minutes from now",
        "thirty seconds from now",
        "sixty seconds from now",
        "fifteen seconds from now",
        "thirty-one minutes from now",
    ]),

    # ── HYPHENATED NUMBERS ────────────────────────────────────────────────────
    ("HYPHENATED NUMBERS", [
        "thirty-one days from now",
        "twenty-two hours from now",
        "forty-five minutes from now",
        "thirty-one minutes from now",
        "twenty-four hours from now",
    ]),

    # ── "A / AN" BEFORE UNIT ──────────────────────────────────────────────────
    ("A / AN BEFORE UNIT", [
        "a second from now",
        "a minute from now",
        "an hour from now",
        "an hour from now",
        "a day from now",
        "a week from now",
        "a month from now",
        "a year from now",
        "in a second",
        "in a minute",
        "in an hour",
        "in a day",
        "in a week",
        "in a month",
        "in a year",
    ]),

    # ── THIS WEEK / THIS MONTH ────────────────────────────────────────────────
    ("THIS WEEK / MONTH", [
        "this week",
        "this month",
        "this morning",
        "this afternoon",
        "this evening",
        "this night",
        "this noon",
    ]),

    # ── CHAINED OFFSET — EXTRA ────────────────────────────────────────────────
    ("CHAINED OFFSET EXTRA", [
        "1 day before June 10",
        "3 days before August 1",
        "one week before Christmas",
        "two weeks before December 25",
        "1 day after July 4",
        "5 days after July 1",
        "2 weeks after June 14",
        "1 week after June 14",
        "3 days before June 28",
    ]),

    # ── SPECIFIC YEAR EXPLICIT ────────────────────────────────────────────────
    ("SPECIFIC YEAR EXPLICIT", [
        "June 28 2026",
        "July 4 2026",
        "December 25 2026",
        "January 1 2027",
        "March 15 2027",
        "October 10 2026",
    ]),

    # ── DAY AFTER / BEFORE VARIANTS ───────────────────────────────────────────
    ("DAY AFTER / BEFORE", [
        "day after tomorrow",
        "day before yesterday",
        "the day after tomorrow",
        "the day before yesterday",
    ]),

    ("Extra cases", [
        "1 week after next Sunday",
        "June 28th",
        "July 1st 2027",
        "in 1.5 hours",
        "in 2.5 days",

        "5 mins from now",
        "2 hrs from now",

        "next weekend",
        "this weekend",

        "tomorrow evening at 7",
        "tomorrow night at 10",

        "end of week",
        "start of month",

        "March 1 after February 28",
        "February 29 2028",

        "31 December",
        "25 December 2027",

        "in 1000 days",
        "in 5000 hours",
    ]),

    ("RECURRING", [
        "every day","every single day","every Monday","every Tuesday","every Friday",
        "every Saturday","every Sunday","every weekday","weekdays","every weekend",
        "every 2 weeks","every 3 days","every morning","every evening","every night",
        "every Monday at 9am","every Friday at 3pm","every Tuesday at 10:30",
    ]),
    ("AMBIGUOUS", [
        "May","in October","January","in March","in August",
    ]),
    ("EOB / BUSINESS", [
        "eob","end of business",
    ]),
    ("TIME-OF-DAY DEFAULTS", [
        "tomorrow morning","tomorrow afternoon","tomorrow evening","tomorrow night",
        "next Friday morning","next Monday afternoon","next Wednesday evening",
        "this morning","this afternoon","this evening",
    ]),
    ("A FEW / INFORMAL QUANTITY", [
        "a few days","a few hours","a few minutes","a few weeks",
        "a couple of days","a couple of hours",
    ]),

    ("RANGE EXPRESSIONS", [
        "this week",
        "this month",
        "this weekend",
        "weekend",
        "next weekend",
        "eow",
        "end of week",
        "eom",
        "end of month",
        "som",
        "start of month",
    ]),

    ("FEB 29 VALIDATION", [
        "february 29",
        "feb 29",
        "february 29 2028",
        "feb 29 2028",
        "february 29 2027",
        "feb 29 2027",
        "february 29 2100",
        "feb 29 2100",
        "february 29 2000",
        "feb 29 2000",
    ]),

]

# ─────────────────────────────────────────────────────────────────────────────
COL_EXPR   = 40
COL_DATE   = 14
COL_TIME   = 8
LINE_WIDTH = COL_EXPR + COL_DATE + COL_TIME + 12

def run():
    print("=" * LINE_WIDTH)
    print("  EXPANDED TEST SUITE — resolve_datetime()")
    print("=" * LINE_WIDTH)
    print(f"  Reference date : {REF_DATE}  ({REF_DATE.strftime('%A')})")
    print(f"  Reference time : {REF_TIME}")
    print("=" * LINE_WIDTH)

    total_pass = 0
    total_fail = 0
    summary    = []

    for title, exprs in CATEGORIES:
        print(f"\n{'─' * LINE_WIDTH}")
        print(f"  {title}  ({len(exprs)} expressions)")
        print(f"{'─' * LINE_WIDTH}")
        print(f"  {'Expression':<{COL_EXPR}} {'Date':<{COL_DATE}} {'Time':<{COL_TIME}} Status")
        print(f"  {'-' * (LINE_WIDTH-2)}")

        p = f = 0
        for expr in exprs:
            r = resolve_datetime(expr, REF_DATE, REF_TIME)
            ok = r["status"] in ("ok", "ambiguous") or r.get("recurring", False)
            p += ok; f += (not ok)
            flag = "  !" if not ok else ""
            start = r.get('date_start') or '-'
            end   = r.get('date_end') or '-'
            rng   = start if start == end else f"{start}~{end}"
            msg   = f" [{r.get('message','')}]" if r.get('message') else ""
            print(f"  {expr:<{COL_EXPR}} {rng:<{COL_DATE}} {r['time'] or '-':<{COL_TIME}} {r['status']}{flag}{msg}")
        total_pass += p; total_fail += f
        summary.append((title, p, f, len(exprs)))

    # summary
    print(f"\n\n{'=' * LINE_WIDTH}")
    print("  SUMMARY")
    print(f"{'=' * LINE_WIDTH}")
    print(f"  {'Category':<30} {'Pass':>5} {'Fail':>5} {'Total':>6}")
    print(f"  {'-' * (LINE_WIDTH-2)}")
    for t, p, f, total in summary:
        flag = "  ← FAILURES" if f else ""
        print(f"  {t:<30} {p:>5} {f:>5} {total:>6}{flag}")
    print(f"  {'-' * (LINE_WIDTH-2)}")
    grand = total_pass + total_fail
    print(f"  {'TOTAL':<30} {total_pass:>5} {total_fail:>5} {grand:>6}")
    print(f"{'=' * LINE_WIDTH}")
    pct = total_pass / grand * 100 if grand else 0
    print(f"\n  Pass rate: {total_pass}/{grand}  ({pct:.1f}%)")
    print()

if __name__ == "__main__":
    run()