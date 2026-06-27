import os
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

import qaarib_side_panel as panel


def clear():
    os.system("clear" if os.name != "nt" else "cls")


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


def ask_scenario(default="airport"):
    names = list(panel.SCENARIOS.keys())
    print("Scenarios:")
    for i, name in enumerate(names, 1):
        marker = "*" if name == default else " "
        print(f"  {i}. {name} {marker}")
    raw = input(f"Scenario [{default}]: ").strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(names):
        return names[int(raw) - 1]
    if raw in panel.SCENARIOS:
        return raw
    print("Invalid scenario, using default.")
    return default


def open_html(interval, loop, start_at_ms):
    html = Path(__file__).resolve().parent / "fallback_demo.html"
    query = urlencode({
        "interval": str(interval),
        "loop": "1" if loop else "0",
        "startAt": str(start_at_ms),
    })
    webbrowser.open(html.as_uri() + "?" + query, new=2)
    return html


def wait_until(start_at_ms):
    while True:
        remaining = (start_at_ms - int(time.time() * 1000)) / 1000
        if remaining <= 0:
            print(" " * 50, end="\r")
            return
        print(f"sync start in {remaining:0.1f}s...", end="\r")
        time.sleep(0.1)


def main():
    clear()
    print("Qaarib synchronized run setup")
    print("This opens the browser view and terminal trace on the same timer.\n")

    scenario = ask_scenario("airport")
    interval = ask_float("Interval in seconds", 7.0)
    loop = ask_bool("Loop browser and terminal trace", False)

    print("\nPrepare the Fanar/Qaarib landing screen now.")
    print("When you have cleared it and are ready to descend into the chat UI, press Enter here.")
    input("Final start signal: ")

    clear()
    start_at_ms = int(time.time() * 1000) + 3000
    html = open_html(interval, loop, start_at_ms)

    print("Qaarib runtime trace")
    print(f"scenario={scenario} interval={interval}s loop={loop} mode=synchronized-run")
    print(f"view={html.name}")
    print("-" * 88)

    wait_until(start_at_ms)
    panel.stream_events(panel.SCENARIOS[scenario], interval, loop)


if __name__ == "__main__":
    main()
