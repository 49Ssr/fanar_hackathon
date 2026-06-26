import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH=Path(__file__).resolve().parent/".env"
load_dotenv(ENV_PATH)
load_dotenv()

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

LOCATION_BIAS={
    "msheireb downtown":(25.2869,51.5321,1400),
    "downtown doha":(25.2869,51.5321,1600),
    "downtown":(25.2869,51.5321,1600),
    "msheireb metro":(25.2869,51.5321,1400),
    "msheireb":(25.2869,51.5321,1600),
    "souq waqif":(25.2887,51.5330,1600),
    "mansoura":(25.2736,51.5370,1800),
    "al mansoura":(25.2736,51.5370,1800),
    "west bay":(25.3267,51.5313,2200),
    "the pearl":(25.3718,51.5504,2200),
    "lusail":(25.4075,51.5150,2800),
    "qcri":(25.3168,51.4385,1800),
    "education city":(25.3176,51.4387,2500),
    "education city metro":(25.3172,51.4343,1800),
    "minaretein":(25.3106,51.4395,1800),
    "banana island":(25.2860,51.6410,2600),
    "anantara":(25.2860,51.6410,2600),
    "museum of islamic art":(25.2958,51.5392,1800),
    "mia park":(25.2958,51.5392,1800),
    "katara":(25.3600,51.5260,2200),
    "the pearl":(25.3718,51.5504,2200),
    "corniche":(25.3000,51.5350,2600),
    "national museum":(25.2867,51.5493,1800),
}

SOCIAL_DOMAINS=("instagram.com","tiktok.com","facebook.com")

QATAR_BOUNDS={"min_lat":24.3,"max_lat":26.3,"min_lng":50.6,"max_lng":52.1}

def _in_qatar_bounds(lat,lng):
    try:
        lat=float(lat); lng=float(lng)
    except Exception:
        return False
    return (QATAR_BOUNDS["min_lat"] <= lat <= QATAR_BOUNDS["max_lat"] and QATAR_BOUNDS["min_lng"] <= lng <= QATAR_BOUNDS["max_lng"])

def _qatar_address(address):
    a=(address or "").lower()
    return any(token in a for token in ["qatar","doha","lusail","wakra","al wakrah","msheireb","mansoura","west bay","pearl"] )


def _price_level(place):
    raw=place.get("priceLevel","")
    if not raw:
        return ""
    return str(raw).replace("PRICE_LEVEL_","").title()


def _location_bias_for(query):
    q=query.lower()
    for key,(lat,lng,radius) in sorted(LOCATION_BIAS.items(),key=lambda kv: len(kv[0]),reverse=True):
        if key in q:
            return {"circle":{"center":{"latitude":lat,"longitude":lng},"radius":radius}}
    return None


def _is_budget_query(query):
    q=query.lower()
    return any(word in q for word in ["budget","cheap","cheaper","affordable","low cost","inexpensive"])


def _is_cafe_query(query):
    q=query.lower()
    return any(word in q for word in ["qahwa","gahwa","arabic coffee","coffee","karak","cafe","café","dates"])


def _is_nightlife_query(query):
    q=query.lower()
    return any(word in q for word in ["nightlife","night life","bar","pub","club","nightclub","drink","drinks","party","lounge","alcohol","beer","wine"])


def _is_photo_query(query):
    q=query.lower()
    return any(word in q for word in ["photo", "photos", "photography", "pictures", "pics", "shots", "cinematic", "scenic", "viewpoint", "viewpoints", "landmark", "landmarks"])


def _is_resort_query(query):
    q=query.lower()
    return any(word in q for word in ["anantara", "anatara", "banana island", "resort", "staycation"] )


def _is_general_food_query(query):
    q=query.lower()
    return any(word in q for word in [
        "restaurant", "restaurants", "food", "eat", "eating", "hungry", "meal",
        "lunch", "dinner", "breakfast", "takeout", "takeaway", "outside",
        "feeling lucky", "feelin lucky", "feelin' lucky", "recommendation", "recommend"
    ]) and not _is_nightlife_query(query) and not _is_cafe_query(query)


def _force_qatar_scope(query):
    q=re.sub(r"\s+"," ",query).strip()
    # The CLI has no live GPS. "near me" must not become a global query.
    # Keep it Qatar-scoped and let the answer ask for the user's area if exact routing is needed.
    q=re.sub(r"\bnear me\b", "in Doha Qatar", q, flags=re.I)
    q=re.sub(r"\bfrom my location\b", "from Doha Qatar", q, flags=re.I)
    lower=q.lower()

    # "downtown" is dangerously ambiguous globally. In this app it means Doha/Msheireb.
    if "downtown" in lower and "doha" not in lower and "qatar" not in lower and "msheireb" not in lower:
        q=f"{q} near Msheireb Downtown Doha Qatar"

    if "mansoura" in lower and "doha" not in lower and "qatar" not in lower:
        q=f"{q} Al Mansoura Doha Qatar"

    # Qaarib is Qatar-scoped. Do not let bare generic queries wander to Charleston/Dubai/etc.
    if not any(token in lower for token in ["qatar","doha","msheireb","mansoura","wakra","lusail","education city","west bay","the pearl","souq waqif"]):
        q=f"{q} Doha Qatar"

    if "anatara" in q.lower() and "anantara" not in q.lower():
        q=q.replace("anatara", "Anantara")

    if _is_nightlife_query(q) and "licensed" not in q.lower():
        q=f"licensed hotel {q}"

    return q


def _extract_location_tail(query):
    q=_force_qatar_scope(query)
    lower=q.lower()
    for key in sorted(LOCATION_BIAS,key=len,reverse=True):
        if key in lower:
            if key == "downtown":
                return "Msheireb Downtown Doha, Qatar"
            return key.title().replace("Qcri","QCRI")+", Doha, Qatar"
    m=re.search(r"\bnear\b(.+)",q,flags=re.I)
    if m:
        return m.group(1).strip(" ,.")
    return "Doha, Qatar"


def _fallback_queries(query):
    q=_force_qatar_scope(query)
    location=_extract_location_tail(q)
    queries=[q]
    lower=q.lower()

    if _is_resort_query(q):
        queries.append("Banana Island Resort Doha by Anantara Qatar")
        queries.append("Anantara Banana Island Doha Qatar")

    if _is_photo_query(q):
        queries.append(f"scenic landmarks photography spots near {location}")
        queries.append(f"tourist attractions viewpoints near {location}")
        queries.append("Museum of Islamic Art Park Corniche Katara The Pearl Msheireb Doha Qatar")

    if _is_nightlife_query(q):
        queries.append(f"licensed hotel bar lounge near {location}")
        queries.append(f"nightlife lounge near {location}")
        queries.append(f"hotel bar near {location}")

    if _is_general_food_query(q):
        queries.append(f"popular highly rated restaurant near {location}")
        queries.append(f"restaurant near {location}")
        queries.append("popular restaurants in Doha Qatar")

    if "qahwa" in lower or "gahwa" in lower or "dates" in lower:
        queries.append(f"Arabic coffee cafe near {location}")
        queries.append(f"traditional Arabic coffee near {location}")
        queries.append(f"cafe near {location}")

    if _is_budget_query(q):
        queries.insert(0,f"affordable cafe near {location}")

    seen=set()
    clean=[]
    for item in queries:
        key=item.lower()
        if key not in seen:
            seen.add(key)
            clean.append(item)
    return clean


def _included_type_for(query):
    # For nightlife, do NOT force includedType=cafe. Let Places return bars/nightclubs/hotel lounges.
    if _is_nightlife_query(query):
        return None
    if _is_cafe_query(query):
        return "cafe"
    if _is_general_food_query(query):
        return "restaurant"
    return None


def _post_text_search(query,num_results=4,price_filter=False):
    url="https://places.googleapis.com/v1/places:searchText"
    headers={
        "Content-Type":"application/json",
        "X-Goog-Api-Key":GOOGLE_API_KEY,
        "X-Goog-FieldMask":(
            "places.displayName,places.formattedAddress,places.location,"
            "places.googleMapsUri,places.rating,places.userRatingCount,"
            "places.priceLevel,places.types,places.websiteUri,places.businessStatus"
        ),
    }
    body={
        "textQuery":_force_qatar_scope(query),
        "pageSize":max(1,min(int(num_results),20)),
        "regionCode":"QA",
        "languageCode":"en",
    }
    bias=_location_bias_for(body["textQuery"])
    if bias:
        body["locationBias"]=bias
    included_type=_included_type_for(body["textQuery"])
    if included_type:
        body["includedType"]=included_type
    if price_filter:
        body["priceLevels"]=["PRICE_LEVEL_INEXPENSIVE","PRICE_LEVEL_MODERATE"]

    response=requests.post(url,headers=headers,json=body,timeout=10)
    if not response.ok:
        print("Places lookup failed:",response.status_code,response.text[:500])
        return []
    return response.json().get("places",[])


def _place_final_answer(query, places):
    if not places:
        return ""
    q=query.lower()
    is_nightlife=_is_nightlife_query(query)
    is_photo=_is_photo_query(query)
    is_resort=_is_resort_query(query)
    is_food=_is_general_food_query(query)
    is_qahwa=("qahwa" in q or "gahwa" in q or "arabic coffee" in q or "dates" in q or "karak" in q)
    is_budget=_is_budget_query(query)
    if not (is_nightlife or is_qahwa or is_budget or is_photo or is_resort or is_food):
        return ""

    if is_nightlife:
        lines=["Best move: keep it to licensed hotel bars/lounges in Doha. These are Qatar-scoped Maps hits, not random global nightlife results:"]
    elif is_food:
        lines=["Best move: since you said you’re feeling lucky, I’ll pick a Qatar-scoped food option instead of giving generic global results:"]
    elif is_photo:
        lines=["Best move: for strong Qatar photo spots, start with these Qatar-scoped Maps hits:"]
    elif is_resort:
        lines=["Best move: for Anantara/Banana Island, check the resort directly and treat summer as a heat-aware staycation/beach-resort plan. Qatar-scoped Maps hit:"]
    elif is_budget:
        lines=["Best move: start with the options that have a lower/moderate price signal. Price is not guaranteed unless Maps shows it:"]
    else:
        lines=["Best nearby Maps hits:"]

    for i, place in enumerate(places[:3], start=1):
        bits=[f"{i}. {place.get('title','')}"]
        if place.get('rating'):
            bits.append(f"rating {place.get('rating')}")
        if place.get('price_level'):
            bits.append(f"price {place.get('price_level')}")
        if place.get('address'):
            bits.append(place.get('address'))
        line=" — ".join([b for b in bits if b])
        if place.get('maps_url'):
            line += f"\n   Map: {place.get('maps_url')}"
        lines.append(line)

    if is_nightlife:
        lines.append("Heads up: carry ID and check the venue rules/timing before heading out.")
    if is_photo:
        lines.append("Heads up: go near golden hour if you can; midday summer light/heat can be brutal.")
    if is_resort:
        lines.append("Heads up: in summer, judge it as an indoor/pool/beach-resort experience, not a long outdoor sightseeing day. Verify current offers, boat transfer timings, and day-pass/stay rules before going.")
    if is_food:
        lines.append("Guide: use the Maps link for navigation. For exact door-to-door routing, send your current area/station because this CLI does not have live GPS.")
    if is_qahwa:
        lines.append("Heads up: unless a place explicitly confirms qahwa/dates, treat these as nearby café/Arabic-coffee leads and verify before walking.")
    return "\n".join(lines)

def place_search(query,num_results=4):
    if not GOOGLE_API_KEY:
        print("GOOGLE KEY FOUND: False")
        return []

    raw_places=[]
    for q in _fallback_queries(query):
        if _is_budget_query(query):
            raw_places.extend(_post_text_search(q,num_results=num_results,price_filter=True))
        raw_places.extend(_post_text_search(q,num_results=num_results,price_filter=False))
        if len(raw_places)>=num_results:
            break

    places=[]
    seen=set()
    for place in raw_places:
        location=place.get("location",{})
        title=place.get("displayName",{}).get("text","").strip()
        address=place.get("formattedAddress","").strip()
        maps_url=place.get("googleMapsUri","").strip()
        website=place.get("websiteUri","").strip()
        if not title:
            continue

        # Hard Qatar scope. Coordinate bounds beat text. This stops global leakage
        # like Charleston/Dubai when the query says vague words such as "downtown".
        lat=location.get("latitude","")
        lng=location.get("longitude","")
        if not (_in_qatar_bounds(lat,lng) or _qatar_address(address)):
            continue

        if any(domain in website.lower() for domain in SOCIAL_DOMAINS):
            website=""

        dedupe_key=(title.lower(),address.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        places.append({
            "title":title,
            "address":address,
            "lat":location.get("latitude",""),
            "lng":location.get("longitude",""),
            "maps_url":maps_url,
            "rating":place.get("rating",""),
            "user_rating_count":place.get("userRatingCount",""),
            "price_level":_price_level(place),
            "types":" | ".join(place.get("types",[])[:6]),
            "website":website,
        })
        if len(places)>=num_results:
            break
    final_answer=_place_final_answer(query, places)
    if final_answer and places:
        places[0]["final_answer"]=final_answer

    return places


if __name__=="__main__":
    tests=[
        "nightlife spots downtown",
        "licensed hotel bar nightlife near Msheireb Downtown Doha Qatar",
        "qahwa dates cafe near Msheireb Metro Station, Doha, Qatar",
    ]
    for test in tests:
        print("\nQUERY:",test)
        results=place_search(test)
        print("Places found:",len(results))
        for result in results:
            print("PLACE:",result["title"],"|",result["address"],"|",result.get("rating",""),"|",result.get("price_level",""))
