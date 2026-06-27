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

SCENARIOS = {
    "airport": [
        ("REQUEST", "route intent: Ras Bu Aboud -> HIA T1, avoid taxi", CYAN, 0.20),
        ("STATE", "history window loaded; last user turn preserved", BLUE, 0.18),
        ("RULE", "route keywords matched; public-transport preference detected", MAGENTA, 0.28),
        ("ROUTER", "local route path selected; model router not required", YELLOW, 0.22),
        ("MODEL", "Fanar reserved for wording only if tool answer is incomplete", YELLOW, 0.25),
        ("TOOL", "route_plan(origin=Ras Bu Aboud, destination=HIA T1)", GREEN, 0.55),
        ("MATCH", "alias: ras abu aboud -> Ras Bu Aboud", GREEN, 0.20),
        ("MATCH", "alias: hia t1 -> Hamad International Airport T1", GREEN, 0.18),
        ("GRAPH", "path: Gold Line -> Msheireb -> Red Line -> airport branch", GREEN, 0.70),
        ("FORMAT", "route steps normalized for frontend response", MAGENTA, 0.24),
        ("UI", "route cards + map backup attached", CYAN, 0.26),
        ("DONE", "response ready", GREEN, 0.15),
    ],
    "qatar_services": [
        ("REQUEST", "local recommendation intent detected", CYAN, 0.20),
        ("STATE", "recent Qatar context loaded", BLUE, 0.16),
        ("RULE", "place lookup and web lookup candidates selected", MAGENTA, 0.30),
        ("ROUTER", "tool route selected directly", YELLOW, 0.18),
        ("TOOL", "place_search(region=QA)", GREEN, 0.55),
        ("TOOL", "web_search(Qatar-scoped query)", GREEN, 0.65),
        ("RANK", "results filtered for Qatar relevance and actionability", GREEN, 0.35),
        ("UI", "place cards prepared", CYAN, 0.25),
        ("DONE", "response ready", GREEN, 0.15),
    ],
    "generic": [
        ("REQUEST", "open-ended user prompt received", CYAN, 0.20),
        ("STATE", "history compressed for prompt window", BLUE, 0.28),
        ("RULE", "no confident tool path", MAGENTA, 0.25),
        ("ROUTER", "single compact model call selected", YELLOW, 0.18),
        ("MODEL", "Fanar request sent", YELLOW, 0.85),
        ("MODEL", "Fanar response received", GREEN, 0.75),
        ("FORMAT", "response checked for user-facing clarity", MAGENTA, 0.22),
        ("DONE", "response ready", GREEN, 0.15),
    ],
    "resilience": [
        ("REQUEST", "user request received during high API load", CYAN, 0.20),
        ("STATE", "local session and tool state available", BLUE, 0.18),
        ("RULE", "deterministic tool coverage checked first", MAGENTA, 0.26),
        ("MODEL", "large model path avoided for latency control", YELLOW, 0.25),
        ("MODEL", "compact Fanar request attempted", YELLOW, 0.75),
        ("TOOL", "local tool output retained as fallback answer source", GREEN, 0.45),
        ("UI", "high-load note available for frontend", CYAN, 0.22),
        ("DONE", "response ready", GREEN, 0.15),
    ],
}

COLORS = {
    "REQUEST": CYAN,
    "STATE": BLUE,
    "RULE": MAGENTA,
    "ROUTER": YELLOW,
    "MODEL": YELLOW,
    "TOOL": GREEN,
    "MATCH": GREEN,
    "GRAPH": GREEN,
    "FORMAT": MAGENTA,
    "UI": CYAN,
    "RANK": GREEN,
    "DONE": GREEN,
}


def now():
    return datetime.now().strftime("%H:%M:%S")


def ask_float(prompt, default):
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return max(0.5, float(raw))
    except ValueError:
        print("Invalid number, using default.")
        return default


def ask_bool(prompt, default):
    default_text = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true", "on"}


def choose_scenario(default="airport"):
    names = list(SCENARIOS.keys())
    print("\nScenarios:")
    for i, name in enumerate(names, 1):
        marker = "*" if name == default else " "
        print(f"  {i}. {name} {marker}")
    raw = input(f"Scenario [{default}]: ").strip()
    if not raw:
        return default
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(names):
            return names[idx]
    if raw in SCENARIOS:
        return raw
    print("Invalid scenario, using default.")
    return default


def interactive_config(default_scenario, default_interval, default_loop):
    os.system("clear" if os.name != "nt" else "cls")
    print(f"{BOLD}Qaarib runtime trace setup{RESET}")
    print(f"{DIM}Press Enter to accept defaults. Ctrl+C cancels.\n{RESET}")
    scenario = choose_scenario(default_scenario)
    interval = ask_float("Maximum step time in seconds", default_interval)
    loop = ask_bool("Loop trace", default_loop)
    input("\nPress Enter to start...")
    os.system("clear" if os.name != "nt" else "cls")
    return scenario, interval, loop


def line(stage, message, color, duration):
    elapsed_ms = max(8, int(duration * 1000 + random.randint(-60, 80)))
    return f"{DIM}{now()}{RESET} {color}{stage:<8}{RESET} {message} {DIM}{elapsed_ms}ms{RESET}"


def banner(scenario, interval, loop):
    print(f"{BOLD}Qaarib runtime trace{RESET}")
    print(f"{DIM}scenario={scenario} max_step={interval}s loop={loop} mode=presentation-runtime{RESET}")
    print("-" * 88)
    sys.stdout.flush()


def stream_events(events, max_interval, loop):
    source = itertools.cycle(events) if loop else iter(events)
    for stage, message, color, factor in source:
        duration = max(0.15, max_interval * factor)
        print(line(stage, message, color or COLORS.get(stage, RESET), duration))
        sys.stdout.flush()
        time.sleep(duration)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="airport")
    parser.add_argument("--interval", type=float, default=7.0)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--no-loop", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--no-menu", action="store_true")
    args = parser.parse_args()

    global RESET, DIM, BOLD, CYAN, GREEN, YELLOW, MAGENTA, BLUE
    if args.no_color:
        RESET = DIM = BOLD = CYAN = GREEN = YELLOW = MAGENTA = BLUE = ""

    scenario = args.scenario
    interval = max(0.5, args.interval)
    loop = args.loop and not args.no_loop

    if not args.no_menu:
        scenario, interval, loop = interactive_config(scenario, interval, loop)

    banner(scenario, interval, loop)
    stream_events(SCENARIOS[scenario], interval, loop)


if __name__ == "__main__":
    main()
