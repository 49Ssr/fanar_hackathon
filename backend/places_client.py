import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH=Path(__file__).resolve().parent/".env"
load_dotenv(ENV_PATH)
load_dotenv()

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

# Coordinates are only used as a bias, not as fake exact positions.
# They stop Google from wandering into random Doha/Qatar results when the user
# clearly gave a local area.
LOCATION_BIAS={
    "msheireb metro":(25.2869,51.5321,1400),
    "msheireb":(25.2869,51.5321,1600),
    "souq waqif":(25.2887,51.5330,1600),
    "qcri":(25.3168,51.4385,1800),
    "education city":(25.3176,51.4387,2500),
    "education city metro":(25.3172,51.4343,1800),
    "minaretein":(25.3106,51.4395,1800),
}

SOCIAL_DOMAINS=("instagram.com","tiktok.com","facebook.com")


def _price_level(place):
    raw=place.get("priceLevel","")
    if not raw:
        return ""
    return str(raw).replace("PRICE_LEVEL_","").title()


def _location_bias_for(query):
    q=query.lower()
    for key,(lat,lng,radius) in sorted(LOCATION_BIAS.items(),key=lambda kv: len(kv[0]),reverse=True):
        if key in q:
            return {
                "circle":{
                    "center":{"latitude":lat,"longitude":lng},
                    "radius":radius,
                }
            }
    return None


def _is_budget_query(query):
    q=query.lower()
    return any(word in q for word in ["budget","cheap","cheaper","affordable","low cost","inexpensive"])


def _is_cafe_query(query):
    q=query.lower()
    return any(word in q for word in ["qahwa","gahwa","arabic coffee","coffee","karak","cafe","café","dates"])


def _extract_location_tail(query):
    """Best-effort location extraction for fallback queries."""
    q=re.sub(r"\s+"," ",query).strip()

    # Prefer known phrases over clever NLP.
    lower=q.lower()
    for key in sorted(LOCATION_BIAS,key=len,reverse=True):
        if key in lower:
            if "metro" in key:
                return key.title().replace("Qcri","QCRI")+", Doha, Qatar"
            return key.title().replace("Qcri","QCRI")+", Doha, Qatar"

    # Last resort: text after "near".
    m=re.search(r"\bnear\b(.+)",q,flags=re.I)
    if m:
        return m.group(1).strip(" ,.")

    return "Doha, Qatar"


def _fallback_queries(query):
    """Try the user's precise query first, then less brittle cafe queries.

    Google Places Text Search is not great with 'qahwa dates' as a phrase.
    For Maps, 'Arabic coffee cafe near X' is usually more productive.
    """
    location=_extract_location_tail(query)
    q=query.strip()
    queries=[q]

    lower=q.lower()
    if "qahwa" in lower or "gahwa" in lower or "dates" in lower:
        queries.append(f"Arabic coffee cafe near {location}")
        queries.append(f"traditional Arabic coffee near {location}")
        queries.append(f"cafe near {location}")

    if _is_budget_query(q):
        queries.insert(0,f"affordable cafe near {location}")

    # Deduplicate while preserving order.
    seen=set()
    clean=[]
    for item in queries:
        key=item.lower()
        if key not in seen:
            seen.add(key)
            clean.append(item)
    return clean


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
        "textQuery":query,
        "pageSize":max(1,min(int(num_results),20)),
        # Text Search (New) uses regionCode, not includedRegionCodes.
        # includedRegionCodes causes HTTP 400 on the New endpoint.
        "regionCode":"QA",
        "languageCode":"en",
    }

    bias=_location_bias_for(query)
    if bias:
        body["locationBias"]=bias

    if _is_cafe_query(query):
        body["includedType"]="cafe"

    if price_filter:
        body["priceLevels"]=["PRICE_LEVEL_INEXPENSIVE","PRICE_LEVEL_MODERATE"]

    response=requests.post(url,headers=headers,json=body,timeout=10)

    if not response.ok:
        # Print the useful Google error body, but never print the API key.
        print("Places lookup failed:",response.status_code,response.text[:500])
        return []

    return response.json().get("places",[])


# Google Places API New.
# This is for place/location lookup, not general web search.
def place_search(query,num_results=4):
    if not GOOGLE_API_KEY:
        print("GOOGLE KEY FOUND: False")
        return []

    raw_places=[]

    # If user asked for cheap/budget, try price-filtered first, then normal fallback.
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

        # Strong guardrail: if Google somehow returns outside Qatar, do not let it poison the answer.
        address_l=address.lower()
        if address and not any(token in address_l for token in ["qatar","doha","qa"]):
            continue

        # Social pages are not place records. Keep actual Maps URL, but avoid surfacing social as website proof.
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
            "types":" | ".join(place.get("types",[])[:5]),
            "website":website,
        })

        if len(places)>=num_results:
            break

    return places


if __name__=="__main__":
    tests=[
        "qahwa dates cafe near Msheireb Metro Station, Doha, Qatar",
        "affordable cafe qahwa dates near Msheireb Metro Station, Doha, Qatar",
    ]
    for test in tests:
        print("\nQUERY:",test)
        results=place_search(test)
        print("Places found:",len(results))
        for result in results:
            print("PLACE:",result["title"],"|",result["address"],"|",result.get("rating",""),"|",result.get("price_level",""))
