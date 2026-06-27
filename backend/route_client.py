import json
import os
import re
from collections import deque, defaultdict
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
TRANSIT_PATH = BASE_DIR / "data" / "qatar_transit_network.json"

load_dotenv(ENV_PATH)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

PUBLIC_MODE_WORDS = [
    "public transport", "transit", "metro", "metro card", "tram", "train", "rail", "bus",
    "no car", "without a car", "without car", "dont have a car", "don't have a car",
    "ran out of cash", "no cash",
]
DRIVE_WORDS = [" by car", " driving", " drive", " uber", " taxi", " karwa", " cab"]
WALK_WORDS = [" walk", " walking", " on foot"]

ALIASES = {
    "qcri": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "qatar computing research institute": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku qcri": "Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "hbku main branch": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "hamad bin khalifa university": "Hamad Bin Khalifa University, Education City, Doha, Qatar",
    "minaretein": "Minaretein Center, Education City, Doha, Qatar",
    "minaretein center": "Minaretein Center, Education City, Doha, Qatar",
    "minaratein": "Minaretein Center, Education City, Doha, Qatar",
    "minareten": "Minaretein Center, Education City, Doha, Qatar",
    "education city mosque": "Education City Mosque, Education City, Doha, Qatar",
    "msheireb metro": "Msheireb Metro Station, Doha, Qatar",
    "msheireb metro station": "Msheireb Metro Station, Doha, Qatar",
    "education city metro": "Education City Metro Station, Doha, Qatar",
    "education city metro station": "Education City Metro Station, Doha, Qatar",
    "al shaqab": "Al Shaqab Metro Station, Doha, Qatar",
    "al-shaqab": "Al Shaqab Metro Station, Doha, Qatar",
    "al rayyan al qadeem": "Al Rayyan Al Qadeem Metro Station, Doha, Qatar",
    "matar qadeem": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "al matar al qadeem": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "old airport": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "family food centre matar qadeem": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "matar qadeem family food centre": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "family food center matar qadeem": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "matar qadeem family food center": "Al Matar Al Qadeem Metro Station, Doha, Qatar",
    "wakra": "Al Wakra Metro Station, Doha, Qatar",
    "al wakra": "Al Wakra Metro Station, Doha, Qatar",
    "ras bu funtas": "Ras Bu Fontas Metro Station, Doha, Qatar",
    "ras bu fontas": "Ras Bu Fontas Metro Station, Doha, Qatar",
    "ras abu aboud": "Ras Bu Aboud Metro Station, Doha, Qatar",
    "ras bu aboud": "Ras Bu Aboud Metro Station, Doha, Qatar",
    "ras bu abboud": "Ras Bu Aboud Metro Station, Doha, Qatar",
    "oqba bin nafe": "Oqba Ibn Nafie Metro Station, Doha, Qatar",
    "oqba ibn nafie": "Oqba Ibn Nafie Metro Station, Doha, Qatar",
    "qnl": "Qatar National Library Metro Station, Doha, Qatar",
    "qatar national library": "Qatar National Library Metro Station, Doha, Qatar",
    "legtaifiya": "Legtaifiya Metro Station, Doha, Qatar",
    "lusail marina": "Lusail Marina Promenade, Doha, Qatar",
    "hia": "Hamad International Airport Terminal 1, Doha, Qatar",
    "hia t1": "Hamad International Airport Terminal 1, Doha, Qatar",
    "hamad international airport": "Hamad International Airport Terminal 1, Doha, Qatar",
    "qatar university": "Qatar University Metro Station, Doha, Qatar",
    "qu": "Qatar University Metro Station, Doha, Qatar",
    "national museum": "National Museum Metro Station, Doha, Qatar",
    "national museum of qatar": "National Museum of Qatar, Doha, Qatar",
    "katara": "Katara Metro Station, Doha, Qatar",
    "katara cultural village": "Katara Cultural Village, Doha, Qatar",
    "west bay": "West Bay Metro Station, Doha, Qatar",
    "dohaexhibition": "DECC Metro Station, Doha, Qatar",
    "doha exhibition and convention center": "DECC Metro Station, Doha, Qatar",
    "doha exhibition and convention centre": "DECC Metro Station, Doha, Qatar",
    "souq waqif": "Souq Waqif Metro Station, Doha, Qatar",
    "souq": "Souq Waqif Metro Station, Doha, Qatar",
    "corniche": "Corniche Metro Station, Doha, Qatar",
    "lusail": "Lusail Metro Station, Doha, Qatar",
    "the pearl": "The Pearl Island, Doha, Qatar",
    "pearl qatar": "The Pearl Island, Doha, Qatar",
    "the pearl qatar": "The Pearl Island, Doha, Qatar",
    "mia": "Museum of Islamic Art, Doha, Qatar",
    "museum of islamic art": "Museum of Islamic Art, Doha, Qatar",
    "mia park": "MIA Park, Doha, Qatar",
    "villaggio": "Villaggio Mall, Doha, Qatar",
    "aspire": "Aspire Zone, Doha, Qatar",
    "aspire zone": "Aspire Zone, Doha, Qatar",
    "khalifa stadium": "Khalifa International Stadium, Doha, Qatar",
    "khalifa international stadium": "Khalifa International Stadium, Doha, Qatar",
    "stadium 974": "Stadium 974, Doha, Qatar",
    "974 stadium": "Stadium 974, Doha, Qatar",
    "qatar foundation": "Qatar Foundation, Education City, Doha, Qatar",
    "qf": "Qatar Foundation, Education City, Doha, Qatar",
}

RED_MAIN_NORTH_TO_SOUTH = [
    "Lusail", "Qatar University", "Legtaifiya", "Katara", "Al Qassar", "DECC",
    "West Bay", "Corniche", "Al Bidda", "Msheireb", "Al Doha Al Jadeeda",
    "Umm Ghuwailina", "Al Matar Al Qadeem", "Oqba Ibn Nafie",
]
RED_AL_WAKRA_BRANCH = ["Oqba Ibn Nafie", "Free Zone", "Ras Bu Fontas", "Al Wakra"]
RED_AIRPORT_BRANCH = ["Oqba Ibn Nafie", "Hamad International Airport T1"]
GREEN_WEST_TO_EAST = [
    "Al Riffa", "Education City", "Qatar National Library", "Al Shaqab",
    "Al Rayyan Al Qadeem", "Al Messila", "Hamad Hospital", "The White Palace",
    "Al Bidda", "Msheireb", "Al Mansoura",
]
GOLD_WEST_TO_EAST = [
    "Al Aziziyah", "Sport City", "Al Waab", "Al Sudan", "Joaan", "Al Sadd",
    "Bin Mahmoud", "Msheireb", "Souq Waqif", "National Museum", "Ras Bu Aboud",
]

def _direction_from_order(stops, order, west_label, east_label):
    try:
        start_i = order.index(stops[0])
        end_i = order.index(stops[-1])
    except ValueError:
        return ""
    if end_i < start_i:
        return west_label
    if end_i > start_i:
        return east_label
    return ""

def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _load_transit_data():
    try:
        return json.loads(TRANSIT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"nodes": {}, "edges": []}


def _alias_index(data):
    index = {}
    for node, meta in data.get("nodes", {}).items():
        index[_clean(node)] = node
        for alias in meta.get("aliases", []):
            index[_clean(alias)] = node
        index[_clean(node + " metro station")] = node
        index[_clean(node + " station")] = node
    return index


def _contains_alias(cleaned, alias):
    # Do not match tiny aliases like 'qu' inside arbitrary words.
    if len(alias) <= 3:
        return re.search(r"\b" + re.escape(alias) + r"\b", cleaned) is not None
    return alias in cleaned


def _transit_node_for(text, data=None):
    data = data or _load_transit_data()
    index = _alias_index(data)
    cleaned = _clean(text)

    if cleaned in index:
        return index[cleaned]

    stripped = cleaned
    stripped = re.sub(r"\b(doha|qatar|metro station|station|promenade|terminal 1|t1)\b", " ", stripped)
    stripped = _clean(stripped.strip(" ,."))
    if stripped in index:
        return index[stripped]

    # Hard demo aliases for common spoken place names not always in the graph JSON.
    hard = {
        "matar qadeem": "Al Matar Al Qadeem",
        "al matar al qadeem": "Al Matar Al Qadeem",
        "old airport": "Al Matar Al Qadeem",
        "family food centre": "Al Matar Al Qadeem",
        "family food center": "Al Matar Al Qadeem",
        "ras abu aboud": "Ras Bu Aboud",
        "ras bu aboud": "Ras Bu Aboud",
        "ras bu abboud": "Ras Bu Aboud",
    }
    for alias, node in hard.items():
        if alias in cleaned:
            return node

    for alias, node in sorted(index.items(), key=lambda kv: len(kv[0]), reverse=True):
        if alias and _contains_alias(cleaned, alias):
            return node

    return None


def canonical_place(text):
    cleaned = _clean(text).strip(" .")

    data = _load_transit_data()
    transit_node = _transit_node_for(cleaned, data)
    if transit_node:
        return transit_node

    if cleaned in ALIASES:
        return ALIASES[cleaned]

    for key, value in sorted(ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        if _contains_alias(cleaned, key):
            return value

    if "qatar" not in cleaned and "doha" not in cleaned:
        return f"{text.strip()}, Doha, Qatar"

    return text.strip()


def split_route_query(query):
    """Return origin, destination, preferred mode: WALK, DRIVE, TRANSIT, or AUTO."""
    q = re.sub(r"\s+", " ", query.strip())
    lower = q.lower()

    mode = "AUTO"
    if any(word in lower for word in PUBLIC_MODE_WORDS):
        mode = "TRANSIT"
    elif any(word in lower for word in DRIVE_WORDS):
        mode = "DRIVE"
    elif any(word in lower for word in WALK_WORDS):
        mode = "WALK"

    q = re.sub(
        r"\b(by public transport|public transport|by transit|transit|metro card|by metro|metro|by tram|tram|by train|train|by rail|rail|by bus|bus|by car|by taxi|by uber|by karwa|driving|drive|by walking|by walk|walking|walk|on foot)\b",
        "",
        q,
        flags=re.I,
    ).strip()

    if " to " in q.lower():
        origin, destination = re.split(r"\s+to\s+", q, maxsplit=1, flags=re.I)
        return canonical_place(origin), canonical_place(destination), mode

    return canonical_place(q), "Education City Metro Station, Doha, Qatar", mode


def _graph(data):
    g = defaultdict(list)
    for edge in data.get("edges", []):
        a, b = edge["from"], edge["to"]
        payload = {"line": edge.get("line", "Transit"), "mode": edge.get("mode", "transit")}
        g[a].append((b, payload))
        g[b].append((a, payload))
    return g


def _shortest_path(data, start, goal):
    if not start or not goal:
        return None
    if start == goal:
        return [(start, None)]

    g = _graph(data)
    q = deque([(start, [(start, None)])])
    seen = {start}
    while q:
        node, path = q.popleft()
        for nxt, edge in g.get(node, []):
            if nxt in seen:
                continue
            new_path = path + [(nxt, edge)]
            if nxt == goal:
                return new_path
            seen.add(nxt)
            q.append((nxt, new_path))
    return None


def _group_segments(path):
    if not path or len(path) < 2:
        return []
    segments = []
    current_line = None
    current_mode = None
    current_stops = []

    for i in range(1, len(path)):
        prev = path[i - 1][0]
        node, edge = path[i]
        line = edge["line"]
        mode = edge["mode"]
        if current_line is None:
            current_line = line
            current_mode = mode
            current_stops = [prev, node]
        elif line == current_line:
            current_stops.append(node)
        else:
            segments.append({"line": current_line, "mode": current_mode, "stops": current_stops})
            current_line = line
            current_mode = mode
            current_stops = [prev, node]
    if current_line:
        segments.append({"line": current_line, "mode": current_mode, "stops": current_stops})
    return segments


def _direction_hint(segment):
    line = segment["line"]
    stops = segment["stops"]
    dest = stops[-1]

    if line == "Red Line airport branch":
        return "toward HIA T1" if dest == "Hamad International Airport T1" else "toward the main Red Line"
    if line == "Red Line Al Wakra branch":
        return _direction_from_order(stops, RED_AL_WAKRA_BRANCH, "toward the main Red Line", "toward Al Wakra")
    if line == "Red Line":
        return _direction_from_order(stops, RED_MAIN_NORTH_TO_SOUTH, "northbound toward Lusail", "southbound toward Msheireb; then follow Al Wakra / HIA T1 branch signage if continuing past Oqba Ibn Nafie")
    if line == "Green Line":
        return _direction_from_order(stops, GREEN_WEST_TO_EAST, "westbound toward Al Riffa", "eastbound toward Al Mansoura")
    if line == "Gold Line":
        return _direction_from_order(stops, GOLD_WEST_TO_EAST, "westbound toward Al Aziziyah", "eastbound toward Ras Bu Aboud")
    if "Lusail Tram" in line:
        return "toward the Marina/Lusail tram stops"
    if line == "Walking link":
        return "toward the destination"
    return ""

def _transit_summary(start, goal, segments):
    pure_walk_access = bool(segments) and all(seg.get("line") == "Walking link" for seg in segments)
    if pure_walk_access:
        parts = ["Final leg:"]
    else:
        parts = ["Quick route: Use public transport for this one."]
    previous_line = None

    for idx, seg in enumerate(segments, start=1):
        stops = seg["stops"]
        hint = _direction_hint(seg)
        line = seg["line"]

        if line == "Walking link":
            parts.append(f"Walk from {stops[0]} to {stops[-1]}. Use station signage and Maps for the exact exit/walking path.")
            previous_line = line
            continue

        if idx == 1:
            prefix = f"Start at {stops[0]}."
        elif previous_line and previous_line.startswith("Red Line") and line.startswith("Red Line"):
            prefix = f"Continue through {stops[0]}."
        elif previous_line and previous_line.startswith("Lusail Tram") and line.startswith("Lusail Tram"):
            prefix = f"Continue through {stops[0]}."
        else:
            prefix = f"Transfer at {stops[0]}."

        if hint:
            parts.append(f"{prefix} Take {line} {hint} to {stops[-1]}.")
        else:
            parts.append(f"{prefix} Take {line} to {stops[-1]}.")
        previous_line = line

    parts.append("Check live Qatar Rail / tram timings and platform signs before you tap in, but the network path is this.")
    return " ".join(parts)

def _maps_url(origin_title, destination_title, mode):
    if mode == "TRANSIT":
        travelmode = "transit"
    elif mode == "DRIVE":
        travelmode = "driving"
    else:
        travelmode = "walking"
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin_title)}"
        f"&destination={quote_plus(destination_title)}"
        f"&travelmode={travelmode}"
    )


def _transit_plan(origin_query, destination_query, requested_mode):
    data = _load_transit_data()
    origin_node = _transit_node_for(origin_query, data)
    dest_node = _transit_node_for(destination_query, data)

    if requested_mode != "TRANSIT" and not (origin_node and dest_node):
        return None

    if origin_node and dest_node:
        if origin_node == dest_node:
            o_short = str(origin_query).split(",")[0].strip()
            d_short = str(destination_query).split(",")[0].strip()
            if o_short.lower() == d_short.lower():
                summary = (f"These resolve to the same {origin_node} area. For the exact building/entrance, "
                           f"use the Maps link or on-site signage — it's a short local access leg, not a metro journey.")
            else:
                summary = (f"{o_short} and {d_short} resolve to the same {origin_node} area. For the exact "
                           f"entrance, use the Maps link or on-site signage — a short local access leg rather "
                           f"than a metro journey.")
            return [{
                "title": "Short local walk",
                "origin": origin_node,
                "destination": dest_node,
                "recommended_mode": "Walk",
                "travel_mode": "WALK",
                "summary": summary,
                "final_answer": summary + "\n\nMaps backup: " + _maps_url(origin_query, destination_query, "WALK"),
                "maps_url": _maps_url(origin_query, destination_query, "WALK"),
                "distance": "same area",
                "duration": "a few minutes on foot",
            }]
        path = _shortest_path(data, origin_node, dest_node)
        if path:
            segments = _group_segments(path)
            lines_used = []
            for seg in segments:
                if seg["line"] not in lines_used:
                    lines_used.append(seg["line"])
            map_mode = "WALK" if (requested_mode == "WALK" or all(seg.get("mode") == "walk" for seg in segments)) else "TRANSIT"
            travel_mode = "WALK" if map_mode == "WALK" else "TRANSIT"
            return [{
                "title": "Walking access leg" if travel_mode == "WALK" else "Transit route",
                "origin": origin_node,
                "destination": dest_node,
                "recommended_mode": " + ".join(lines_used),
                "travel_mode": travel_mode,
                "summary": _transit_summary(origin_node, dest_node, segments),
                "final_answer": _transit_summary(origin_node, dest_node, segments) + "\n\nMaps backup: " + _maps_url(origin_node, dest_node, map_mode),
                "maps_url": _maps_url(origin_node, dest_node, map_mode),
                "distance": f"{max(0, len(path)-1)} transit/walking hops",
                "duration": "Check live Qatar Rail timings / walking map",
            }]

    if requested_mode == "TRANSIT":
        return [{
            "title": "Public transport route",
            "origin": origin_query,
            "destination": destination_query,
            "recommended_mode": "Metro / tram / bus where available",
            "travel_mode": "TRANSIT",
            "summary": "Transit graph did not fully resolve both endpoints, so use the Maps transit route to the exact place and verify live timings/signage.",
            "final_answer": "Quick route: Use public transport to the exact destination, not just the nearest station. Open the transit map from " + str(origin_query) + " to " + str(destination_query) + "; it should include any station exit/walking leg where available. Verify live timings/signage before tapping in.\n\nMaps backup: " + _maps_url(origin_query, destination_query, "TRANSIT"),
            "maps_url": _maps_url(origin_query, destination_query, "TRANSIT"),
            "duration": "Check live timings",
        }]

    return None


def resolve_place(query):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.googleMapsUri",
    }
    body = {"textQuery": query, "pageSize": 1, "regionCode": "QA", "languageCode": "en"}
    response = requests.post(url, headers=headers, json=body, timeout=10)
    if not response.ok:
        print("Place resolve failed:", response.status_code, response.text[:500])
        response.raise_for_status()
    places = response.json().get("places", [])
    if not places:
        return None
    place = places[0]
    location = place.get("location", {})
    return {
        "title": place.get("displayName", {}).get("text", query),
        "address": place.get("formattedAddress", ""),
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
        "maps_url": place.get("googleMapsUri", ""),
    }


def seconds_to_minutes(duration_text):
    if not duration_text or not duration_text.endswith("s"):
        return ""
    seconds = int(float(duration_text[:-1]))
    minutes = max(1, round(seconds / 60))
    return f"{minutes} min"


def meters_to_km(meters):
    if meters is None:
        return ""
    if meters < 1000:
        return f"{int(meters)} m"
    return f"{meters / 1000:.1f} km"


def compute_route(origin_place, destination_place, travel_mode):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.description",
    }
    body = {
        "origin": {"location": {"latLng": {"latitude": origin_place["lat"], "longitude": origin_place["lng"]}}},
        "destination": {"location": {"latLng": {"latitude": destination_place["lat"], "longitude": destination_place["lng"]}}},
        "travelMode": travel_mode,
        "languageCode": "en",
    }
    response = requests.post(url, headers=headers, json=body, timeout=10)
    if not response.ok:
        print("Route compute failed:", response.status_code, response.text[:500])
        response.raise_for_status()
    routes = response.json().get("routes", [])
    if not routes:
        return None
    route = routes[0]
    return {
        "duration": seconds_to_minutes(route.get("duration", "")),
        "distance": meters_to_km(route.get("distanceMeters")),
        "description": route.get("description", ""),
    }


def route_plan(query):
    if not GOOGLE_API_KEY:
        origin_query, destination_query, requested_mode = split_route_query(query)
        transit = _transit_plan(origin_query, destination_query, requested_mode)
        if transit:
            return transit
        return [{"title": "Route unavailable", "summary": "GOOGLE_API_KEY is missing."}]

    origin_query, destination_query, requested_mode = split_route_query(query)

    transit = _transit_plan(origin_query, destination_query, requested_mode)
    if transit:
        return transit

    try:
        origin = resolve_place(origin_query)
        destination = resolve_place(destination_query)
        if not origin or not destination:
            return [{"title": "Route unavailable", "origin": origin_query, "destination": destination_query, "summary": "Could not resolve the origin or destination clearly."}]

        main_mode = "DRIVE" if requested_mode == "DRIVE" else "WALK"
        main_route = compute_route(origin, destination, main_mode)
        alt_mode = "WALK" if main_mode == "DRIVE" else "DRIVE"
        alt_route = None
        try:
            alt_route = compute_route(origin, destination, alt_mode)
        except Exception:
            alt_route = None
    except Exception as e:
        return [{"title": "Route unavailable", "origin": origin_query, "destination": destination_query, "summary": f"Route lookup failed: {e}"}]

    if main_mode == "DRIVE":
        title = "Least-sweat route"
        recommended = "Uber / Karwa taxi / car"
        summary = "Use a car/taxi for this one. Walking is the backup, not the smart move in the heat."
    else:
        title = "Walking route"
        recommended = "Walk"
        summary = "Walking route calculated. If the heat is bad or the distance feels annoying, use the driving map option instead."

    result = {
        "title": title,
        "origin": origin["title"],
        "destination": destination["title"],
        "origin_address": origin["address"],
        "destination_address": destination["address"],
        "recommended_mode": recommended,
        "travel_mode": main_mode,
        "distance": main_route.get("distance", "") if main_route else "",
        "duration": main_route.get("duration", "") if main_route else "",
        "summary": summary,
        "maps_url": _maps_url(origin["title"], destination["title"], main_mode),
    }
    if alt_route:
        result["alternate_distance"] = f"{alt_mode}: {alt_route.get('distance', '')}"
        result["alternate_duration"] = f"{alt_mode}: {alt_route.get('duration', '')}"
    return [result]


if __name__ == "__main__":
    tests = [
        "Matar Qadeem Family Food Centre to Ras Abu Aboud by public transport",
        "Al Wakra to Al Rayyan Al Qadeem by public transport",
        "Al Shaqab to Lusail Marina by public transport",
        "Oqba Ibn Nafie to HIA T1 by public transport",
    ]
    for test in tests:
        print("\nQUERY:", test)
        for result in route_plan(test):
            print(result)
