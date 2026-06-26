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
from router import build_router_prompt, parse_router_response
from rules.local_rules import (
    improve_web_query,
    improve_place_query,
    improve_route_query,
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


def run_one_tool(tool, query):
    if tool == "web_search":
        label = make_tool_label("web_search")
        results = web_search(query)
        append_tool_result("web_search", label, query, results)
        return results, label, f"web_search:{label}"

    if tool == "place_lookup":
        label = make_tool_label("place_lookup")
        results = place_search(query)
        append_tool_result("place_lookup", label, query, results)
        return results, label, f"place_lookup:{label}"

    if tool == "route_plan":
        label = make_tool_label("route_plan")
        results = route_plan(query)
        append_tool_result("route_plan", label, query, results)
        return results, label, f"route_plan:{label}"

    return [], None, "no_tool"


def run_tools(router_data, user_prompt, history=""):
    tools = router_data.get("tools", [])
    queries = router_data.get("queries", {})

    all_results = []
    labels = []
    notes = []

    if not tools:
        return [], None, "no_tool"

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []

        for tool in tools:
            query = queries.get(tool, "")

            # Deterministic polish after the model router.
            # This keeps query quality stable without touching chat memory.
            if tool == "web_search":
                query = improve_web_query(query, user_prompt, history)
            elif tool == "place_lookup":
                query = improve_place_query(query, user_prompt, history)
            elif tool == "route_plan":
                query = improve_route_query(query, user_prompt, history)

            futures.append(executor.submit(run_one_tool, tool, query))

        for future in as_completed(futures):
            results, label, note = future.result()
            all_results.extend(results)
            if label:
                labels.append(label)
            notes.append(note)

    active_labels = ",".join(labels) if labels else None
    return all_results, active_labels, ";".join(notes)


if __name__ == "__main__":
    router_model = os.getenv("FANAR_ROUTER_MODEL", "Fanar")
    responder_model = os.getenv("FANAR_RESPONDER_MODEL", "Fanar-C-2-27B")

    # This is chat-session memory, not evaluation logging.
    # Keep this if you want every CLI run to start fresh.
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
            router_raw, router_ms = ask_fanar_timed(
                router_prompt,
                router_model,
                max_tokens=350,
            )

            router_data = parse_router_response(router_raw)
            router_data = apply_local_router_rules(
                user_prompt,
                history_before_turn,
                router_data,
            )

            # Keep router decisions in chat_session.md for continuity/debugging.
            # This is separate from CSV evaluation logging.
            append_router_decision(router_data)

            print("\nROUTER:")
            print(router_data)
            print("router_ms:", router_ms)

            tool_start = time.perf_counter()
            tool_results, active_tool_label, tool_notes = run_tools(
                router_data,
                user_prompt,
                history_before_turn,
            )
            tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
            print("tool_ms:", tool_ms)

            sent_prompt = build_prompt(
                user_prompt,
                tool_results=tool_results,
                active_tool_label=active_tool_label,
            )

            response, responder_ms = ask_fanar_timed(
                sent_prompt,
                responder_model,
                max_tokens=900,
            )

            print("responder_ms:", responder_ms)
            print("\nResponse:\n")
            print(response)

            # Keep actual conversational memory.
            append_turn(user_prompt, response)

        except Exception as e:
            print("\nError:\n")
            print(str(e))