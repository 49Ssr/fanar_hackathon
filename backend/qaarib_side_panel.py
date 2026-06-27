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
        ("INPUT", "received user prompt: route from Ras Bu Aboud to HIA T1 while minimising taxi spend", CYAN),
        ("SESSION", "loaded short-term context and recent route state", BLUE),
        ("GUARD", "local rules checked: greeting=false, time=false, calendar=false, route=true", MAGENTA),
        ("ROUTER", "Fanar router bypassed: emergency single-call mode active", YELLOW),
        ("PLAN", "selected tool route_plan with transit preference", GREEN),
        ("ALIAS", "normalised Ras Abu/Ras Bu Aboud -> Ras Bu Aboud station", GREEN),
        ("ALIAS", "normalised HIA T1 -> Hamad International Airport T1", GREEN),
        ("GRAPH", "computed metro path: Gold Line -> Msheireb -> Red Line -> Airport branch", GREEN),
        ("TOOL", "route_plan returned deterministic transit answer", GREEN),
        ("FORMAT", "cleaned repeated transfer wording for judge-facing response", MAGENTA),
        ("WIDGET", "frontend route/widget layer can render transit guidance", CYAN),
        ("OUTPUT", "response delivered with maps backup and live-timing disclaimer", GREEN),
    ],
    "places": [
        ("INPUT", "received user prompt: find Qatar-local place recommendation", CYAN),
        ("SESSION", "loaded recent chat context", BLUE),
        ("GUARD", "local rules checked: place_lookup intent detected", MAGENTA),
        ("ROUTER", "Fanar router skipped because local planner is confident", YELLOW),
        ("PLAN", "selected place_lookup with Qatar-scoped query", GREEN),
        ("TOOL", "Google Places request sent with regionCode=QA", GREEN),
        ("TOOL", "place candidates returned and ranked", GREEN),
        ("FORMAT", "compressed results into user-facing recommendation", MAGENTA),
        ("WIDGET", "frontend card/widget payload available", CYAN),
        ("OUTPUT", "response delivered without waiting for a second model call", GREEN),
    ],
    "generic": [
        ("INPUT", "received open-ended user prompt", CYAN),
        ("SESSION", "trimmed conversation context for compact prompt", BLUE),
        ("GUARD", "no deterministic tool path found", MAGENTA),
        ("ROUTER", "Fanar router bypassed to avoid double latency", YELLOW),
        ("MODEL", "using Fanar-C-1-8.7B fallback model", YELLOW),
        ("CALL", "single compact responder request sent", CYAN),
        ("MODEL", "response received from Fanar", GREEN),
        ("SAFETY", "removed backend/internal failure wording", MAGENTA),
        ("OUTPUT", "concise Qaarib answer delivered to chat UI", GREEN),
    ],
    "fallback": [
        ("INPUT", "received user prompt during high server load", CYAN),
        ("SESSION", "context loaded from local history", BLUE),
        ("GUARD", "local tools checked before model call", MAGENTA),
        ("MODEL", "primary Fanar request exceeded safe latency window", RED),
        ("RECOVERY", "fallback model selected: Fanar-C-1-8.7B", YELLOW),
        ("RECOVERY", "response simplified to preserve demo stability", YELLOW),
        ("UI", "frontend should show high-load disclaimer below answer", CYAN),
        ("OUTPUT", "graceful degraded response delivered instead of blank failure", GREEN),
    ],
}

PREFIXES = {
    "INPUT": CYAN,
    "SESSION": BLUE,
    "GUARD": MAGENTA,
    "ROUTER": YELLOW,
    "PLAN": GREEN,
    "ALIAS": GREEN,
    "GRAPH": GREEN,
    "TOOL": GREEN,
    "FORMAT": MAGENTA,
    "WIDGET": CYAN,
    "OUTPUT": GREEN,
    "MODEL": YELLOW,
    "CALL": CYAN,
    "SAFETY": MAGENTA,
    "RECOVERY": YELLOW,
    "UI": CYAN,
}


def now():
    return datetime.now().strftime("%H:%M:%S")


def line(stage, message, color):
    latency = random.randint(12, 480)
    pid = os.getpid()
    return f"{DIM}{now()}{RESET} {color}{stage:<8}{RESET} {message} {DIM}pid={pid} latency={latency}ms{RESET}"


def banner(scenario, interval):
    print(f"{BOLD}Qaarib runtime trace{RESET}")
    print(f"{DIM}scenario={scenario} interval={interval}s mode=side-panel{RESET}")
    print("-" * 72)
    sys.stdout.flush()


def stream_events(events, interval, loop):
    source = itertools.cycle(events) if loop else iter(events)
    for stage, message, color in source:
        print(line(stage, message, color or PREFIXES.get(stage, RESET)))
        sys.stdout.flush()
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="airport")
    parser.add_argument("--interval", type=float, default=5.0)
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
