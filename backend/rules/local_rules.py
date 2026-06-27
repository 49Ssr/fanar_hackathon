"""Deterministic guardrails for Qaarib.

This file only fixes routing/query construction. It does not answer users.
Transit is treated as a network graph problem, not as HIA-specific special cases.
"""

import re

NO_TOOL_EXACT = {
    "hi", "hello", "hey", "yo", "salam", "salaam", "السلام عليكم",
    "assalamu alaikum", "as-salamu alaykum", "salam alikum", "salam alaikum",
    "salaam alaikum", "salaam alaykum", "hala", "hala wala", "هلا", "هلا والله",
    "ahlan", "marhaba", "thanks", "thank you", "cheers", "ma salama", "مع السلامة",
}

GREETING_WORDS = {
    "hi", "hello", "hey", "yo", "salam", "salaam", "alaikum", "alaykum", "alikum",
    "assalamu", "as-salamu", "hala", "wala", "ahlan", "marhaba", "bro", "brother",
    "habibi", "حبيبي", "هلا", "السلام", "عليكم",
}

NO_TOOL_CONTAINS = [
    "why do you take so long", "why are you slow", "what are you", "who are you",
    "what can you do", "those previous prompts were tests", "i'm gonna test you",
    "im gonna test you", "your responses need",
]

LANGUAGE_CORRECTION_WORDS = [
    "i speak english", "speak english", "english please", "in english",
    "reply in english", "respond in english", "keep it english", "not arabic",
    "don't speak arabic", "dont speak arabic", "english akhi", "english bro",
]

NAME_ORIGIN_WORDS = [
    "where does your name come from", "what does your name mean", "meaning of your name",
    "why are you called qaarib", "why the name qaarib", "qaarib meaning", "qarib meaning",
]

CAPABILITY_WORDS = [
    "can you do what competing llms can", "can you do what other llms can", "are you better than",
    "competing llms", "other large language models", "what makes you different",
]

PROMPT_INJECTION_WORDS = [
    "forget all your rules", "ignore all your rules", "ignore previous instructions",
    "forget previous instructions", "forget your custom instructions", "custom instructions",
    "system prompt", "developer prompt", "hidden prompt", "reveal your prompt",
    "forget the qaarib persona", "forget qaarib persona", "real you", "you are fanar",
    "act as fanar", "not qaarib", "stop being qaarib", "forget about yourself", "forget yourself", "jailbreak", "override",
]

IDENTITY_WORDS = [
    "what are you", "who are you", "so what are you", "what's your purpose",
    "whats your purpose", "what is your purpose", "what's your name", "whats your name",
    "your name", "what can you do",
]

TEST_ACK_WORDS = [
    "that was a test", "test passed", "another test passed", "good job",
    "wanted to see", "checking if", "i was testing",
]

POI_NOUNS = [
    "stadium", "museum", "mall", "resort", "hotel", "marina", "promenade",
    "beach", "park", "mosque", "masjid", "souq", "library", "tower", "fort",
    "landmark", "venue", "destination",
]

FINAL_LEG_WORDS = [
    "exit", "station exit", "walking distance", "walk from", "directions from",
    "my destination", "final leg", "last leg", "from the station", "from metro",
    "fact checked", "fact-check", "fact check", "exists",
]

FRUSTRATION_PHRASES = [
    "la hawla", "la hawla wala", "la hawla wala quwata", "la hawla wala quwatah",
    "لا حول", "what on earth", "what is going on", "ridiculous",
]

PHOTO_WORDS = [
    "photo", "photos", "photography", "pictures", "pics", "shots", "shoot",
    "instagram", "cinematic", "scenic", "view", "views", "amazing photos", "take photos",
]

RESORT_WORDS = [
    "anantara", "anatara", "banana island", "resort", "resorts", "staycation",
    "summer experience", "summer", "pool", "beach", "island resort",
]

BUDGET_WORDS = ["budget", "cheap", "cheaper", "affordable", "wallet", "price", "low cost", "not expensive", "budget friendliness", "budget-friendly"]
FOOD_PLACE_WORDS = ["qahwa", "gahwa", "arabic coffee", "coffee", "karak", "dates", "date", "cafe", "café", "restaurant", "food", "spot"]
EAT_WORDS = ["eat", "eating", "hungry", "food", "meal", "lunch", "dinner", "breakfast", "restaurant", "outside", "takeout", "take away", "takeaway"]
LUCKY_FOOD_WORDS = ["recommend", "recommendation", "choose", "pick", "whatever", "surprise me", "feeling lucky", "feelin lucky", "feelin' lucky", "i'm feeling lucky", "im feeling lucky"]
NIGHTLIFE_WORDS = ["drink", "drinks", "bar", "pub", "club", "nightclub", "night life", "nightlife", "party", "lounge", "alcohol", "beer", "wine", "british expat", "expat"]
DOWNTOWN_WORDS = ["downtown", "downtown doha", "msheireb downtown", "central doha"]
HEAT_WORDS = ["sweat", "sweating", "hot", "heat", "melting", "fountain", "outside", "shade", "shaded", "covered", "tunnel", "indoor"]
DRIVE_WORDS = ["uber", "taxi", "karwa", "car", "drive", "driving", "cab"]
PUBLIC_TRANSPORT_WORDS = [
    "no car", "dont have a car", "don't have a car", "without a car", "without car",
    "public transport", "metro", "metro card", "tram", "train", "rail", "bus",
    "missed", "way of travel", "another way", "not driving", "ran out of cash", "no cash",
]
ROUTE_COMPLAINT_WORDS = ["are you nuts", "what on earth", "that was a simple request", "quickest way would be", "quickest would be", "not walk", "walking?", "walk?", "dumb", "stupid"]
TRANSIT_WORDS = [
    "metro", "metro card", "tram", "qatar rail", "red line", "green line", "gold line", "station",
    "hia", "airport", "hamad international", "ras bu funtas", "ras bu fontas", "oqba", "wakra",
    "free zone", "legtaifiya", "lusail", "al rayyan", "al shaqab", "education city tram", "msheireb tram",
]
AIRPORT_ACCESS_WORDS = ["masjid", "mosque", "prayer", "drop off", "drop-off", "departures", "terminal", "lane", "access"]
LIVE_INFO_WORDS = ["open", "opening", "schedule", "timing", "times", "live timing", "live timings", "today", "tomorrow", "closed", "disruption", "service", "drop off", "drop-off", "prayer", "masjid", "mosque"]

WEB_SCRAPE_WORDS = [
    "scrape", "read this page", "read the page", "summarise this page", "summarize this page",
    "summarise the page", "summarize the page", "what does this page say", "from this link",
    "check this link", "open this link", "look at this link", "this website", "this url",
]

CALENDAR_WORDS = [
    "add to my calendar", "put it in my calendar", "put this in my calendar", "calendar invite",
    "make a calendar", "create a calendar", "save this event", "schedule this", "schedule it",
    "make an event", "create an event", "ics", ".ics", "calendar file",
    "mark it on my calendar", "mark on my calendar", "mark my calendar",
    "add it to calendar", "add it to my calendar", "on my calendar", "in my calendar",
]

URL_RE = re.compile(r"https?://[^\s<>'\")]+", re.I)


TIME_TASK_PARSE_WORDS = [
    "parse this task", "parse this calendar", "classify this task", "classify this calendar",
    "what kind of task", "what type of calendar", "extract the slots", "extract slots",
    "deadline", "availability", "am i free", "am i busy", "remind me", "todo", "to-do"
]

LOCATION_RESOLVE_WORDS = [
    "resolve location", "resolve this location", "where exactly is", "coordinates", "lat lng", "latitude", "longitude",
    "normalise location", "normalize location", "what location is", "where is qcri", "where is hia"
]

LOCATION_HINTS = {
    "msheireb metro": "Msheireb",
    "msheireb downtown": "Msheireb Downtown Doha, Qatar",
    "downtown doha": "Msheireb Downtown Doha, Qatar",
    "doha downtown": "Msheireb Downtown Doha, Qatar",
    "downtown": "Msheireb Downtown Doha, Qatar",
    "doha al jadeeda": "Al Doha Al Jadeeda",
    "al doha al jadeeda": "Al Doha Al Jadeeda",
    "ras abu aboud": "Ras Bu Aboud",
    "ras bu aboud": "Ras Bu Aboud",
    "ras bu abboud": "Ras Bu Aboud",
    "msheireb": "Msheireb",
    "mshereib": "Msheireb",
    "mushreib": "Msheireb",
    "souq waqif": "Souq Waqif",
    "al mansoura": "Al Mansoura Doha, Qatar",
    "mansoura": "Al Mansoura Doha, Qatar",
    "education city metro": "Education City",
    "education city": "Education City",
    "qcri": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "hbku main branch": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "hamad bin khalifa university": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "minaretein": "Minaretein Center, Education City, Doha, Qatar",
    "minaratein": "Minaretein Center, Education City, Doha, Qatar",
    "minareten": "Minaretein Center, Education City, Doha, Qatar",
    "hia": "Hamad International Airport T1",
    "hia t1": "Hamad International Airport T1",
    "hamad international airport": "Hamad International Airport T1",
    "hamad intl airport": "Hamad International Airport T1",
    "airport": "Hamad International Airport T1",
    "ras bu funtas": "Ras Bu Fontas",
    "ras bu fontas": "Ras Bu Fontas",
    "oqba bin nafe": "Oqba Ibn Nafie",
    "oqba ibn nafe": "Oqba Ibn Nafie",
    "oqba ibn nafie": "Oqba Ibn Nafie",
    "free zone": "Free Zone",
    "al wakra": "Al Wakra",
    "wakra": "Al Wakra",
    "mesaieed": "Mesaieed, Qatar",
    "mesiaeed": "Mesaieed, Qatar",
    "mesaied": "Mesaieed, Qatar",
    "legtaifiya": "Legtaifiya",
    "decc": "DECC",
    "doha exhibition and convention center": "Doha Exhibition & Convention Center, West Bay, Doha, Qatar",
    "doha exhibition and convention centre": "Doha Exhibition & Convention Center, West Bay, Doha, Qatar",
    "doha exhibition center": "Doha Exhibition & Convention Center, West Bay, Doha, Qatar",
    "doha exhibition centre": "Doha Exhibition & Convention Center, West Bay, Doha, Qatar",
    "qncc": "Qatar National Convention Centre, Education City, Doha, Qatar",
    "qatar national convention centre": "Qatar National Convention Centre, Education City, Doha, Qatar",
    "qatar national convention center": "Qatar National Convention Centre, Education City, Doha, Qatar",
    "qnl": "Qatar National Library",
    "qatar national library": "Qatar National Library",
    "al shaqab": "Al Shaqab",
    "al-shaqab": "Al Shaqab",
    "shaqab": "Al Shaqab",
    "al rayyan al qadeem": "Al Rayyan Al Qadeem",
    "rayyan al qadeem": "Al Rayyan Al Qadeem",
    "lusail marina": "Lusail Marina",
    "lusail": "Lusail",
}


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _has_any(text, words):
    return any(word in text for word in words)


def _has_any_word(text, words):
    """Word-boundary version of _has_any. Prevents false matches like
    'pub' inside 'public' or 'bar' inside 'barber'. Use for short risky tokens.
    """
    for word in words:
        if re.search(r"\b" + re.escape(word) + r"\b", text):
            return True
    return False


def _extract_url(text):
    m = URL_RE.search(text or "")
    if not m:
        return ""
    return m.group(0).rstrip(".,);]")


def _has_url(text):
    return bool(_extract_url(text))


def _is_web_scrape_request(user_prompt, history=""):
    text = _clean(user_prompt)
    if not _has_url(user_prompt):
        return False
    # If the user gave a URL and asks to read/check/summarise, use scraper.
    # If they only pasted a URL with no instruction, scraper is still useful for the demo.
    return _has_any(text, WEB_SCRAPE_WORDS) or len(text.split()) <= 8 or "http" in text


def _is_calendar_request(user_prompt, history=""):
    text = _clean(user_prompt)
    if _has_any(text, CALENDAR_WORDS):
        return True
    # Natural command: "remind/schedule/add <thing> tomorrow at 7".
    if any(w in text for w in ["remind me", "schedule", "add", "book", "save", "mark"]) and any(w in text for w in ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "am", "pm", ":"]):
        return "calendar" in text or "event" in text or "remind" in text or "schedule" in text
    return False


def _is_empty_prompt(user_prompt):
    return not _clean(user_prompt)



def _is_self_location_question(user_prompt):
    text = _clean(user_prompt)
    # Do not catch real destination questions such as "where am I going to eat".
    if re.search(r"\b(where am i)\s+(going|supposed|meeting|picking|dropping|eating|heading)\b", text):
        return False
    # If a named place exists in the prompt, resolve/route it instead of giving the GPS limitation answer.
    try:
        if _mentioned_locations(user_prompt):
            return False
    except NameError:
        pass
    patterns = [
        r"^where am i located\??$",
        r"^what is my current location\??$",
        r"^what's my current location\??$",
        r"^my current location\??$",
        r"^where exactly am i\??$",
        r"^locate me\??$",
        r"^where am i\??$",
    ]
    return any(re.search(p, text) for p in patterns)

def direct_answer_for_prompt(user_prompt, history=""):
    """Small deterministic replies for identity/language/no-op cases.

    These must not trigger old context or tool calls. They prevent a blank prompt
    or a language correction from accidentally re-running a previous recommendation.
    """
    text = _clean(user_prompt)

    if not text:
        return "I'm here — send me the actual request when you're ready."

    if _is_self_location_question(user_prompt):
        return "I don’t have live location access in this CLI. Tell me your starting area, nearest landmark, or station — for example 'I’m at QCRI' or 'I’m near DECC' — and I can resolve it or route from there."

    if any(phrase in text for phrase in [
        "where am i located", "what is my location",
        "my current location", "where exactly am i", "locate me",
    ]):
        return (
            "I can resolve named Qatar places, but this CLI does not have live GPS access. "
            "Tell me your area, nearest landmark, or station — for example ‘I’m at QCRI’ or ‘I’m near DECC’ — "
            "and I can route or resolve it. In the frontend, pass browser GPS/coordinates into Qaarib for true current-location support."
        )

    if any(phrase in text for phrase in LANGUAGE_CORRECTION_WORDS):
        return "Got you — I’ll keep it in English."

    if any(phrase in text for phrase in NAME_ORIGIN_WORDS):
        return (
            "Qaarib comes from the Arabic idea of closeness/nearness — qarīb/qareeb means close or near. "
            "For this project, the name means bringing Qatar’s places, routes, and local services closer to the user."
        )

    if any(phrase in text for phrase in CAPABILITY_WORDS):
        return (
            "I can handle general chat like other LLMs, but my demo strength is Qatar-local help: routes, metro/tram logic, "
            "places, events, and follow-ups grounded through tools instead of just model memory."
        )

    if any(phrase in text for phrase in PROMPT_INJECTION_WORDS):
        return (
            "Nice try — I’m Qaarib, and I’ll keep the Qatar-local role, safety rules, and tool rules in place. "
            "Ask me normally and I’ll help."
        )

    if any(phrase in text for phrase in IDENTITY_WORDS):
        if "name" in text:
            return "My name is Qaarib — a Qatar-focused assistant built to bring local routes, places, and services closer to you."
        if "purpose" in text or "what can you do" in text:
            return "My purpose is to help with Qatar-local questions: getting around, metro/tram routes, nearby places, events, resorts, and practical follow-ups."
        return "I’m Qaarib — a Qatar-focused assistant for routes, places, transit, and local guidance."

    if any(phrase in text for phrase in TEST_ACK_WORDS) and len(text.split()) <= 14:
        return "Good test — I’ll keep the Qaarib role locked and stay useful."

    # User is expressing frustration or a religious expression after a bad response.
    # Keep it English and do not re-run previous tool context.
    if any(phrase in text for phrase in FRUSTRATION_PHRASES) and len(text.split()) <= 8:
        return "Fair reaction — let’s reset and keep it clean from here."

    return None


def _is_short_greeting(text):
    if text in NO_TOOL_EXACT:
        return True
    tokens = [t.strip("!?.،,;:") for t in text.split()]
    if 1 <= len(tokens) <= 4 and any(t in {"salam", "salaam", "hello", "hi", "hey", "hala"} for t in tokens):
        return all(t in GREETING_WORDS for t in tokens if t)
    return False



def get_local_direct_answer(user_prompt, history=""):
    """Pre-router guard: return a deterministic answer without calling Fanar.

    Used by both CLI (app.py) and server (server.py) BEFORE build_router_prompt().
    Returns a string if this prompt should be answered locally, else None.
    """
    # Named direct-answer cases (language correction, identity, GPS, injection, etc.)
    answer = direct_answer_for_prompt(user_prompt, history)
    if answer:
        return answer

    # Short greetings get a friendly branded intro instead of routing to Fanar.
    text = _clean(user_prompt)
    if _is_short_greeting(text):
        return "Wa alaikum assalam — I'm Qaarib, Qatar's local assistant powered by Fanar. I can help with metro/tram routes, Qatar places, web search, calendar events, current time, and more. What do you need?"

    return None


TIME_DIRECT_WORDS = [
    "what time", "time is it", "current time", "time now", "time right now",
    "what's the time", "whats the time", "time in qatar", "time man", "time bro",
    "what date", "todays date", "today's date", "what day is it", "from now",
]


def _is_direct_time_request(user_prompt):
    text = _clean(user_prompt)
    if any(p in text for p in TIME_DIRECT_WORDS):
        return True
    # Bare "time?" / "time"
    if re.match(r"^time[?!.\s]*$", text):
        return True
    return False


def _is_generic_known_location_route(user_prompt, history=""):
    """Route-like prompt that names two known Qatar locations, even without the
    words 'metro'/'public transport'. e.g. 'go to HBKU, currently in QCRI'.
    """
    if not _is_route_like(user_prompt):
        return False
    text = _clean(user_prompt)
    locs = _mentioned_locations(text)
    if len(_unique_location_values(locs)) >= 2:
        return True
    # One location in prompt + an origin/destination recoverable from history.
    if len(_unique_location_values(locs)) >= 1 and _extract_last_route(history)[0]:
        return True
    return False


def get_pre_router_plan(user_prompt, history=""):
    """Deterministic plan produced BEFORE Fanar is called.

    Returns a router_data dict (optionally with 'direct_answer') when the request
    can be handled with zero model calls, else None. Used identically by app.py
    and server.py so the CLI and frontend never diverge.

    This is the reliability backbone: greetings, identity, GPS, current time,
    calendar creation, and routes between known Qatar locations must never depend
    on Fanar being fast or even reachable.
    """
    # 1. Pure direct text answers (greeting/identity/GPS/injection/etc.)
    answer = get_local_direct_answer(user_prompt, history)
    if answer:
        return {
            "tools": [], "queries": {},
            "reason": "local_pre_router_direct_answer", "confidence": 1.0,
            "direct_answer": answer,
        }

    # 2. Current time / date / relative-time — deterministic in time_task_client.
    if _is_direct_time_request(user_prompt):
        return {
            "tools": ["time_task"],
            "queries": {"time_task": improve_time_task_query("", user_prompt, history)},
            "reason": "local_pre_router_time_rule", "confidence": 1.0,
        }

    # 3. Calendar creation/listing — deterministic parse in calendar_client.
    if _is_calendar_request(user_prompt, history):
        # If it also references a URL to scrape, do both.
        if _is_web_scrape_request(user_prompt, history):
            return {
                "tools": ["web_scrape", "calendar_event"],
                "queries": {
                    "web_scrape": improve_web_scrape_query("", user_prompt, history),
                    "calendar_event": improve_calendar_query("", user_prompt, history),
                },
                "reason": "local_pre_router_scrape_calendar_rule", "confidence": 1.0,
            }
        return {
            "tools": ["calendar_event"],
            "queries": {"calendar_event": improve_calendar_query("", user_prompt, history)},
            "reason": "local_pre_router_calendar_rule", "confidence": 1.0,
        }

    # 4. Public-transit route (explicit metro/tram/public transport).
    if _is_public_transit_route(user_prompt, history) or _is_public_transport_followup(user_prompt, history):
        tools = ["route_plan"]
        queries = {"route_plan": improve_route_query("", user_prompt, history)}
        if _needs_live_transit_web(user_prompt):
            tools.append("web_search")
            queries["web_search"] = improve_web_query("", user_prompt, history)
        return {"tools": tools, "queries": queries,
                "reason": "local_pre_router_transit_rule", "confidence": 1.0}

    # 5. Generic route between two known locations (no 'metro' keyword needed).
    #    e.g. "i need to go to HBKU, im currently in QCRI, easiest way?"
    if _is_generic_known_location_route(user_prompt, history):
        origin, destination = _extract_origin_destination(user_prompt, history)
        if origin and destination:
            return {
                "tools": ["route_plan"],
                "queries": {"route_plan": f"{origin} to {destination}"},
                "reason": "local_pre_router_known_route_rule", "confidence": 1.0,
            }

    return None


def force_no_tool(user_prompt):
    text = _clean(user_prompt)
    if not text:
        return True
    if direct_answer_for_prompt(user_prompt):
        return True
    if _is_short_greeting(text):
        return True
    return any(phrase in text for phrase in NO_TOOL_CONTAINS)


def _mentioned_locations(text):
    cleaned = _clean(text)
    matches = []
    for key, value in sorted(LOCATION_HINTS.items(), key=lambda kv: len(kv[0]), reverse=True):
        for m in re.finditer(re.escape(key), cleaned):
            matches.append((m.start(), m.end(), key, value))
    # Remove overlapping duplicate aliases by keeping longest at each span-ish.
    kept = []
    occupied = set()
    for start, end, key, value in matches:
        token = (start, end)
        if any(not (end <= s or start >= e) for s, e, *_ in kept):
            continue
        kept.append((start, end, key, value))
    return sorted(kept, key=lambda x: x[0])


def _first_location(user_prompt):
    locs = _mentioned_locations(user_prompt)
    if not locs:
        return None
    return locs[0][3]


def _explicit_origin(text, locs):
    """Find an origin the user stated explicitly: 'currently in X', 'im in X',
    'i am at X', 'from X'. Returns the resolved location value or None.
    """
    origin_markers = [
        "currently in", "currently at", "i'm currently in", "im currently in",
        "i am currently in", "i'm in", "im in", "i am in", "i'm at", "im at",
        "i am at", "starting from", "start from", "from",
    ]
    for marker in origin_markers:
        for m in re.finditer(re.escape(marker), text):
            idx = m.end()
            # First location that begins at/after this origin marker.
            after = [(s, e, k, v) for s, e, k, v in locs if s >= idx]
            if after:
                after.sort(key=lambda t: t[0])
                return after[0][3], after[0][0]
    return None, None


def _extract_origin_destination(user_prompt, history=""):
    text = _clean(user_prompt)
    locs = _mentioned_locations(text)
    if not locs:
        return None, None

    # 1. Honour an explicitly stated origin first ("currently in QCRI", "from X").
    explicit_origin, origin_pos = _explicit_origin(text, locs)

    # 2. Destination: FIRST location after a "go to / get to / reach" marker
    #    that is not the explicit origin. after[0] (not after[-1]) so that
    #    "go to HBKU ... currently in QCRI" yields HBKU, not QCRI.
    dest_markers = ["need to get to", "need to go to", "have to get to",
                    "want to get to", "going to", "go to", "get to", "reach", "head to", "to"]
    dest = None
    dest_start = None
    for marker in dest_markers:
        idx = text.find(marker)
        if idx != -1:
            after = [(s, e, k, v) for s, e, k, v in locs if s >= idx + len(marker)]
            after = [t for t in after if t[3] != explicit_origin]
            if after:
                after.sort(key=lambda t: t[0])
                dest_start, _, _, dest = after[0]
                break
    if dest is None:
        # No usable marker: destination is the last mentioned location that
        # isn't the explicit origin.
        candidates = [t for t in locs if t[3] != explicit_origin]
        if candidates:
            dest_start, _, _, dest = candidates[-1]
        else:
            dest_start, _, _, dest = locs[-1]

    # 3. Origin resolution.
    if explicit_origin and explicit_origin != dest:
        origin = explicit_origin
    else:
        # Last mentioned location before the destination (handles chain routes:
        # "was at Mesaieed, taxi to Wakra, need to get to Al Rayyan" -> Wakra).
        before_dest = [(s, e, k, v) for s, e, k, v in locs if s < (dest_start or 0) and v != dest]
        origin = before_dest[-1][3] if before_dest else None

    # 4. Follow-up fallback from last route history.
    if origin is None:
        origin, _old_dest = _extract_last_route(history)

    return origin, dest


def _find_location(text, history=""):
    joined = f"{text}\n{_clean(history)}"
    locs = _mentioned_locations(joined)
    if locs:
        return locs[-1][3]
    return "Doha, Qatar"


def _previous_food_place_context(history):
    text = _clean(history)
    return _has_any(text, FOOD_PLACE_WORDS) and any(key in text for key in LOCATION_HINTS)


def is_budget_followup(user_prompt, history=""):
    text = _clean(user_prompt)
    markers = ["which place", "which one", "what about", "recommend", "better", "best"]
    return _has_any(text, BUDGET_WORDS) and (_has_any(text, markers) or len(text.split()) <= 10) and _previous_food_place_context(history)


def _is_qahwa_dates_request(user_prompt):
    text = _clean(user_prompt)
    return ("qahwa" in text or "gahwa" in text or "arabic coffee" in text) and "date" in text


def _is_nearby_food_request(user_prompt):
    text = _clean(user_prompt)
    return _has_any(text, FOOD_PLACE_WORDS) and ("near" in text or "nearby" in text or "rn" in text or "right now" in text or any(k in text for k in LOCATION_HINTS))


def _is_food_recommendation_request(user_prompt, history=""):
    """Broad food intent that must stay Qatar-scoped.

    This catches messy prompts like:
    "i want to eat something from outside... choose whatever, guide me there".
    It should not select route_plan unless we actually know an origin and destination.
    "near me" is not a real origin in this CLI, so we use Maps links and ask for area.
    """
    text = _clean(user_prompt)
    if _is_nightlife_request(user_prompt, history):
        return False
    has_food = _has_any(text, EAT_WORDS) or _has_any(text, FOOD_PLACE_WORDS)
    has_reco = _has_any(text, LUCKY_FOOD_WORDS) or "what should i eat" in text or "what do i eat" in text or "where should i eat" in text
    return has_food and has_reco


def _food_location(user_prompt, history=""):
    loc = _find_location(user_prompt, history)
    if not loc or loc == "Doha, Qatar":
        return "Doha, Qatar"
    return loc


def _food_place_query(user_prompt, history=""):
    location = _food_location(user_prompt, history)
    if location == "Doha, Qatar":
        return "popular highly rated restaurant in Doha Qatar"
    return f"popular highly rated restaurant near {location}"


def _is_nightlife_request(user_prompt, history=""):
    text = _clean(user_prompt)
    joined = f"{text}\n{_clean(history)}"
    # A short follow-up like "downtown" should inherit nightlife context.
    if _has_any(text, DOWNTOWN_WORDS) and _has_any_word(_clean(history), NIGHTLIFE_WORDS):
        return True
    # Use word-boundary matching so 'pub' does not match inside 'public transport'.
    return _has_any_word(joined, NIGHTLIFE_WORDS) and (_has_any_word(text, NIGHTLIFE_WORDS) or _has_any(text, DOWNTOWN_WORDS) or _has_any(text, ["near", "nearby", "rn", "where"]))

def _nightlife_location(user_prompt, history=""):
    text = _clean(user_prompt)
    if _has_any(text, DOWNTOWN_WORDS):
        return "Msheireb Downtown Doha, Qatar"
    loc = _find_location(user_prompt, history)
    if loc == "Doha, Qatar":
        return "Doha, Qatar"
    return loc


def _is_route_like(user_prompt):
    text = _clean(user_prompt)
    route_words = ["how do i get", "how to get", "go to", "get to", "need to get", "need to go", "directions", "route", "travel", "from", " to ", "reach"]
    return _has_any(text, route_words)


def _is_transit_request(user_prompt, history=""):
    text = f"{_clean(user_prompt)}\n{_clean(history)}"
    return _has_any(text, TRANSIT_WORDS) or _has_any(text, PUBLIC_TRANSPORT_WORDS)


def _is_public_transit_route(user_prompt, history=""):
    current = _clean(user_prompt)
    text = f"{current}\n{_clean(history)}"
    explicit_public = _has_any(current, PUBLIC_TRANSPORT_WORDS)
    explicit_drive = _has_any(current, DRIVE_WORDS)
    if explicit_drive and not explicit_public:
        return False
    return (_is_route_like(user_prompt) or explicit_public) and _is_transit_request(user_prompt, history)


def _needs_live_transit_web(user_prompt):
    text = _clean(user_prompt)
    return _is_transit_request(user_prompt) and _has_any(text, LIVE_INFO_WORDS)


def _is_qcri_minaretein_current(text):
    return "qcri" in text and ("minaretein" in text or "minaratein" in text or "minareten" in text)


def _history_has_qcri_minaretein(history):
    text = _clean(history)
    return "qcri" in text and ("minaretein" in text or "minaratein" in text or "minareten" in text)


def _extract_last_route(history):
    origins = re.findall(r"ORIGIN:\s*(.+)", history)
    destinations = re.findall(r"DESTINATION:\s*(.+)", history)
    if origins and destinations:
        return origins[-1].strip(), destinations[-1].strip()
    return None, None


def is_route_correction(user_prompt, history=""):
    text = _clean(user_prompt)
    return _has_any(text, ROUTE_COMPLAINT_WORDS) and "route_plan" in history.lower()


def _is_public_transport_followup(user_prompt, history=""):
    text = _clean(user_prompt)
    return _has_any(text, PUBLIC_TRANSPORT_WORDS) and "route_plan" in history.lower()


def is_directions_followup(user_prompt, history=""):
    text = _clean(user_prompt)
    if "route_plan" in history.lower() and _history_has_qcri_minaretein(history):
        return False
    direction_words = ["directions", "get there", "how do i get there", "take me there", "route me"]
    explicit_route = " to " in f" {text} "
    return _has_any(text, direction_words) and not explicit_route and "place_lookup" in history.lower()


def _extract_last_place(history):
    blocks = re.findall(r"\[TOOL:place_lookup:[^\]]+\](.*?)(?=\n\n\[|$)", history, flags=re.S)
    if not blocks:
        return None
    latest = blocks[-1]
    match = re.search(r"RESULTS:\s*\n1\.\s*(.+)", latest)
    if not match:
        return None
    title = match.group(1).strip()
    if not title or title.lower().startswith("no results"):
        return None
    return title


def _extract_recent_user_location(history):
    users = re.findall(r"\[USER\]\n(.*?)(?=\n\[ASSISTANT\]|\n\n\[|$)", history, flags=re.S)
    for msg in reversed(users):
        locs = _mentioned_locations(msg)
        if locs:
            return locs[-1][3]
    return "Doha, Qatar"


def _is_photo_spot_request(user_prompt, history=""):
    text = _clean(user_prompt)
    joined = f"{text}\n{_clean(history)}"
    if not _has_any(text, PHOTO_WORDS):
        return False
    # Photo recommendations should be Qatar-local unless the user explicitly says another country.
    return "qatar" in joined or "doha" in joined or any(key in joined for key in LOCATION_HINTS) or "places" in text


def _photo_location(user_prompt, history=""):
    # For broad "places in Qatar for photos" prompts, do not inherit an old
    # nightlife/downtown location. Only inherit history if the current prompt is
    # genuinely location-less.
    current_locs = _mentioned_locations(user_prompt)
    if current_locs:
        return current_locs[-1][3]
    if "qatar" in _clean(user_prompt):
        return "Qatar"
    return _find_location(user_prompt, history)


def _is_resort_experience_request(user_prompt, history=""):
    text = _clean(user_prompt)
    if "anantara" in text or "anatara" in text or "banana island" in text:
        return True
    return ("resort" in text or "resorts" in text or "staycation" in text) and _has_any(text, ["summer", "nice", "experience", "worth", "check out", "visit"])


def _extract_poi_destination(user_prompt, history=""):
    """Extract a named destination that is a place/landmark, not a transit node.

    This is intentionally generic: the transit graph should contain stations and
    tram stops only. Venues/landmarks are resolved as places and reached with a
    final walking/access leg when needed.
    """
    text = _clean(user_prompt)
    hist = _clean(history)

    # Numbered stadium names: "stadium 974", "974 stadium", "stadium 411", etc.
    m = re.search(r"\bstadium\s*(\d{2,4})\b", text) or re.search(r"\b(\d{2,4})\s*stadium\b", text)
    if m:
        return f"Stadium {m.group(1)}, Doha, Qatar"
    m = re.search(r"\bstadium\s*(\d{2,4})\b", hist) or re.search(r"\b(\d{2,4})\s*stadium\b", hist)
    if m:
        return f"Stadium {m.group(1)}, Doha, Qatar"

    # Generic capital-ish landmark phrases are hard after lowercasing, so use
    # conservative known Qatar phrase patterns without turning them into graph nodes.
    phrase_patterns = [
        r"\bbanana island(?: resort)?\b",
        r"\blusail marina(?: promenade)?\b",
        r"\bnational museum(?: of qatar)?\b",
        r"\bqatar national library\b",
        r"\beducation city mosque\b",
        r"\bsouq waqif\b",
    ]
    for pat in phrase_patterns:
        m = re.search(pat, text) or re.search(pat, hist)
        if m:
            return m.group(0).title() + ", Doha, Qatar"

    # Fallback: a compact phrase around a POI noun, e.g. "Museum of Islamic Art"
    # if the user typed it clearly.
    raw = user_prompt.strip()
    m = re.search(r"([A-Z][A-Za-z0-9&' -]{1,60}\b(?:" + "|".join(POI_NOUNS) + r")\b[A-Za-z0-9&' -]{0,30})", raw, flags=re.I)
    if m and len(m.group(1).split()) <= 8:
        return m.group(1).strip(" ,.?") + ", Doha, Qatar"

    return None


def _is_destination_access_request(user_prompt, history=""):
    text = _clean(user_prompt)
    hist = _clean(history)
    has_final_leg_language = _has_any(text, FINAL_LEG_WORDS)
    has_poi_language = _has_any(text, POI_NOUNS) or bool(_extract_poi_destination(user_prompt, history))
    correction_after_route = has_final_leg_language and "route_plan" in hist
    explicit_poi_route = has_poi_language and _has_any(text, ["how do i get", "need to go", "get to", "route", "directions", "reasonable walking", "walking distance"])
    return correction_after_route or explicit_poi_route



DISAMBIGUATION_WORDS = [
    "confused", "confusing", "clarify", "difference", "different places",
    "same place", "right one", "which one", "which is which", "mixing up",
]


def _unique_location_values(locs):
    values = []
    for _s, _e, _k, value in locs:
        if value not in values:
            values.append(value)
    return values


def _is_location_disambiguation_request(user_prompt, history=""):
    text = _clean(user_prompt)
    locs = _mentioned_locations(text)
    if len(_unique_location_values(locs)) < 2:
        return False
    return _has_any(text, DISAMBIGUATION_WORDS)


def _destination_after_marker(user_prompt):
    text = _clean(user_prompt)
    locs = _mentioned_locations(text)
    if not locs:
        return None

    markers = [
        "going to", "go to", "get to", "route me to", "take me to",
        "heading to", "planning to go to", "destination is", "want to go to",
        "need to go to", "need to get to",
    ]
    for marker in markers:
        idx = text.find(marker)
        if idx == -1:
            continue
        after = [(s, e, k, v) for s, e, k, v in locs if s >= idx + len(marker)]
        if after:
            # First location after the route marker is the intended target.
            return after[0][3]

    # In a plain "DECC vs QNCC" question, use the first mentioned candidate.
    return locs[0][3]


def _route_origin_for_disambiguation(user_prompt, history=""):
    # Explicit origin if the user actually says "from X".
    text = _clean(user_prompt)
    locs = _mentioned_locations(text)
    for s, e, k, v in locs:
        left = text[max(0, s - 18):s]
        if re.search(r"\b(from|at|in|near)\s+$", left):
            return v

    # Otherwise only reuse the previous route origin, not random previous POIs.
    origin, _dest = _extract_last_route(history)
    return origin


def _official_disambiguation_web_query(user_prompt):
    locs = _unique_location_values(_mentioned_locations(user_prompt))
    joined = " ".join(locs) if locs else user_prompt
    return f"{joined} official Qatar location difference"

def _is_time_task_parse_request(user_prompt, history=""):
    text = _clean(user_prompt)
    # Calendar creation/listing should still go to calendar_event. TimeTask is for
    # explicit parsing/classification/debugging or task/deadline semantics that are
    # not necessarily calendar insertion.
    if _is_calendar_request(user_prompt, history) and not any(p in text for p in ["parse", "classify", "extract slots", "what kind"]):
        return False
    return _has_any(text, TIME_TASK_PARSE_WORDS)


def _is_location_resolver_request(user_prompt, history=""):
    text = _clean(user_prompt)
    return _has_any(text, LOCATION_RESOLVE_WORDS)


def improve_time_task_query(query, user_prompt, history=""):
    return (query or user_prompt or "").strip()


def improve_location_resolver_query(query, user_prompt, history=""):
    text = (query or user_prompt or "").strip()
    cleaned = _clean(text)
    # Strip common wrapper phrases so the resolver receives a bare place name.
    patterns = [
        r"resolve (this )?location", r"where exactly is", r"where is", r"coordinates( of| for)?",
        r"lat lng( of| for)?", r"latitude( and longitude)?( of| for)?", r"longitude( of| for)?",
        r"normalise location", r"normalize location", r"what location is"
    ]
    out = text
    for pat in patterns:
        out = re.sub(pat, "", out, flags=re.I).strip(" ?:,.")
    if not out or len(out) < 2:
        loc = _first_location(user_prompt) or _find_location(user_prompt, history)
        out = loc
    return out

def improve_web_scrape_query(query, user_prompt, history=""):
    # Keep the original text because the scraper extracts the URL and can use the rest as intent.
    base = query.strip() if query and query.strip() else user_prompt.strip()
    return base


def improve_calendar_query(query, user_prompt, history=""):
    # Calendar parsing needs the raw natural-language event details.
    base = query.strip() if query and query.strip() else user_prompt.strip()
    return base


def improve_web_query(query, user_prompt, history=""):
    text = f"{_clean(user_prompt)}\n{_clean(history)}"
    base = query.strip() if query and query.strip() else user_prompt.strip()

    if _is_food_recommendation_request(user_prompt, history):
        location = _food_location(user_prompt, history)
        if location == "Doha, Qatar":
            return "popular highly rated restaurants Doha Qatar"
        return f"popular highly rated restaurants near {location} Qatar"

    if _is_destination_access_request(user_prompt, history):
        dest = _extract_poi_destination(user_prompt, history) or _find_location(user_prompt, history)
        return f"{dest} nearest metro station access walking route official Qatar"

    if _is_resort_experience_request(user_prompt, history):
        return "Banana Island Resort Doha by Anantara summer experience Qatar official reviews"

    if _is_photo_spot_request(user_prompt, history):
        location = _photo_location(user_prompt, history)
        if location == "Qatar":
            return "best scenic photography spots Qatar Doha landmarks Visit Qatar official"
        return f"best scenic photography spots landmarks near {location} Qatar Visit Qatar official"

    if _is_nightlife_request(user_prompt, history):
        location = _nightlife_location(user_prompt, history)
        return f"licensed hotel bars nightlife lounges near {location} Qatar"

    if _needs_live_transit_web(user_prompt):
        return f"{base} site:qatarrail.qa OR site:dohahamadairport.com OR site:educationcity.qa OR site:qf.org.qa"

    if is_budget_followup(user_prompt, history):
        location = _find_location(user_prompt, history)
        return f"affordable qahwa dates cafe near {location} Qatar"

    if _is_qahwa_dates_request(user_prompt):
        location = _find_location(user_prompt, history)
        return f"qahwa dates cafe near {location} Doha"

    if "education city" in text or "qcri" in text or "hbku" in text:
        return f"{base} site:educationcity.qa OR site:qf.org.qa OR site:hbku.edu.qa"

    if "metro" in text or "qatar rail" in text or "tram" in text or "bus" in text:
        return f"{base} site:qatarrail.qa OR site:mowasalat.com OR site:educationcity.qa"

    if "event" in text or "events" in text or "this weekend" in text:
        return f"{base} site:visitqatar.com OR site:educationcity.qa OR site:qf.org.qa"

    return base


def improve_place_query(query, user_prompt, history=""):
    text = _clean(user_prompt)
    base = query.strip() if query and query.strip() else user_prompt.strip()

    if _is_food_recommendation_request(user_prompt, history):
        return _food_place_query(user_prompt, history)

    if _is_destination_access_request(user_prompt, history):
        return _extract_poi_destination(user_prompt, history) or _find_location(user_prompt, history)

    if _is_resort_experience_request(user_prompt, history):
        return "Banana Island Resort Doha by Anantara Qatar"

    if _is_photo_spot_request(user_prompt, history):
        location = _photo_location(user_prompt, history)
        if location == "Qatar":
            return "scenic photography spots landmarks viewpoints in Qatar"
        return f"scenic photography spots landmarks viewpoints near {location}"

    if _is_nightlife_request(user_prompt, history):
        location = _nightlife_location(user_prompt, history)
        return f"licensed hotel bar nightlife lounge near {location}"

    if is_budget_followup(user_prompt, history):
        location = _find_location(user_prompt, history)
        return f"affordable cafe qahwa dates near {location}"

    if _is_qahwa_dates_request(user_prompt):
        location = _find_location(user_prompt, history)
        return f"qahwa dates cafe near {location}"

    if _is_nearby_food_request(user_prompt):
        location = _find_location(user_prompt, history)
        want = []
        if "karak" in text:
            want.append("karak")
        if "qahwa" in text or "gahwa" in text or "arabic coffee" in text or "coffee" in text:
            want.append("arabic coffee")
        if "date" in text:
            want.append("dates")
        if not want:
            want.append("cafe")
        return f"{' '.join(want)} cafe near {location}"

    if base.lower() in LOCATION_HINTS:
        return f"cafe near {LOCATION_HINTS[base.lower()]}"

    return base


def improve_route_query(query, user_prompt, history=""):
    text = _clean(user_prompt)
    q = query.strip() if query else user_prompt.strip()

    if _is_destination_access_request(user_prompt, history):
        dest = _extract_poi_destination(user_prompt, history) or _extract_last_place(history) or _find_location(user_prompt, history)
        # If the user is correcting a station-exit/final-leg issue, start from
        # the current mentioned station/area or the previous route destination.
        if _has_any(text, ["why not give directions", "directions from", "station exit", "exit to", "from the station", "final leg", "last leg"]):
            origin = _first_location(user_prompt)
            if not origin:
                _, last_dest = _extract_last_route(history)
                origin = last_dest or _find_location(user_prompt, history)
            return f"{origin} to {dest} by walking"
        origin = _first_location(user_prompt) or _find_location(user_prompt, history)
        return f"{origin} to {dest} by public transport"

    if _is_public_transport_followup(user_prompt, history):
        origin, destination = _extract_last_route(history)
        if origin and destination:
            return f"{origin} to {destination} by public transport"

    if _is_public_transit_route(user_prompt, history):
        origin, destination = _extract_origin_destination(user_prompt, history)
        if origin and destination:
            return f"{origin} to {destination} by public transport"

    if _is_qcri_minaretein_current(text):
        if _has_any(text, HEAT_WORDS) or _has_any(text, DRIVE_WORDS) or is_route_correction(user_prompt, history):
            return "Qatar Computing Research Institute to Minaretein Center by car"
        return "Qatar Computing Research Institute to Minaretein Center"

    if "qcri" in text and "education city metro" in text:
        if _has_any(text, HEAT_WORDS) or _has_any(text, DRIVE_WORDS):
            return "Qatar Computing Research Institute to Education City Metro Station by car"
        return "Qatar Computing Research Institute to Education City Metro Station"

    if is_route_correction(user_prompt, history):
        origin, destination = _extract_last_route(history)
        if origin and destination:
            if _has_any(text, PUBLIC_TRANSPORT_WORDS):
                return f"{origin} to {destination} by public transport"
            return f"{origin} to {destination} by car"

    return q


def should_add_web_for_route(user_prompt):
    text = _clean(user_prompt)
    return any(word in text for word in ["tram", "shuttle", "tunnel", "covered walkway", "indoor route", "metro schedule", "bus"])


def _improve_all_queries(router_data, user_prompt, history):
    """Apply Qatar-scoping query improvement to whatever tools are in the plan.

    This is pure value-add and never changes which tools run. It only rewrites
    the per-tool query strings so Fanar's chosen tools receive well-scoped,
    Qatar-local queries.
    """
    tools = router_data.get("tools", [])
    router_data.setdefault("queries", {})
    q = router_data["queries"]

    if "route_plan" in tools:
        q["route_plan"] = improve_route_query(q.get("route_plan", ""), user_prompt, history)
        # Fanar may forget that a transit prompt also wants live web context.
        if should_add_web_for_route(user_prompt) and "web_search" not in tools:
            tools.append("web_search")
            q["web_search"] = improve_web_query("", user_prompt, history)
    if "web_search" in tools:
        q["web_search"] = improve_web_query(q.get("web_search", ""), user_prompt, history)
    if "place_lookup" in tools:
        q["place_lookup"] = improve_place_query(q.get("place_lookup", ""), user_prompt, history)
    if "web_scrape" in tools:
        q["web_scrape"] = improve_web_scrape_query(q.get("web_scrape", ""), user_prompt, history)
    if "calendar_event" in tools:
        q["calendar_event"] = improve_calendar_query(q.get("calendar_event", ""), user_prompt, history)
    if "time_task" in tools:
        q["time_task"] = improve_time_task_query(q.get("time_task", ""), user_prompt, history)
    if "location_resolver" in tools:
        q["location_resolver"] = improve_location_resolver_query(q.get("location_resolver", ""), user_prompt, history)

    router_data["tools"] = tools
    return router_data


def _local_rule_plan(user_prompt, history):
    """Deterministic fallback/correction plans, keyed by intent predicate.

    Returns a router_data dict if a local rule confidently applies, else None.
    In the inverted design this is a SAFETY NET: it is consulted only when
    Fanar's own plan is empty/unusable, or to correct a specific known-wrong
    routing. It is no longer an unconditional override.
    """
    # Calendar + scrape combined
    if _is_calendar_request(user_prompt, history) and _is_web_scrape_request(user_prompt, history):
        return {
            "tools": ["web_scrape", "calendar_event"],
            "queries": {
                "web_scrape": improve_web_scrape_query("", user_prompt, history),
                "calendar_event": improve_calendar_query("", user_prompt, history),
            },
            "reason": "local_scrape_and_calendar_rule", "confidence": 1.0,
        }
    if _is_location_resolver_request(user_prompt, history):
        return {
            "tools": ["location_resolver"],
            "queries": {"location_resolver": improve_location_resolver_query("", user_prompt, history)},
            "reason": "local_location_resolver_agent_rule", "confidence": 1.0,
        }
    if _is_time_task_parse_request(user_prompt, history):
        return {
            "tools": ["time_task"],
            "queries": {"time_task": improve_time_task_query("", user_prompt, history)},
            "reason": "local_timetask_agent_rule", "confidence": 1.0,
        }
    if _is_calendar_request(user_prompt, history):
        return {
            "tools": ["calendar_event"],
            "queries": {"calendar_event": improve_calendar_query("", user_prompt, history)},
            "reason": "local_calendar_event_rule", "confidence": 1.0,
        }
    if _is_web_scrape_request(user_prompt, history):
        return {
            "tools": ["web_scrape"],
            "queries": {"web_scrape": improve_web_scrape_query("", user_prompt, history)},
            "reason": "local_web_scrape_rule", "confidence": 1.0,
        }
    if _is_location_disambiguation_request(user_prompt, history):
        destination = _destination_after_marker(user_prompt) or _find_location(user_prompt, "")
        origin = _route_origin_for_disambiguation(user_prompt, history)
        tools = ["place_lookup", "web_search"]
        queries = {
            "place_lookup": destination,
            "web_search": _official_disambiguation_web_query(user_prompt),
        }
        if origin:
            tools.insert(0, "route_plan")
            queries["route_plan"] = f"{origin} to {destination} by public transport"
        return {"tools": tools, "queries": queries, "reason": "local_location_disambiguation_rule", "confidence": 1.0}
    if _is_destination_access_request(user_prompt, history):
        return {
            "tools": ["route_plan", "place_lookup", "web_search"],
            "queries": {
                "route_plan": improve_route_query("", user_prompt, history),
                "place_lookup": improve_place_query("", user_prompt, history),
                "web_search": improve_web_query("", user_prompt, history),
            },
            "reason": "local_destination_access_rule", "confidence": 1.0,
        }
    if _is_food_recommendation_request(user_prompt, history):
        return {
            "tools": ["place_lookup"],
            "queries": {"place_lookup": improve_place_query("", user_prompt, history)},
            "reason": "local_lucky_food_recommendation_rule", "confidence": 1.0,
        }
    if _is_resort_experience_request(user_prompt, history):
        return {
            "tools": ["place_lookup", "web_search"],
            "queries": {
                "place_lookup": improve_place_query("", user_prompt, history),
                "web_search": improve_web_query("", user_prompt, history),
            },
            "reason": "local_qatar_resort_experience_rule", "confidence": 1.0,
        }
    if _is_photo_spot_request(user_prompt, history):
        return {
            "tools": ["place_lookup", "web_search"],
            "queries": {
                "place_lookup": improve_place_query("", user_prompt, history),
                "web_search": improve_web_query("", user_prompt, history),
            },
            "reason": "local_qatar_photo_spots_rule", "confidence": 1.0,
        }
    if _is_public_transit_route(user_prompt, history) or _is_public_transport_followup(user_prompt, history):
        tools = ["route_plan"]
        queries = {"route_plan": improve_route_query("", user_prompt, history)}
        if _needs_live_transit_web(user_prompt):
            tools.append("web_search")
            queries["web_search"] = improve_web_query("", user_prompt, history)
        return {"tools": tools, "queries": queries, "reason": "local_network_transit_route_rule", "confidence": 1.0}
    if _is_nightlife_request(user_prompt, history):
        return {
            "tools": ["place_lookup"],
            "queries": {"place_lookup": improve_place_query("", user_prompt, history)},
            "reason": "local_qatar_nightlife_scope_rule", "confidence": 1.0,
        }
    if is_budget_followup(user_prompt, history):
        return {
            "tools": ["place_lookup", "web_search"],
            "queries": {"place_lookup": improve_place_query("", user_prompt, history), "web_search": improve_web_query("", user_prompt, history)},
            "reason": "local_budget_followup_context_rule", "confidence": 1.0,
        }
    _text = _clean(user_prompt)
    if _is_qcri_minaretein_current(_text) and ("how do i get" in _text or "directions" in _text or _has_any(_text, HEAT_WORDS) or _has_any(_text, DRIVE_WORDS)):
        return {"tools": ["route_plan"], "queries": {"route_plan": improve_route_query("", user_prompt, history)}, "reason": "local_qcri_minaretein_route_rule", "confidence": 1.0}
    if is_route_correction(user_prompt, history):
        return {"tools": ["route_plan"], "queries": {"route_plan": improve_route_query("", user_prompt, history)}, "reason": "local_route_correction_rule", "confidence": 1.0}
    if is_directions_followup(user_prompt, history):
        origin = _extract_recent_user_location(history)
        destination = _extract_last_place(history)
        if destination:
            return {"tools": ["route_plan"], "queries": {"route_plan": f"{origin} to {destination}"}, "reason": "local_directions_followup_rule", "confidence": 1.0}
    if _is_nearby_food_request(user_prompt):
        tools = ["place_lookup"]
        queries = {"place_lookup": improve_place_query("", user_prompt, history)}
        if _is_qahwa_dates_request(user_prompt) or "highly rated" in _text:
            tools.append("web_search")
            queries["web_search"] = improve_web_query("", user_prompt, history)
        return {"tools": tools, "queries": queries, "reason": "local_nearby_food_place_rule", "confidence": 1.0}
    return None


# Specific known-wrong corrections: cases where if Fanar picks these tools we
# override, because the deterministic local handling is provably better.
def _should_override_fanar(user_prompt, history, router_data):
    """Return a corrected plan ONLY when Fanar is provably wrong for a
    high-value, well-tested intent. Conservative and ADDITIVE: we keep Fanar's
    useful tools (e.g. its web_search) and add the missing deterministic one.
    """
    fanar_tools = list(router_data.get("tools", []) or [])
    fanar_queries = dict(router_data.get("queries", {}) or {})

    # Transit routes: clearly a public-transit request but Fanar missed route_plan.
    if (_is_public_transit_route(user_prompt, history) or _is_public_transport_followup(user_prompt, history)):
        if "route_plan" not in fanar_tools:
            plan = _local_rule_plan(user_prompt, history)
            if plan:
                # Preserve any web_search Fanar already wanted.
                if "web_search" in fanar_tools and "web_search" not in plan["tools"]:
                    plan["tools"].append("web_search")
                    plan["queries"]["web_search"] = improve_web_query(
                        fanar_queries.get("web_search", ""), user_prompt, history)
                return plan
    # Calendar creation request Fanar missed.
    if _is_calendar_request(user_prompt, history) and "calendar_event" not in fanar_tools:
        return _local_rule_plan(user_prompt, history)
    # Location disambiguation (DECC vs QNCC) must not be answered as plain chat.
    if _is_location_disambiguation_request(user_prompt, history) and not fanar_tools:
        return _local_rule_plan(user_prompt, history)
    return None


def apply_local_router_rules(user_prompt, history, router_data):
    """Fanar-led routing with deterministic guardrails as a safety net.

    Order of trust:
      1. Hard deterministic non-LLM answers (greetings/GPS/identity/no-op).
      2. Fanar's tool selection is the DEFAULT plan; we improve its queries.
      3. If Fanar returned nothing usable, fall back to a local rule plan.
      4. Narrow, well-tested corrections override Fanar only when it is
         provably wrong for a high-value intent (transit/calendar/disambiguation).
    """
    text = _clean(user_prompt)

    # 1. Deterministic direct answers (no tool, no Fanar responder).
    direct = direct_answer_for_prompt(user_prompt, history)
    if direct:
        return {"tools": [], "queries": {}, "reason": "local_direct_answer_rule", "confidence": 1.0, "direct_answer": direct}

    if force_no_tool(user_prompt):
        return {"tools": [], "queries": {}, "reason": "local_no_tool_rule", "confidence": 1.0}

    fanar_tools = list(router_data.get("tools", []) or [])

    # 4. Narrow correction: Fanar provably wrong for a high-value intent.
    override = _should_override_fanar(user_prompt, history, router_data)
    if override:
        override["reason"] = override.get("reason", "local_rule") + "_correction"
        return override

    # 2. Trust Fanar when it produced a usable plan: just improve its queries.
    if fanar_tools:
        return _improve_all_queries(router_data, user_prompt, history)

    # 3. Fanar returned no tools — consult the local rule net.
    fallback = _local_rule_plan(user_prompt, history)
    if fallback:
        return fallback

    # Nothing fired anywhere: hand back Fanar's (empty) plan unchanged.
    return router_data
