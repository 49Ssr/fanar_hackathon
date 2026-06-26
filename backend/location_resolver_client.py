from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _load_run():
    try:
        from agents.location.location_resolver_agent import run
        return run, None
    except Exception as e:
        return None, str(e)


def resolve_location_tool(query, num_results=1):
    run, err = _load_run()
    if not run:
        return [{
            "title": "Location resolver unavailable",
            "summary": f"Location resolver import failed: {err}",
            "final_answer": f"Location resolver is unavailable: {err}",
        }]
    try:
        result = run(query, context={"default_country":"Qatar"})
    except Exception as e:
        return [{
            "title": "Location resolver failed",
            "summary": str(e),
            "final_answer": f"I couldn't resolve that location cleanly: {e}",
        }]

    data = result.get("data", {}) if isinstance(result, dict) else {}
    if result.get("status") == "ok":
        name = data.get("location") or data.get("normalized_name") or query
        display = data.get("display_name") or data.get("query") or ""
        lat = data.get("lat", "")
        lng = data.get("lng", "")
        source = data.get("source", "")
        parts = [f"Resolved location: {name}."]
        if display:
            parts.append(f"Map/geocoder display: {display}.")
        if lat and lng:
            parts.append(f"Coordinates: {lat}, {lng}.")
        if source:
            parts.append(f"Source: {source}.")
        final = "\n".join(parts)
        return [{
            "title": "Resolved location",
            "location": name,
            "display_name": display,
            "lat": lat,
            "lng": lng,
            "confidence": data.get("confidence", ""),
            "source": source,
            "summary": final,
            "final_answer": final,
        }]

    err_msg = result.get("error") or "unresolved"
    return [{
        "title": "Location unresolved",
        "query": query,
        "summary": err_msg,
        "final_answer": f"I couldn't resolve '{query}' confidently inside Qatar. Try a more specific landmark or area name.",
    }]


if __name__ == "__main__":
    import sys, json
    q = " ".join(sys.argv[1:]) or "QCRI"
    print(json.dumps(resolve_location_tool(q), ensure_ascii=False, indent=2))
