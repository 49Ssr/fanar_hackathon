"""
resolve_datetime.py
-------------------
Converts natural language temporal expressions into structured date/time dicts.

Input:
    expression (str): e.g. "next Monday", "3 days before June 28", "tomorrow at 9am"
    reference_date (datetime.date, optional) — defaults to today
    reference_time (datetime.time, optional) — defaults to current time

Output (all results share this schema):
    {
        "date_start": "YYYY-MM-DD" or None,
        "date_end":   "YYYY-MM-DD" or None,   # equals date_start for single-day results
        "time":       "HH:MM"      or None,
        "status":     "ok" | "failed" | "ambiguous",
        "expression": "original input",
        # optional fields present only when relevant:
        "recurring":  bool,
        "recurrence": str or None,
        "needs":      list or None,
        "message":    str   (only on failed results with extra context)
    }

Gulf calendar assumptions:
    - Work week : Sunday - Thursday
    - Weekend   : Friday - Saturday
    - "this week"    -> Sunday to Thursday of the current work week
    - "end of week"  -> Thursday 23:59
    - "this weekend" -> coming Friday + Saturday (as a range)

Dependencies: parsedatetime, word2number
"""
import parsedatetime
import datetime
import re
import calendar
from word2number import w2n

constants = parsedatetime.Constants()
constants.DOWParseStyle = 1
cal = parsedatetime.Calendar(constants)

PAST_EXPRESSIONS = {"yesterday", "last week", "last month", "last year"}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS   = ["january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december"]

_NUMBER_TOKENS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
}

_TIME_UNITS = {
    "second", "seconds", "minute", "minutes", "hour", "hours",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
}

_ALIASES = {
    r'\btmr\b':               'tomorrow',
    r'\btmrw\b':              'tomorrow',
    r'\btmw\b':               'tomorrow',
    r'\btomoro\b':            'tomorrow',
    r'\byest\b':              'yesterday',
    r'\bchristmas\b':         'December 25',
    r'\bxmas\b':              'December 25',
    r"\bnew\s+year'?s?\b":   'January 1',
    r'\ba\s+couple\s+of\b':  '2',
    r'\ba\s+few\b':           '3',
    r'\beob\b':               'end of business',
    r'\bhrs\b':               'hours',
    r'\bhr\b':                'hour',
}

_DAY_AFTER_TOMORROW   = re.compile(r'\bday\s+after\s+tomorrow\b',   re.IGNORECASE)
_DAY_BEFORE_YESTERDAY = re.compile(r'\bday\s+before\s+yesterday\b', re.IGNORECASE)

_THIS_WEEK_RE       = re.compile(r'^this\s+week$',           re.IGNORECASE)
_THIS_MONTH_RE      = re.compile(r'^this\s+month$',          re.IGNORECASE)
_THIS_WEEKEND_RE    = re.compile(r'^this\s+weekend$',        re.IGNORECASE)
_NEXT_WEEKEND_RE    = re.compile(r'^next\s+weekend$',        re.IGNORECASE)
_WEEKEND_RE         = re.compile(r'^weekend$',               re.IGNORECASE)
_END_OF_WEEK_RE     = re.compile(r'^(eow|end\s+of\s+week)$',    re.IGNORECASE)
_START_OF_MONTH_RE  = re.compile(r'^(som|start\s+of\s+month)$', re.IGNORECASE)
_END_OF_MONTH_RE    = re.compile(r'^(eom|end\s+of\s+month)$',   re.IGNORECASE)
_END_OF_BUSINESS_RE = re.compile(r'^(eob|end\s+of\s+business)$', re.IGNORECASE)

_HALF_HOUR_RE = re.compile(r'\bhalf\s+an?\s+hour\b',    re.IGNORECASE)
_HALF_DAY_RE  = re.compile(r'\bhalf\s+a\s+day\b',       re.IGNORECASE)
_ONE_HALF_RE  = re.compile(r'\bone\s+and\s+a\s+half\b', re.IGNORECASE)
_TWO_HALF_RE  = re.compile(r'\btwo\s+and\s+a\s+half\b', re.IGNORECASE)

_HAS_YEAR_RE = re.compile(r'\b\d{4}\b')

_TODAY_TIME_OF_DAY = ("morning", "afternoon", "evening", "night", "noon")

# Feb 29 detector: "feb 29", "february 29", optionally followed by a 4-digit year
_FEB29_RE = re.compile(r'\bfeb(?:ruary)?\s+29\b(?:\s+(\d{4}))?', re.IGNORECASE)

_TOD_DEFAULTS = {
    "morning":          "09:00",
    "afternoon":        "14:00",
    "evening":          "18:00",
    "night":            "21:00",
    "tonight":          "21:00",
    "noon":             "12:00",
    "midnight":         "00:00",
    "eod":              "23:59",
    "end of day":       "23:59",
    "eob":              "17:00",
    "end of business":  "17:00",
    "later":            "12:00",
}

_TOD_AT_HOUR_RE = re.compile(
    r'\b(?:this\s+)?(morning|afternoon|evening|night|tonight)\s+at\s+(\d{1,2})(:\d{2})?\b',
    re.IGNORECASE
)
_TOD_AMPM = {
    "morning":  "am",
    "afternoon": "pm",
    "evening":  "pm",
    "night":    "pm",
    "tonight":  "pm",
}

def _tod_at_hour_sub(match):
    period  = match.group(1).lower()
    hour    = match.group(2)
    minutes = match.group(3) or ""
    return f"{hour}{minutes}{_TOD_AMPM[period]}"


_RECURRING_PATTERNS = [
    (re.compile(r'^every\s+(single\s+)?day$', re.I),
     lambda m, ref: ("daily", None)),

    (re.compile(r'^(every\s+)?weekdays?$', re.I),
     lambda m, ref: ("weekdays", None)),

    # Gulf weekend = Friday + Saturday
    (re.compile(r'^every\s+weekends?$', re.I),
     lambda m, ref: ("weekly:friday,saturday", None)),

    (re.compile(r'^every\s+(' + '|'.join(WEEKDAYS) + r')$', re.I),
     lambda m, ref: (f"weekly:{m.group(1).lower()}", None)),

    (re.compile(
        r'^every\s+(' + '|'.join(WEEKDAYS) + r')\s+at\s+(\d{1,2}(?::\d{2})?(?:am|pm)?)$',
        re.I),
     lambda m, ref: (f"weekly:{m.group(1).lower()}", m.group(2))),

    (re.compile(r'^every\s+(\d+)\s+(day|days|week|weeks)$', re.I),
     lambda m, ref: (f"every_{m.group(1)}_{m.group(2).rstrip('s')}", None)),

    (re.compile(r'^every\s+(morning|afternoon|evening|night)\b', re.I),
     lambda m, ref: ("daily", _TOD_DEFAULTS.get(m.group(1).lower()))),
]

_REL_TO_NEXT_WEEKDAY_RE = re.compile(
    r'^(\d+)\s+(day|days|week|weeks)\s+(after|before)\s+next\s+('
    + '|'.join(WEEKDAYS) + r')$'
)

_MONTH_ONLY_RE = re.compile(
    r'^(?:in\s+)?(' + '|'.join(MONTHS) + r')$',
    re.I
)


# ─────────────────────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean(expr):
    return expr.strip().lower()


def _tokenize(text):
    s = re.sub(r'(\d),(\d)', r'\1\2', text)
    s = s.replace('-', ' ')
    return re.findall(r'\d+\.\d+|\d+:\d+|\d+[ap]m|\b\w+\b', s.lower())


def is_past_expression(expr):
    e = _clean(expr)
    if e in PAST_EXPRESSIONS or e.endswith("ago"):
        return True
    return any(e.startswith(pw) for pw in PAST_EXPRESSIONS)


def has_absolute_month(expr):
    words = set(re.findall(r'\b\w+\b', _clean(expr)))
    return bool(words & set(MONTHS))


def get_next_weekday(weekday_name, reference_date, force_next_week=True):
    target     = WEEKDAYS.index(_clean(weekday_name))
    days_ahead = (target - reference_date.weekday()) % 7
    if force_next_week and days_ahead == 0:
        days_ahead = 7
    return reference_date + datetime.timedelta(days=days_ahead)


def get_weekend_friday(reference_date, next_week=False):
    """Returns the upcoming Friday (Gulf weekend start). Python Friday = weekday 4."""
    friday     = 4
    days_ahead = (friday - reference_date.weekday()) % 7
    if next_week:
        if days_ahead == 0:
            days_ahead = 7
        days_ahead += 7
    return reference_date + datetime.timedelta(days=days_ahead)


def is_next_weekday_expr(expr):
    """Returns the weekday name if expression is 'next [weekday]', else None."""
    e = _clean(expr)
    if not e.startswith("next "):
        return None
    parts = e.split()
    return parts[1] if len(parts) >= 2 and parts[1] in WEEKDAYS else None


def _get_this_week_range(reference_date):
    """
    Gulf work week: Sunday -> Thursday.
    Python weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    Walk back to the most recent Sunday, then forward 4 days to Thursday.
    """
    wd = reference_date.weekday()
    days_since_sunday = (wd - 6) % 7       # 0 when today is Sunday
    week_sunday   = reference_date - datetime.timedelta(days=days_since_sunday)
    week_thursday = week_sunday + datetime.timedelta(days=4)
    return week_sunday, week_thursday


def _get_this_month_range(reference_date):
    """Returns (first_day, last_day) of current month — fully leap-year aware."""
    first        = reference_date.replace(day=1)
    last_day_num = calendar.monthrange(reference_date.year, reference_date.month)[1]
    last         = reference_date.replace(day=last_day_num)
    return first, last


def _check_feb29(expression, reference_date):
    """
    If the expression explicitly requests Feb 29, validate the target year.
    Returns a failed _make_result dict when invalid, else None.
    """
    m = _FEB29_RE.search(_clean(expression))
    if not m:
        return None
    year_str = m.group(1)
    year     = int(year_str) if year_str else reference_date.year

    if not calendar.isleap(year):
        if year_str:
            msg = f"{year} is not a leap year — February 29 does not exist in {year}."
        else:
            next_leap = year + 1
            while not calendar.isleap(next_leap):
                next_leap += 1
            msg = (f"{year} is not a leap year — February 29 does not exist. "
                   f"Next occurrence: {next_leap}-02-29.")
        return _make_result(status="failed", expression=expression, message=msg)

    return None   # valid leap year — proceed normally


# ─────────────────────────────────────────────────────────────────────────────
# Result builder
# ─────────────────────────────────────────────────────────────────────────────

def _make_result(date_start=None, date_end=None, time=None, status="ok",
                 expression="", recurring=False, recurrence=None,
                 needs=None, message=None):
    """
    Unified result builder.
    - Single-day results: pass only date_start; date_end mirrors it automatically.
    - Range results: caller passes distinct date_start and date_end.
    """
    if date_start and not date_end:
        date_end = date_start

    result = {
        "date_start":  date_start,
        "date_end":    date_end,
        "time":        time,
        "status":      status,
        "needs":       needs,
        "recurring":   recurring,
        "recurrence":  recurrence,
        "expression":  expression,
    }
    if message:
        result["message"] = message
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Number-phrase normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _convert_number_phrases(text):
    tokens = _tokenize(text)
    result = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok in ("a", "an"):
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else ""
            if next_tok in _TIME_UNITS:
                result.append("1")
                i += 1
                continue

        if tok in _NUMBER_TOKENS:
            span = [tok]
            j    = i + 1
            while j < len(tokens):
                t = tokens[j]
                if t in _NUMBER_TOKENS:
                    span.append(t); j += 1
                elif (t == "and" and j + 1 < len(tokens)
                      and tokens[j + 1] in _NUMBER_TOKENS):
                    span.append(t); j += 1
                else:
                    break
            while span and span[-1] == "and":
                span.pop()
            if span:
                try:
                    num = w2n.word_to_num(" ".join(span))
                    result.append(str(int(num)) if float(num).is_integer() else str(num))
                    i = j
                    continue
                except Exception:
                    pass

        result.append(tok)
        i += 1
    return " ".join(result)


def _normalize(expression):
    s = _clean(expression)
    s = _ONE_HALF_RE.sub("1.5", s)
    s = _TWO_HALF_RE.sub("2.5", s)
    s = _HALF_HOUR_RE.sub("30 minutes", s)
    s = _HALF_DAY_RE.sub("12 hours", s)
    s = re.sub(r'\bquarter\s+past\s+(\d+)\b', lambda m: f"{m.group(1)}:15", s)
    s = re.sub(r'\bhalf\s+past\s+(\d+)\b',    lambda m: f"{m.group(1)}:30", s)
    for pattern, replacement in _ALIASES.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
    s = _DAY_AFTER_TOMORROW.sub("in 2 days", s)
    s = _DAY_BEFORE_YESTERDAY.sub("2 days ago", s)
    s = _TOD_AT_HOUR_RE.sub(_tod_at_hour_sub, s)
    s = _convert_number_phrases(s)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Main resolver
# ─────────────────────────────────────────────────────────────────────────────

def resolve_datetime(expression, reference_date=None, reference_time=None):
    """
    Resolves a natural language temporal expression to an exact date and/or time.

    Args:
        expression     : str           — e.g. "next Monday at 9am", "this week"
        reference_date : datetime.date — anchor date  (defaults to today)
        reference_time : datetime.time — anchor time  (defaults to 00:00:00)

    Returns a result dict — see module docstring for full schema.
    """
    if reference_date is None:
        reference_date = datetime.date.today()
    if reference_time is None:
        reference_time = datetime.time(0, 0, 0)

    expr_stripped = expression.strip()
    ref_dt  = datetime.datetime.combine(reference_date, reference_time)
    e_clean = _clean(expr_stripped)

    # 1. Feb 29 validation (fast-fail before any parsing)
    feb29_fail = _check_feb29(expr_stripped, reference_date)
    if feb29_fail:
        return feb29_fail

    # 2. Recurring expressions
    for pattern, extractor in _RECURRING_PATTERNS:
        m = pattern.match(e_clean)
        if m:
            recurrence, default_time = extractor(m, reference_date)
            return _make_result(
                time=default_time, expression=expression,
                recurring=True, recurrence=recurrence,
            )

    # 3. Ambiguous month-only (e.g. "in May")
    if _MONTH_ONLY_RE.match(e_clean):
        return _make_result(status="ambiguous", needs=["day"], expression=expression)

    # 4. Range: this week -> Gulf Sunday - Thursday
    if _THIS_WEEK_RE.match(e_clean):
        sun, thu = _get_this_week_range(reference_date)
        return _make_result(
            date_start=sun.strftime("%Y-%m-%d"),
            date_end=thu.strftime("%Y-%m-%d"),
            expression=expression,
        )

    # 5. Range: this month -> 1st - last (leap-year aware)
    if _THIS_MONTH_RE.match(e_clean):
        first, last = _get_this_month_range(reference_date)
        return _make_result(
            date_start=first.strftime("%Y-%m-%d"),
            date_end=last.strftime("%Y-%m-%d"),
            expression=expression,
        )

    # 6. Range: this weekend / weekend -> Friday - Saturday (Gulf)
    if _THIS_WEEKEND_RE.match(e_clean) or _WEEKEND_RE.match(e_clean):
        friday   = get_weekend_friday(reference_date)
        saturday = friday + datetime.timedelta(days=1)
        return _make_result(
            date_start=friday.strftime("%Y-%m-%d"),
            date_end=saturday.strftime("%Y-%m-%d"),
            expression=expression,
        )

    # 7. Range: next weekend -> following Friday - Saturday
    if _NEXT_WEEKEND_RE.match(e_clean):
        friday   = get_weekend_friday(reference_date, next_week=True)
        saturday = friday + datetime.timedelta(days=1)
        return _make_result(
            date_start=friday.strftime("%Y-%m-%d"),
            date_end=saturday.strftime("%Y-%m-%d"),
            expression=expression,
        )

    # 8. Single day + time: end of week / eow -> Thursday 23:59
    if _END_OF_WEEK_RE.match(e_clean):
        wd = reference_date.weekday()           # Mon=0 Thu=3 Sun=6
        days_until_thursday = (3 - wd) % 7
        thursday = reference_date + datetime.timedelta(days=days_until_thursday)
        return _make_result(
            date_start=thursday.strftime("%Y-%m-%d"),
            time="23:59",
            expression=expression,
        )

    # 9. Start of month
    if _START_OF_MONTH_RE.match(e_clean):
        d = reference_date.replace(day=1)
        return _make_result(date_start=d.strftime("%Y-%m-%d"), time="00:00",
                            expression=expression)

    # 10. End of month (leap-year aware)
    if _END_OF_MONTH_RE.match(e_clean):
        _, last = _get_this_month_range(reference_date)
        return _make_result(date_start=last.strftime("%Y-%m-%d"), time="23:59",
                            expression=expression)

    # 11. End of business
    if _END_OF_BUSINESS_RE.match(e_clean):
        return _make_result(date_start=reference_date.strftime("%Y-%m-%d"),
                            time="17:00", expression=expression)

    # 12. "N days/weeks before/after next [weekday]"
    pre = _convert_number_phrases(e_clean)
    m   = _REL_TO_NEXT_WEEKDAY_RE.match(pre)
    if m:
        amount, unit, direction, weekday = m.groups()
        amount = int(amount)
        if unit.startswith("week"):
            amount *= 7
        base        = get_next_weekday(weekday, reference_date, force_next_week=True)
        delta       = datetime.timedelta(days=amount)
        result_date = base + delta if direction == "after" else base - delta
        return _make_result(date_start=result_date.strftime("%Y-%m-%d"),
                            expression=expression)

    # 13. Normalize -> parsedatetime fallback
    normalized = _normalize(expression)
    dt, status = cal.parse(normalized, sourceTime=ref_dt)

    try:
        status = int(status)
    except Exception:
        return _make_result(status="failed", expression=expression)

    if status == 0:
        return _make_result(status="failed", expression=expression)

    dt            = datetime.datetime(*dt[:6])
    resolved_date = dt.strftime("%Y-%m-%d") if status in (1, 3) else None
    resolved_time = dt.strftime("%H:%M")    if status in (2, 3) else None

    # Fix A: time-only (status=2) — attach today's date when needed
    if status == 2:
        always_today = (
            e_clean in ("now", "right now", "eod", "end of day", "noon",
                        "midnight", "later today")
            or "second" in e_clean
            or e_clean == "tonight"
            or any(e_clean.startswith(f"this {t}") for t in _TODAY_TIME_OF_DAY)
            or e_clean.startswith("early ")
        )
        if always_today:
            resolved_date = reference_date.strftime("%Y-%m-%d")
        elif dt.date() != reference_date:
            resolved_date = dt.strftime("%Y-%m-%d")

    # Fix B: absolute-month year correction (don't roll into the past)
    if (resolved_date and has_absolute_month(normalized)
            and not is_past_expression(expression)
            and not _HAS_YEAR_RE.search(normalized)):
        resolved = datetime.date.fromisoformat(resolved_date)
        if resolved < reference_date:
            try:
                resolved      = resolved.replace(year=resolved.year + 1)
                resolved_date = resolved.strftime("%Y-%m-%d")
            except ValueError:
                pass
        elif resolved.year > reference_date.year:
            try:
                candidate = resolved.replace(year=reference_date.year)
                if candidate >= reference_date:
                    resolved_date = candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Fix C: "next [weekday]" — override parsedatetime's calculation
    weekday = is_next_weekday_expr(expression)
    if weekday:
        correct_date  = get_next_weekday(weekday, reference_date, force_next_week=True)
        resolved_date = correct_date.strftime("%Y-%m-%d")
        if resolved_time is None and status == 3:
            resolved_time = dt.strftime("%H:%M")

    # Fix D: eod / end of day must always carry today's date
    if e_clean in ("eod", "end of day") and resolved_date is None:
        resolved_date = reference_date.strftime("%Y-%m-%d")

    return _make_result(date_start=resolved_date, time=resolved_time,
                        expression=expression)


# ─────────────────────────────────────────────────────────────────────────────
# CLI test harness
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ref_date = datetime.date.today()
    ref_time = datetime.datetime.now().time().replace(microsecond=0)
    print(f"Reference date : {ref_date} ({ref_date.strftime('%A')})")
    print(f"Reference time : {ref_time}\n")

    tests = [
         # seconds / minutes / hours
        "in 30 seconds", "thirty seconds from now", "fifteen seconds from now",
        "in 5 minutes", "thirty minutes from now", "fifty one minutes from now",
        "one and a half hours", "two and a half hours",
        "in half an hour", "in 1 hour", "one hundred hours from now",
        "in 24 hours", "48 hours from now",
        # days / weeks
        "today", "tomorrow", "yesterday",
        "in 3 days", "thirty one days from now",
        "one hundred days from now", "one hundred twenty five days from now",
        "a couple of days",
        "next week", "last week", "in 2 weeks",
        "this week", "this month",
        "day after tomorrow", "day before yesterday", "tmw",
        # weekdays
        "next Monday", "next Friday at 3pm", "next Thursday at 14:30",
        # end-of-period
        "eod", "eom", "now", "right now",
        # specific dates
        "June 28", "December 31",
        "3 days before June 28", "one week before Christmas",
        # time-of-day
        "this morning", "this afternoon", "this evening", "tonight",
        # combined
        "tomorrow at 9am", "today at 3pm", "tomorrow morning",
        "thirty-one minutes from now",
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
    ]

    print(f"  {'Expression':<30} {'Note':<32} {'Start':<13} {'End':<13} {'Time':<7} Status")
    print("-" * 105)
    for expr, note in tests:
        r   = resolve_datetime(expr, ref_date, ref_time)
        msg = r.get("message", "")
        row = (
            f"  {expr:<30} {note:<32} "
            f"{r['date_start'] or '-':<13} "
            f"{r['date_end']   or '-':<13} "
            f"{r['time']       or '-':<7} "
            f"{r['status']}"
        )
        if msg:
            row += f"\n    --> {msg}"
        print(row)