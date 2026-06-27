from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv

from chat_session import make_tool_label, append_tool_result
from search_client import web_search
from places_client import place_search
from route_client import route_plan
from route_context_guard import repair_route_query
from web_scraper_client import web_scrape
from calendar_client import calendar_event
from time_task_client import time_task
from location_resolver_client import resolve_location_tool
from rules.local_rules import (
    improve_web_query,
    improve_place_query,
    improve_route_query,
    improve_web_scrape_query,
    improve_calendar_query,
    improve_time_task_query,
    improve_location_resolver_query,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _tag_results(results, tool):
    tagged = []
    for result in results or []:
        if isinstance(result, dict):
            item = dict(result)
            item["source_tool"] = tool
            tagged.append(item)
    return tagged


def run_one_tool(tool, query):
    if tool == "web_search":
        label = make_tool_label("web_search")
        results = _tag_results(web_search(query), "web_search")
    elif tool == "place_lookup":
        label = make_tool_label("place_lookup")
        results = _tag_results(place_search(query), "place_lookup")
    elif tool == "route_plan":
        label = make_tool_label("route_plan")
        results = _tag_results(route_plan(query), "route_plan")
    elif tool == "web_scrape":
        label = make_tool_label("web_scrape")
        results = _tag_results(web_scrape(query), "web_scrape")
    elif tool == "calendar_event":
        label = make_tool_label("calendar_event")
        results = _tag_results(calendar_event(query), "calendar_event")
    elif tool == "time_task":
        label = make_tool_label("time_task")
        results = _tag_results(time_task(query), "time_task")
    elif tool == "location_resolver":
        label = make_tool_label("location_resolver")
        results = _tag_results(resolve_location_tool(query), "location_resolver")
    else:
        return [], None, "no_tool"

    append_tool_result(tool, label, query, results)
    return results, label, f"{tool}:{label}"


def run_tools(router_data, user_prompt, history=""):
    tools = router_data.get("tools", [])
    queries = router_data.get("queries", {})
    if not tools:
        return [], None, "no_tool"

    all_results = []
    labels = []
    notes = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for tool in tools:
            query = queries.get(tool, "")
            if tool == "web_search":
                query = improve_web_query(query, user_prompt, history)
            elif tool == "place_lookup":
                query = improve_place_query(query, user_prompt, history)
            elif tool == "route_plan":
                query = repair_route_query(improve_route_query(query, user_prompt, history), user_prompt, history)
            elif tool == "web_scrape":
                query = improve_web_scrape_query(query, user_prompt, history)
            elif tool == "calendar_event":
                query = improve_calendar_query(query, user_prompt, history)
            elif tool == "time_task":
                query = improve_time_task_query(query, user_prompt, history)
            elif tool == "location_resolver":
                query = improve_location_resolver_query(query, user_prompt, history)
            futures.append(executor.submit(run_one_tool, tool, query))

        for future in as_completed(futures):
            results, label, note = future.result()
            all_results.extend(results)
            if label:
                labels.append(label)
            notes.append(note)

    return all_results, ",".join(labels) if labels else None, ";".join(notes)


def _first_result(tool_results, tool):
    for result in tool_results or []:
        if result.get("source_tool") == tool:
            return result
    return None


def _results_for(tool_results, tool):
    return [r for r in (tool_results or []) if r.get("source_tool") == tool]


def _route_text(route):
    origin = route.get("origin", "")
    dest = route.get("destination", "")
    text = (route.get("final_answer") or route.get("summary") or "").strip()
    if not text:
        mode = route.get("recommended_mode") or route.get("travel_mode") or "route"
        text = f"Best move: {mode} from {origin} to {dest}."
    swaps = {
        "Quick route: Use public transport for this one.": "Best move: use metro/public transport.",
        "Cheapest route: use metro/public transport instead of taxis.": "Best move: use metro/public transport instead of taxi.",
        "Check live Qatar Rail / tram timings and platform signs before you tap in, but the network path is this.": "Check live Qatar Rail/tram signs before tapping in.",
    }
    for old, new in swaps.items():
        text = text.replace(old, new)
    return text.strip()


def compose_destination_access_answer(tool_results):
    route = _first_result(tool_results, "route_plan")
    place = _first_result(tool_results, "place_lookup")
    web_items = _results_for(tool_results, "web_search")
    parts = []

    if place:
        title = place.get("title", "the destination")
        address = place.get("address", "")
        maps_url = place.get("maps_url", "")
        line = f"Place check: {title}"
        if address:
            line += f" — {address}"
        parts.append(line + ".")
        if maps_url:
            parts.append(f"Place map: {maps_url}")

    if route:
        answer = _route_text(route)
        if answer:
            parts.append(answer)

    if web_items:
        top = web_items[0]
        if top.get("title") or top.get("link"):
            text = "Source check: " + top.get("title", "relevant source")
            if top.get("link"):
                text += f" — {top.get('link')}"
            parts.append(text)

    if parts:
        parts.append("Use the map/signage for the exact exit and walking path.")
        return "\n".join(parts).strip()
    return None


def direct_answer_from_results(tool_results, router_data=None):
    tools = (router_data or {}).get("tools", [])
    reason = (router_data or {}).get("reason", "")

    if reason == "local_destination_access_rule":
        composed = compose_destination_access_answer(tool_results)
        if composed:
            return composed

    if len(tools) != 1:
        return None

    for result in tool_results or []:
        if result.get("source_tool") == "route_plan":
            return _route_text(result)
        answer = result.get("final_answer")
        if answer:
            return answer.strip()
    return None
