from fanar_client import ask_fanar_timed
from chat_session import (
    build_prompt,
    append_turn,
    get_turn_index,
    reset_history,
    make_tool_label,
    append_tool_result,
    append_router_decision,
    load_history,
)
from search_client import web_search
from places_client import place_search
from route_client import route_plan
from web_scraper_client import web_scrape
from calendar_client import calendar_event
from time_task_client import time_task
from location_resolver_client import resolve_location_tool
from router import build_router_prompt, parse_router_response
from rules.local_rules import (
    improve_web_query,
    improve_place_query,
    improve_route_query,
    improve_web_scrape_query,
    improve_calendar_query,
    improve_time_task_query,
    improve_location_resolver_query,
    apply_local_router_rules,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
import os
import time

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
        append_tool_result("web_search", label, query, results)
        return results, label, f"web_search:{label}"

    if tool == "place_lookup":
        label = make_tool_label("place_lookup")
        results = _tag_results(place_search(query), "place_lookup")
        append_tool_result("place_lookup", label, query, results)
        return results, label, f"place_lookup:{label}"

    if tool == "route_plan":
        label = make_tool_label("route_plan")
        results = _tag_results(route_plan(query), "route_plan")
        append_tool_result("route_plan", label, query, results)
        return results, label, f"route_plan:{label}"

    if tool == "web_scrape":
        label = make_tool_label("web_scrape")
        results = _tag_results(web_scrape(query), "web_scrape")
        append_tool_result("web_scrape", label, query, results)
        return results, label, f"web_scrape:{label}"

    if tool == "calendar_event":
        label = make_tool_label("calendar_event")
        results = _tag_results(calendar_event(query), "calendar_event")
        append_tool_result("calendar_event", label, query, results)
        return results, label, f"calendar_event:{label}"

    if tool == "time_task":
        label = make_tool_label("time_task")
        results = _tag_results(time_task(query), "time_task")
        append_tool_result("time_task", label, query, results)
        return results, label, f"time_task:{label}"

    if tool == "location_resolver":
        label = make_tool_label("location_resolver")
        results = _tag_results(resolve_location_tool(query), "location_resolver")
        append_tool_result("location_resolver", label, query, results)
        return results, label, f"location_resolver:{label}"

    return [], None, "no_tool"


def run_tools(router_data, user_prompt, history=""):
    tools = router_data.get("tools", [])
    queries = router_data.get("queries", {})

    all_results = []
    labels = []
    notes = []

    if not tools:
        return [], None, "no_tool"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for tool in tools:
            query = queries.get(tool, "")
            if tool == "web_search":
                query = improve_web_query(query, user_prompt, history)
            elif tool == "place_lookup":
                query = improve_place_query(query, user_prompt, history)
            elif tool == "route_plan":
                query = improve_route_query(query, user_prompt, history)
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

    active_labels = ",".join(labels) if labels else None
    return all_results, active_labels, ";".join(notes)


def _first_result(tool_results, tool):
    for result in tool_results or []:
        if result.get("source_tool") == tool:
            return result
    return None


def _results_for(tool_results, tool):
    return [r for r in (tool_results or []) if r.get("source_tool") == tool]


def compose_destination_access_answer(tool_results):
    """Deterministically combine navigation + place verification + web context.

    This is for prompts like: "get me to X, is it there?". The route tool
    should not drown out the place/web tools, and Fanar should not be asked to
    invent the merge under demo pressure.
    """
    route = _first_result(tool_results, "route_plan")
    place = _first_result(tool_results, "place_lookup")
    web_items = _results_for(tool_results, "web_search")

    parts = []

    if place:
        title = place.get("title", "the destination")
        address = place.get("address", "")
        maps_url = place.get("maps_url", "")
        line = f"Destination check: {title}"
        if address:
            line += f" — {address}"
        parts.append(line + ".")
        if maps_url:
            parts.append(f"Place map: {maps_url}")

    if route:
        answer = route.get("final_answer") or route.get("summary")
        if answer:
            parts.append(answer.strip())
        elif route.get("maps_url"):
            parts.append(f"Navigation backup: {route.get('maps_url')}")

    if web_items:
        top = web_items[0]
        if top.get("title") or top.get("link"):
            text = "Web check: " + top.get("title", "relevant source")
            if top.get("link"):
                text += f" — {top.get('link')}"
            parts.append(text)

    if parts:
        parts.append("Use the Maps link/signage for the exact exit and walking path; use the web/source link only as a verification backup.")
        return "\n".join(parts).strip()

    return None


def direct_answer_from_results(tool_results, router_data=None):
    """Bypass Fanar for fragile deterministic outputs.

    Conservative rule:
    - if multiple tools ran for destination/access verification, compose them.
    - if exactly one tool ran and it returned final_answer, print it directly.
    - otherwise let Fanar combine the evidence.
    """
    tools = (router_data or {}).get("tools", [])
    reason = (router_data or {}).get("reason", "")

    if reason == "local_destination_access_rule":
        composed = compose_destination_access_answer(tool_results)
        if composed:
            return composed

    if len(tools) != 1:
        return None

    for result in tool_results or []:
        answer = result.get("final_answer")
        if answer:
            return answer.strip()
    return None


if __name__ == "__main__":
    router_model = os.getenv("FANAR_ROUTER_MODEL", "Fanar")
    responder_model = os.getenv("FANAR_RESPONDER_MODEL", "Fanar-C-2-27B")

    reset_history()

    print("Qaarib agentic backend started.")
    print("Type q, quit, or exit to stop.\n")

    while True:
        user_prompt = input("prompt:\t")

        if user_prompt.lower().strip() in {"q", "quit", "exit"}:
            break

        session_turn = get_turn_index()
        router_ms = 0
        tool_ms = 0
        responder_ms = 0

        try:
            history_before_turn = load_history()

            router_prompt = build_router_prompt(user_prompt, history_before_turn)
            router_raw, router_ms = ask_fanar_timed(router_prompt, router_model, max_tokens=350)

            router_data = parse_router_response(router_raw)
            router_data = apply_local_router_rules(user_prompt, history_before_turn, router_data)

            append_router_decision(router_data)

            print("\nROUTER:")
            print(router_data)
            print("router_ms:", router_ms)

            # Direct policy answers are for no-tool corrections/identity/no-op cases.
            # They must not accidentally revive the previous place/route context.
            policy_answer = router_data.get("direct_answer")
            if policy_answer:
                tool_results = []
                active_tool_label = None
                tool_ms = 0
                response = str(policy_answer).strip()
                responder_ms = 0
                print("tool_ms:", tool_ms)
            else:
                tool_start = time.perf_counter()
                tool_results, active_tool_label, tool_notes = run_tools(router_data, user_prompt, history_before_turn)
                tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
                print("tool_ms:", tool_ms)

                deterministic = direct_answer_from_results(tool_results, router_data)
                if deterministic:
                    response = deterministic
                    responder_ms = 0
                else:
                    sent_prompt = build_prompt(user_prompt, tool_results=tool_results, active_tool_label=active_tool_label)
                    response, responder_ms = ask_fanar_timed(sent_prompt, responder_model, max_tokens=900)

            print("responder_ms:", responder_ms)
            print("\nResponse:\n")
            print(response)

            append_turn(user_prompt, response)

        except Exception as e:
            print("\nError:\n")
            print(str(e))
