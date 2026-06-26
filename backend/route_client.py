import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus

ENV_PATH=Path(__file__).resolve().parent/".env"
load_dotenv(ENV_PATH)
load_dotenv()

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

ALIASES={
    "qcri":"Qatar Computing Research Institute, Education City, Doha, Qatar",
    "qatar computing research institute":"Qatar Computing Research Institute, Education City, Doha, Qatar",
    "hbku qcri":"Qatar Computing Research Institute, Education City, Doha, Qatar",
    "minaretein":"Minaretein Center, Education City, Doha, Qatar",
    "minaretein center":"Minaretein Center, Education City, Doha, Qatar",
    "minaratein":"Minaretein Center, Education City, Doha, Qatar",
    "minareten":"Minaretein Center, Education City, Doha, Qatar",
    "education city mosque":"Education City Mosque, Education City, Doha, Qatar",
    "msheireb metro":"Msheireb Metro Station, Doha, Qatar",
    "msheireb metro station":"Msheireb Metro Station, Doha, Qatar",
    "education city metro":"Education City Metro Station, Doha, Qatar",
    "education city metro station":"Education City Metro Station, Doha, Qatar",
}


def canonical_place(text):
    cleaned=re.sub(r"\s+"," ",text.lower().strip())
    cleaned=cleaned.strip(" .")

    if cleaned in ALIASES:
        return ALIASES[cleaned]

    for key,value in sorted(ALIASES.items(),key=lambda kv: len(kv[0]),reverse=True):
        if key in cleaned:
            return value

    if "qatar" not in cleaned and "doha" not in cleaned:
        return f"{text.strip()}, Doha, Qatar"

    return text.strip()


def split_route_query(query):
    """Return origin, destination, preferred mode.

    mode is WALK, DRIVE, or AUTO. Uber/Karwa/taxi map to DRIVE because the
    Routes API cannot request a ride-hailing car directly.
    """
    q=re.sub(r"\s+"," ",query.strip())
    lower=q.lower()

    mode="AUTO"
    if any(word in lower for word in [" by car"," driving"," drive"," uber"," taxi"," karwa"," cab"]):
        mode="DRIVE"
    elif any(word in lower for word in [" walk"," walking"," on foot"]):
        mode="WALK"

    q=re.sub(r"\b(by car|by taxi|by uber|by karwa|driving|drive|walking|walk|on foot)\b","",q,flags=re.I).strip()

    if " to " in q.lower():
        origin,destination=re.split(r"\s+to\s+",q,maxsplit=1,flags=re.I)
        return canonical_place(origin),canonical_place(destination),mode

    return canonical_place(q),"Education City Metro Station, Doha, Qatar",mode


def resolve_place(query):
    url="https://places.googleapis.com/v1/places:searchText"

    headers={
        "Content-Type":"application/json",
        "X-Goog-Api-Key":GOOGLE_API_KEY,
        "X-Goog-FieldMask":"places.displayName,places.formattedAddress,places.location,places.googleMapsUri",
    }

    body={
        "textQuery":query,
        "pageSize":1,
        # Text Search (New) uses regionCode, not includedRegionCodes.
        "regionCode":"QA",
        "languageCode":"en",
    }

    response=requests.post(url,headers=headers,json=body,timeout=10)
    if not response.ok:
        print("Place resolve failed:",response.status_code,response.text[:500])
        response.raise_for_status()

    places=response.json().get("places",[])
    if not places:
        return None

    place=places[0]
    location=place.get("location",{})

    return {
        "title":place.get("displayName",{}).get("text",query),
        "address":place.get("formattedAddress",""),
        "lat":location.get("latitude"),
        "lng":location.get("longitude"),
        "maps_url":place.get("googleMapsUri",""),
    }


def seconds_to_minutes(duration_text):
    if not duration_text or not duration_text.endswith("s"):
        return ""
    seconds=int(float(duration_text[:-1]))
    minutes=max(1,round(seconds/60))
    return f"{minutes} min"


def meters_to_km(meters):
    if meters is None:
        return ""
    if meters<1000:
        return f"{int(meters)} m"
    return f"{meters/1000:.1f} km"


def compute_route(origin_place,destination_place,travel_mode):
    url="https://routes.googleapis.com/directions/v2:computeRoutes"

    headers={
        "Content-Type":"application/json",
        "X-Goog-Api-Key":GOOGLE_API_KEY,
        "X-Goog-FieldMask":"routes.duration,routes.distanceMeters,routes.description",
    }

    body={
        "origin":{
            "location":{
                "latLng":{
                    "latitude":origin_place["lat"],
                    "longitude":origin_place["lng"],
                }
            }
        },
        "destination":{
            "location":{
                "latLng":{
                    "latitude":destination_place["lat"],
                    "longitude":destination_place["lng"],
                }
            }
        },
        "travelMode":travel_mode,
        "languageCode":"en",
    }

    response=requests.post(url,headers=headers,json=body,timeout=10)
    if not response.ok:
        print("Route compute failed:",response.status_code,response.text[:500])
        response.raise_for_status()

    routes=response.json().get("routes",[])
    if not routes:
        return None

    route=routes[0]
    return {
        "duration":seconds_to_minutes(route.get("duration","")),
        "distance":meters_to_km(route.get("distanceMeters")),
        "description":route.get("description",""),
    }


def _maps_url(origin_title,destination_title,mode):
    travelmode="driving" if mode=="DRIVE" else "walking"
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin_title)}"
        f"&destination={quote_plus(destination_title)}"
        f"&travelmode={travelmode}"
    )


def route_plan(query):
    if not GOOGLE_API_KEY:
        return [{"title":"Route unavailable","summary":"GOOGLE_API_KEY is missing."}]

    origin_query,destination_query,requested_mode=split_route_query(query)

    try:
        origin=resolve_place(origin_query)
        destination=resolve_place(destination_query)

        if not origin or not destination:
            return [{
                "title":"Route unavailable",
                "origin":origin_query,
                "destination":destination_query,
                "summary":"Could not resolve the origin or destination clearly.",
            }]

        # AUTO defaults to walking for short station/cafe directions, but QCRI/Minaretein
        # and heat-aware queries are sent in as DRIVE by local_rules.
        main_mode="DRIVE" if requested_mode=="DRIVE" else "WALK"
        main_route=compute_route(origin,destination,main_mode)

        alt_mode="WALK" if main_mode=="DRIVE" else "DRIVE"
        alt_route=None
        try:
            alt_route=compute_route(origin,destination,alt_mode)
        except Exception:
            alt_route=None

    except Exception as e:
        return [{
            "title":"Route unavailable",
            "origin":origin_query,
            "destination":destination_query,
            "summary":f"Route lookup failed: {e}",
        }]

    if main_mode=="DRIVE":
        title="Least-sweat route"
        recommended="Uber / Karwa taxi / car"
        summary="Use a car/taxi for this one. Walking is the backup, not the smart move in the heat."
    else:
        title="Walking route"
        recommended="Walk"
        summary="Walking route calculated. If the heat is bad or the distance feels annoying, use the driving map option instead."

    result={
        "title":title,
        "origin":origin["title"],
        "destination":destination["title"],
        "origin_address":origin["address"],
        "destination_address":destination["address"],
        "recommended_mode":recommended,
        "travel_mode":main_mode,
        "distance":main_route.get("distance","") if main_route else "",
        "duration":main_route.get("duration","") if main_route else "",
        "summary":summary,
        "maps_url":_maps_url(origin["title"],destination["title"],main_mode),
    }

    if alt_route:
        result["alternate_distance"]=f"{alt_mode}: {alt_route.get('distance','')}"
        result["alternate_duration"]=f"{alt_mode}: {alt_route.get('duration','')}"

    return [result]


if __name__=="__main__":
    for result in route_plan("QCRI to Minaretein by car"):
        print(result)
