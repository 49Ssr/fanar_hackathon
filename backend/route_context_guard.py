import re

LOCATION_HINTS = {
    "msheireb metro": "Msheireb",
    "msheireb station": "Msheireb",
    "msheireb": "Msheireb",
    "mshereib": "Msheireb",
    "mushreib": "Msheireb",
    "souq waqif": "Souq Waqif",
    "ras abu aboud": "Ras Bu Aboud",
    "ras bu aboud": "Ras Bu Aboud",
    "ras bu abboud": "Ras Bu Aboud",
    "hia t1": "Hamad International Airport T1",
    "hia": "Hamad International Airport T1",
    "airport": "Hamad International Airport T1",
    "hamad international airport": "Hamad International Airport T1",
    "education city": "Education City",
    "qcri": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "qnl": "Qatar National Library",
    "qatar national library": "Qatar National Library",
    "al shaqab": "Al Shaqab",
    "legtaifiya": "Legtaifiya",
    "lusail": "Lusail",
    "lusail marina": "Lusail Marina",
    "mesaied": "Mesaieed, Qatar",
    "mesaieed": "Mesaieed, Qatar",
    "al wakra": "Al Wakra",
    "wakra": "Al Wakra",
}

HERE_MARKERS = [
    "from here", "from my location", "from where i am", "from where i'm at",
    "from where im at", "near me", "i am here", "i'm here", "im here",
    "current location", "my location",
]

ORIGIN_MARKERS = [
    "i'm stuck in", "im stuck in", "i am stuck in", "stuck in",
    "i'm at", "im at", "i am at", "i'm in", "im in", "i am in",
    "currently at", "currently in", "near", "inside",
]

DEST_MARKERS = [
    "get to", "go to", "reach", "head to", "route to", "directions to", "take me to", "show me how to get to",
]


def clean(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def locations_in(text):
    c = clean(text)
    found = []
    for key, value in sorted(LOCATION_HINTS.items(), key=lambda kv: len(kv[0]), reverse=True):
        for m in re.finditer(r"\b" + re.escape(key) + r"\b", c):
            if any(not (m.end() <= s or m.start() >= e) for s, e, _ in found):
                continue
            found.append((m.start(), m.end(), value))
    return sorted(found, key=lambda x: x[0])


def current_location_from_context(text):
    # Matches server-injected block: lat=25.123456 lng=51.123456
    m = re.search(r"lat=([-+]?\d+(?:\.\d+)?)\s+lng=([-+]?\d+(?:\.\d+)?)", text or "", flags=re.I)
    if not m:
        return None
    return f"{m.group(1)},{m.group(2)}"


def latest_user_location(history):
    coord = current_location_from_context(history)
    if coord:
        return coord
    users = re.findall(r"\[USER\]\s*\n(.*?)(?=\n\[ASSISTANT\]|\n\n\[|$)", history or "", flags=re.S)
    for msg in reversed(users):
        locs = locations_in(msg)
        if locs:
            return locs[-1][2]
    return None


def destination_from_prompt(prompt):
    c = clean(prompt)
    locs = locations_in(prompt)
    if not locs:
        return None
    for marker in DEST_MARKERS:
        idx = c.find(marker)
        if idx >= 0:
            after = [x for x in locs if x[0] >= idx + len(marker)]
            if after:
                return after[0][2]
    return locs[-1][2]


def explicit_origin_from_prompt(prompt):
    c = clean(prompt)
    locs = locations_in(prompt)
    if not locs:
        return None
    for marker in ORIGIN_MARKERS:
        for m in re.finditer(re.escape(marker), c):
            after = [x for x in locs if x[0] >= m.end()]
            if after:
                return after[0][2]
    return None


def has_here_marker(prompt):
    c = clean(prompt)
    return any(marker in c for marker in HERE_MARKERS)


def repair_route_query(query, user_prompt, history=""):
    destination = destination_from_prompt(user_prompt)
    if not destination:
        return query

    origin = explicit_origin_from_prompt(user_prompt)
    if not origin and has_here_marker(user_prompt):
        origin = latest_user_location(history)

    if not origin:
        return query

    if origin == destination:
        return f"{origin} to {destination} by walking"

    c = clean(user_prompt)
    if any(x in c for x in ["walk", "walking", "on foot"]):
        mode = "by walking"
    elif any(x in c for x in ["taxi", "uber", "karwa", "drive", "car"]):
        mode = "by car"
    else:
        mode = "by public transport"
    return f"{origin} to {destination} {mode}"
