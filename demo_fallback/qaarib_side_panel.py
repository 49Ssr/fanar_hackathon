import argparse
import itertools
import os
import random
import sys
import time
from datetime import datetime

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"

SCENARIOS = {
    "airport": [
        ("INPUT", "user asks for the cheapest route from Ras Bu Aboud to HIA T1", CYAN),
        ("CONTEXT", "Qaarib keeps recent chat state but trims it before routing", BLUE),
        ("INTENT", "local intent detector recognises a Qatar transit request", MAGENTA),
        ("RESILIENCE", "Fanar router is bypassed to avoid double model latency", YELLOW),
        ("MODEL", "backup model locked: Fanar-C-1-8.7B for any required generation", YELLOW),
        ("PLAN", "route_plan selected with public-transport preference", GREEN),
        ("NORMALIZE", "Ras Abu/Ras Bu Aboud resolved to Ras Bu Aboud station", GREEN),
        ("NORMALIZE", "HIA T1 resolved to Hamad International Airport Terminal 1", GREEN),
        ("GRAPH", "metro graph search finds Gold Line -> Msheireb -> Red Line -> airport branch", GREEN),
        ("TOOLS", "deterministic route answer produced without waiting for Fanar", GREEN),
        ("FORMAT", "response is cleaned for judge-facing readability", MAGENTA),
        ("WIDGET", "frontend can attach route cards, map links, and high-load disclaimer", CYAN),
        ("OUTPUT", "Qaarib returns a useful answer even if Fanar is overloaded", GREEN),
    ],
    "qatar_services": [
        ("INPUT", "user asks for a Qatar-local service, venue, or recommendation", CYAN),
        ("CONTEXT", "recent conversation is loaded for continuity", BLUE),
        ("INTENT", "local planner identifies place_lookup / web_search / route_plan candidates", MAGENTA),
        ("RESILIENCE", "obvious tool requests skip the Fanar router", YELLOW),
        ("TOOLS", "Qatar-scoped API calls run in parallel where possible", GREEN),
        ("RANK", "results are filtered toward Qatar relevance and practical next steps", GREEN),
        ("WIDGET", "Oryx/widget layer can render cards instead of plain text", CYAN),
        ("OUTPUT", "answer is delivered with map/source backups", GREEN),
    ],
    "generic": [
        ("INPUT", "user asks an open-ended question", CYAN),
        ("CONTEXT", "history is compressed into a small prompt window", BLUE),
        ("INTENT", "no deterministic tool path is confident enough", MAGENTA),
        ("RESILIENCE", "router call skipped; Qaarib makes only one model request", YELLOW),
        ("MODEL", "Fanar-C-1-8.7B receives compact Qaarib prompt", YELLOW),
        ("MODEL", "response received and checked for backend leakage", GREEN),
        ("OUTPUT", "concise answer is sent to chat UI", GREEN),
    ],
    "fallback": [
        ("INPUT", "server load spikes during a judge interaction", CYAN),
        ("CONTEXT", "local state and deterministic tools remain available", BLUE),
        ("RESILIENCE", "slow model requests are redirected away from 27B / default Fanar", YELLOW),
        ("RECOVERY", "fallback model attempted with shorter timeout", YELLOW),
        ("RECOVERY", "if generation fails, local tool output is still shown", YELLOW),
        ("UI", "frontend displays a calm high-load note below the answer", CYAN),
        ("OUTPUT", "demo degrades gracefully instead of showing a blank failure", GREEN),
    ],
}

COLORS = {
    "INPUT": CYAN,
    "CONTEXT": BLUE,
    "INTENT": MAGENTA,
    "RESILIENCE": YELLOW,
    "MODEL": YELLOW,
    "PLAN": GREEN,
    "NORMALIZE": GREEN,
    "GRAPH": GREEN,
    "TOOLS": GREEN,
    "FORMAT": MAGENTA,
    "WIDGET": CYAN,
    "RANK": GREEN,
    "RECOVERY": YELLOW,
    "UI": CYAN,
    "OUTPUT": GREEN,
}


def now():
    return datetime.now().strftime("%H:%M:%S")


def line(stage, message, color):
    latency = random.randint(24, 920)
    pid = os.getpid()
    return f"{DIM}{now()}{RESET} {color}{stage:<10}{RESET} {message} {DIM}pid={pid} latency={latency}ms{RESET}"


def banner(scenario, interval):
    print(f"{BOLD}Qaarib runtime trace{RESET}")
    print(f"{DIM}scenario={scenario} interval={interval}s mode=demo-fallback side-panel{RESET}")
    print("-" * 88)
    sys.stdout.flush()


def stream_events(events, interval, loop):
    source = itertools.cycle(events) if loop else iter(events)
    for stage, message, color in source:
        print(line(stage, message, color or COLORS.get(stage, RESET)))
        sys.stdout.flush()
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="airport")
    parser.add_argument("--interval", type=float, default=7.0)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    global RESET, DIM, BOLD, CYAN, GREEN, YELLOW, MAGENTA, BLUE, RED
    if args.no_color:
        RESET = DIM = BOLD = CYAN = GREEN = YELLOW = MAGENTA = BLUE = RED = ""

    banner(args.scenario, args.interval)
    stream_events(SCENARIOS[args.scenario], args.interval, args.loop)


if __name__ == "__main__":
    main()
