from fanar_client import ask_fanar_timed
from chat_session import (
    build_prompt,append_turn,get_turn_index,reset_history,make_tool_label,
    append_tool_result,append_router_decision,load_history
)
from search_client import web_search
from places_client import place_search
from route_client import route_plan
from router import build_router_prompt,parse_router_response
from rules.local_rules import (
    improve_web_query,improve_place_query,improve_route_query,
    apply_local_router_rules
)
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import csv
import os
import time

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")
load_dotenv()

RESULTS_PATH=BASE_DIR.parent/"evaluation"/"results.csv"


def log_result(session_turn,router_model,responder_model,user_prompt,router_data,router_ms,tool_ms,responder_ms,response,status="ok",notes=""):
    RESULTS_PATH.parent.mkdir(parents=True,exist_ok=True)
    file_exists=RESULTS_PATH.exists()

    with open(RESULTS_PATH,"a",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp","session_turn","router_model","responder_model",
                "user_prompt","router_tools","router_queries","router_confidence",
                "router_ms","tool_ms","responder_ms","response","status","notes"
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            session_turn,
            router_model,
            responder_model,
            user_prompt,
            "|".join(router_data.get("tools",[])),
            str(router_data.get("queries",{})),
            router_data.get("confidence",0.0),
            router_ms,
            tool_ms,
            responder_ms,
            response,
            status,
            notes,
        ])


def run_one_tool(tool,query):
    if tool=="web_search":
        label=make_tool_label("web_search")
        results=web_search(query)
        append_tool_result("web_search",label,query,results)
        return results,label,f"web_search:{label}"

    if tool=="place_lookup":
        label=make_tool_label("place_lookup")
        results=place_search(query)
        append_tool_result("place_lookup",label,query,results)
        return results,label,f"place_lookup:{label}"

    if tool=="route_plan":
        label=make_tool_label("route_plan")
        results=route_plan(query)
        append_tool_result("route_plan",label,query,results)
        return results,label,f"route_plan:{label}"

    return [],None,"no_tool"


def run_tools(router_data,user_prompt,history=""):
    tools=router_data.get("tools",[])
    queries=router_data.get("queries",{})

    all_results=[]
    labels=[]
    notes=[]

    if not tools:
        return [],None,"no_tool"

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures=[]

        for tool in tools:
            query=queries.get(tool,"")

            # Deterministic polish after the model router.
            if tool=="web_search":
                query=improve_web_query(query,user_prompt,history)
            elif tool=="place_lookup":
                query=improve_place_query(query,user_prompt,history)
            elif tool=="route_plan":
                query=improve_route_query(query,user_prompt,history)

            futures.append(executor.submit(run_one_tool,tool,query))

        for future in as_completed(futures):
            results,label,note=future.result()
            all_results.extend(results)
            if label:
                labels.append(label)
            notes.append(note)

    active_labels=",".join(labels) if labels else None
    return all_results,active_labels,";".join(notes)


if __name__=="__main__":
    router_model=os.getenv("FANAR_ROUTER_MODEL","Fanar")
    responder_model=os.getenv("FANAR_RESPONDER_MODEL","Fanar-C-2-27B")

    reset_history()

    print("Qaarib agentic backend started.")
    print("Type q, quit, or exit to stop.\n")

    while True:
        user_prompt=input("prompt:\t")

        if user_prompt.lower().strip() in {"q","quit","exit"}:
            break

        session_turn=get_turn_index()
        router_ms=0
        tool_ms=0
        responder_ms=0
        response=""
        notes=""

        try:
            history_before_turn=load_history()

            # First ask the model router, then force deterministic guardrails.
            router_prompt=build_router_prompt(user_prompt,history_before_turn)
            router_raw,router_ms=ask_fanar_timed(router_prompt,router_model,max_tokens=350)
            router_data=parse_router_response(router_raw)
            router_data=apply_local_router_rules(user_prompt,history_before_turn,router_data)

            append_router_decision(router_data)

            print("\nROUTER:")
            print(router_data)
            print("router_ms:",router_ms)

            tool_start=time.perf_counter()
            tool_results,active_tool_label,notes=run_tools(router_data,user_prompt,history_before_turn)
            tool_ms=round((time.perf_counter()-tool_start)*1000,2)
            print("tool_ms:",tool_ms)

            sent_prompt=build_prompt(
                user_prompt,
                tool_results=tool_results,
                active_tool_label=active_tool_label,
            )

            response,responder_ms=ask_fanar_timed(sent_prompt,responder_model,max_tokens=900)

            print("responder_ms:",responder_ms)
            print("\nResponse:\n")
            print(response)

            append_turn(user_prompt,response)

            log_result(
                session_turn,router_model,responder_model,user_prompt,router_data,
                router_ms,tool_ms,responder_ms,response,"ok",notes
            )

        except Exception as e:
            error_msg=str(e)
            print("\nError:\n")
            print(error_msg)

            log_result(
                session_turn,router_model,responder_model,user_prompt,
                {"tools":["error"],"queries":{},"confidence":0.0},
                router_ms,tool_ms,responder_ms,response,"error",error_msg
            )
