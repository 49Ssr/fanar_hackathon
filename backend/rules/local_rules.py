"""Deterministic guardrails for Qaarib.

These rules sit around the Fanar router. The model can still route most
requests, but demo-critical Qatar cases should not depend on the model being
perfect JSON or perfectly context-aware.
"""

import re

NO_TOOL_EXACT={
    "hi","hello","hey","yo","salam","salaam","السلام عليكم",
    "assalamu alaikum","as-salamu alaykum","salam alikum","salam alaikum",
    "salaam alaikum","salaam alaykum","hala","hala wala","هلا","هلا والله",
    "ahlan","marhaba","thanks","thank you","cheers","ma salama","مع السلامة"
}

GREETING_WORDS={
    "hi","hello","hey","yo","salam","salaam","alaikum","alaykum","alikum",
    "assalamu","as-salamu","hala","wala","ahlan","marhaba","bro","brother",
    "habibi","حبيبي","هلا","السلام","عليكم"
}

NO_TOOL_CONTAINS=[
    "why do you take so long",
    "why are you slow",
    "what are you",
    "who are you",
    "what can you do",
    "those previous prompts were tests",
    "i'm gonna test you",
    "im gonna test you",
    "your responses need",
]

BUDGET_WORDS=[
    "budget","cheap","cheaper","affordable","wallet","price","low cost",
    "not expensive","budget friendliness","budget-friendly"
]

FOOD_PLACE_WORDS=[
    "qahwa","gahwa","arabic coffee","coffee","karak","dates","date",
    "cafe","café","restaurant","food","spot"
]

HEAT_WORDS=[
    "sweat","sweating","hot","heat","melting","fountain","outside",
    "shade","shaded","covered","tunnel","indoor"
]

DRIVE_WORDS=["uber","taxi","karwa","car","drive","driving","cab"]

ROUTE_COMPLAINT_WORDS=[
    "are you nuts","what on earth","that was a simple request","quickest way would be",
    "quickest would be","not walk","walking?","walk?","dumb","stupid"
]

LOCATION_HINTS={
    "msheireb metro":"Msheireb Metro Station, Doha, Qatar",
    "msheireb":"Msheireb Downtown Doha, Qatar",
    "mshereib":"Msheireb Downtown Doha, Qatar",
    "mushreib":"Msheireb Downtown Doha, Qatar",
    "souq waqif":"Souq Waqif Doha, Qatar",
    "education city metro":"Education City Metro Station, Doha, Qatar",
    "education city":"Education City Doha, Qatar",
    "qcri":"Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku":"HBKU Doha, Qatar",
    "minaretein":"Minaretein Center, Education City, Doha, Qatar",
    "minaratein":"Minaretein Center, Education City, Doha, Qatar",
    "minareten":"Minaretein Center, Education City, Doha, Qatar",
}

QATAR_SOURCE_HINTS=[
    "educationcity.qa","qf.org.qa","hbku.edu.qa","qatarrail.qa",
    "mowasalat.com","visitqatar.com"
]


def _clean(text):
    return re.sub(r"\s+"," ",text.lower().strip())


def _has_any(text,words):
    return any(word in text for word in words)


def _is_short_greeting(text):
    if text in NO_TOOL_EXACT:
        return True

    # Handles things like "salam brother" without searching the web.
    tokens=[t.strip("!?.،,;:") for t in text.split()]
    if 1 <= len(tokens) <= 4 and any(t in {"salam","salaam","hello","hi","hey","hala"} for t in tokens):
        return all(t in GREETING_WORDS for t in tokens if t)

    return False


def force_no_tool(user_prompt):
    text=_clean(user_prompt)
    if _is_short_greeting(text):
        return True
    return any(phrase in text for phrase in NO_TOOL_CONTAINS)


def _find_location(text,history=""):
    joined=f"{text}\n{_clean(history)}"
    # More specific keys first.
    for key in sorted(LOCATION_HINTS,key=len,reverse=True):
        if key in joined:
            return LOCATION_HINTS[key]
    return "Doha, Qatar"


def _previous_food_place_context(history):
    text=_clean(history)
    return _has_any(text,FOOD_PLACE_WORDS) and any(key in text for key in LOCATION_HINTS)


def is_budget_followup(user_prompt,history=""):
    text=_clean(user_prompt)
    followup_markers=["which place","which one","what about","recommend","better","best"]
    return (
        _has_any(text,BUDGET_WORDS)
        and (_has_any(text,followup_markers) or len(text.split())<=10)
        and _previous_food_place_context(history)
    )


def _is_qahwa_dates_request(user_prompt):
    text=_clean(user_prompt)
    return ("qahwa" in text or "gahwa" in text or "arabic coffee" in text) and "date" in text


def _is_nearby_food_request(user_prompt):
    text=_clean(user_prompt)
    return _has_any(text,FOOD_PLACE_WORDS) and ("near" in text or "nearby" in text or "rn" in text or "right now" in text or any(k in text for k in LOCATION_HINTS))


def _is_qcri_minaretein_current(text):
    return "qcri" in text and ("minaretein" in text or "minaratein" in text or "minareten" in text)


def _history_has_qcri_minaretein(history):
    text=_clean(history)
    return "qcri" in text and ("minaretein" in text or "minaratein" in text or "minareten" in text)


def _extract_last_route(history):
    """Return last origin/destination from stored route tool output if present."""
    origins=re.findall(r"ORIGIN:\s*(.+)",history)
    destinations=re.findall(r"DESTINATION:\s*(.+)",history)
    if origins and destinations:
        return origins[-1].strip(),destinations[-1].strip()
    return None,None


def is_route_heat_request(user_prompt):
    text=_clean(user_prompt)
    return _has_any(text,HEAT_WORDS)


def is_route_correction(user_prompt,history=""):
    text=_clean(user_prompt)
    return _has_any(text,ROUTE_COMPLAINT_WORDS) and "route_plan" in history.lower()


def is_directions_followup(user_prompt,history=""):
    text=_clean(user_prompt)
    if "route_plan" in history.lower() and _history_has_qcri_minaretein(history):
        return False
    direction_words=["directions","get there","how do i get there","take me there","route me"]
    explicit_route=" to " in f" {text} "
    return _has_any(text,direction_words) and not explicit_route and "place_lookup" in history.lower()


def _extract_last_place(history):
    # Finds the first result from the latest place_lookup block.
    blocks=re.findall(r"\[TOOL:place_lookup:[^\]]+\](.*?)(?=\n\n\[|$)",history,flags=re.S)
    if not blocks:
        return None
    latest=blocks[-1]
    match=re.search(r"RESULTS:\s*\n1\.\s*(.+)",latest)
    if not match:
        return None
    title=match.group(1).strip()
    if not title or title.lower().startswith("no results"):
        return None
    return title


def _extract_recent_user_location(history):
    users=re.findall(r"\[USER\]\n(.*?)(?=\n\[ASSISTANT\]|\n\n\[|$)",history,flags=re.S)
    for msg in reversed(users):
        text=_clean(msg)
        for key in sorted(LOCATION_HINTS,key=len,reverse=True):
            if key in text:
                return LOCATION_HINTS[key]
    return "Doha, Qatar"


def improve_web_query(query,user_prompt,history=""):
    text=f"{_clean(user_prompt)}\n{_clean(history)}"
    base=query.strip() if query and query.strip() else user_prompt.strip()

    if is_budget_followup(user_prompt,history):
        location=_find_location(user_prompt,history)
        return f"affordable qahwa dates cafe near {location} Qatar"

    if _is_qahwa_dates_request(user_prompt):
        location=_find_location(user_prompt,history)
        return f"qahwa dates cafe near {location} Doha"

    if "education city" in text or "qcri" in text or "hbku" in text:
        return f"{base} site:educationcity.qa OR site:qf.org.qa OR site:hbku.edu.qa"

    if "metro" in text or "qatar rail" in text or "tram" in text or "bus" in text:
        return f"{base} site:qatarrail.qa OR site:mowasalat.com OR site:educationcity.qa"

    if "event" in text or "events" in text or "this weekend" in text:
        return f"{base} site:visitqatar.com OR site:educationcity.qa OR site:qf.org.qa"

    return base


def improve_place_query(query,user_prompt,history=""):
    text=_clean(user_prompt)
    base=query.strip() if query and query.strip() else user_prompt.strip()

    if is_budget_followup(user_prompt,history):
        location=_find_location(user_prompt,history)
        return f"affordable cafe qahwa dates near {location}"

    if _is_qahwa_dates_request(user_prompt):
        location=_find_location(user_prompt,history)
        return f"qahwa dates cafe near {location}"

    if _is_nearby_food_request(user_prompt):
        location=_find_location(user_prompt,history)
        want=[]
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


def improve_route_query(query,user_prompt,history=""):
    text=_clean(user_prompt)
    q=query.strip() if query else user_prompt.strip()

    if _is_qcri_minaretein_current(text):
        if _has_any(text,HEAT_WORDS) or _has_any(text,DRIVE_WORDS) or is_route_correction(user_prompt,history):
            return "Qatar Computing Research Institute to Minaretein Center by car"
        return "Qatar Computing Research Institute to Minaretein Center"

    if "qcri" in text and "education city metro" in text:
        if _has_any(text,HEAT_WORDS) or _has_any(text,DRIVE_WORDS):
            return "Qatar Computing Research Institute to Education City Metro Station by car"
        return "Qatar Computing Research Institute to Education City Metro Station"

    if "mansoura" in text and ("ras abu aboud" in text or "ras bu abboud" in text):
        return "Mansoura Metro Station to Ras Abu Aboud Metro Station"

    # If user is correcting a bad walking answer, re-route the same route as car.
    if is_route_correction(user_prompt,history):
        origin,destination=_extract_last_route(history)
        if origin and destination:
            return f"{origin} to {destination} by car"

    return q


def should_add_web_for_route(user_prompt):
    text=_clean(user_prompt)
    # Do not add web just because user says "sweating". That caused empty web
    # results to overpower a valid route. Web is only for explicit campus transit info.
    campus_lookup_words=["tram","shuttle","tunnel","covered walkway","indoor route","metro schedule","bus"]
    return any(word in text for word in campus_lookup_words)


def apply_local_router_rules(user_prompt,history,router_data):
    """Patch/override the model router for demo-critical cases."""
    text=_clean(user_prompt)

    if force_no_tool(user_prompt):
        return {"tools":[],"queries":{},"reason":"local_no_tool_rule","confidence":1.0}

    if is_budget_followup(user_prompt,history):
        return {
            "tools":["place_lookup","web_search"],
            "queries":{
                "place_lookup":improve_place_query("",user_prompt,history),
                "web_search":improve_web_query("",user_prompt,history),
            },
            "reason":"local_budget_followup_context_rule",
            "confidence":1.0,
        }

    if _is_qcri_minaretein_current(text) and ("how do i get" in text or "directions" in text or _has_any(text,HEAT_WORDS) or _has_any(text,DRIVE_WORDS)):
        return {
            "tools":["route_plan"],
            "queries":{"route_plan":improve_route_query("",user_prompt,history)},
            "reason":"local_qcri_minaretein_route_rule",
            "confidence":1.0,
        }

    if is_route_correction(user_prompt,history):
        return {
            "tools":["route_plan"],
            "queries":{"route_plan":improve_route_query("",user_prompt,history)},
            "reason":"local_route_correction_rule",
            "confidence":1.0,
        }

    if is_directions_followup(user_prompt,history):
        origin=_extract_recent_user_location(history)
        destination=_extract_last_place(history)
        if destination:
            return {
                "tools":["route_plan"],
                "queries":{"route_plan":f"{origin} to {destination}"},
                "reason":"local_directions_followup_rule",
                "confidence":1.0,
            }

    if _is_nearby_food_request(user_prompt):
        tools=["place_lookup"]
        queries={"place_lookup":improve_place_query(router_data.get("queries",{}).get("place_lookup",""),user_prompt,history)}
        if _is_qahwa_dates_request(user_prompt) or "highly rated" in text:
            tools.append("web_search")
            queries["web_search"]=improve_web_query(router_data.get("queries",{}).get("web_search",""),user_prompt,history)
        return {
            "tools":tools,
            "queries":queries,
            "reason":"local_nearby_food_place_rule",
            "confidence":1.0,
        }

    # Keep existing model route, but polish route queries and add web only when truly useful.
    if "route_plan" in router_data.get("tools",[]):
        router_data.setdefault("queries",{})
        router_data["queries"]["route_plan"]=improve_route_query(router_data["queries"].get("route_plan",""),user_prompt,history)
        if should_add_web_for_route(user_prompt) and "web_search" not in router_data["tools"]:
            router_data["tools"].append("web_search")
            router_data["queries"]["web_search"]=improve_web_query("",user_prompt,history)

    return router_data
