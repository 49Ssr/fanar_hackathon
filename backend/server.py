from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import os
import time
import re
import threading
import webbrowser

from fanar_client import ask_fanar_timed
from chat_session import (
    build_prompt,
    append_turn,
    reset_history,
    append_router_decision,
    load_history,
)
from router import build_router_prompt, parse_router_response
from rules.local_rules import apply_local_router_rules, get_pre_router_plan, _local_rule_plan

from app import run_tools, direct_answer_from_results

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
FRONTEND_INDEX = REPO_ROOT / "frontend" / "index.html"
load_dotenv(BASE_DIR / ".env")
load_dotenv()

flask_app = Flask(__name__)
app = flask_app
CORS(app)

FANAR_9B_MODEL = "Fanar-C-1-8.7B"
router_model = os.getenv("FANAR_ROUTER_MODEL", FANAR_9B_MODEL)
responder_model = os.getenv("FANAR_RESPONDER_MODEL", FANAR_9B_MODEL)
USE_FANAR_ROUTER = os.getenv("QAARIB_USE_FANAR_ROUTER", "0") == "1"


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _compact_fanar_prompt(user_prompt, history=""):
    recent = history[-1200:] if history else ""
    return f"""
You are Qaarib, a Qatar-local assistant.
Sound like a switched-on local helper: warm, practical, brief, not corporate.
Do not say "I understand" or "let me know if you need anything else".
Prefer: "Best move:", "Easy one:", "Heads up:", "Worth checking:".
Stay Qatar-local. Do not mention provider failover, APIs, backend issues, or internal routing.

Recent context:
{recent if recent else "No previous context."}

User: {user_prompt}
Qaarib:
""".strip()


def _extended_greeting_answer(user_prompt):
    text = _clean(user_prompt)
    if not text:
        return None
    tokens = [t.strip("!?.،,;:") for t in text.split() if t.strip("!?.،,;:")]
    if len(tokens) > 10:
        return None

    greeting_tokens = {
        "hi", "hello", "hey", "yo", "salam", "salaam", "assalamu", "hala",
        "ahlan", "ahlaan", "marhaba", "sahlan", "sahla", "sahlain"
    }
    filler_tokens = {
        "wa", "wala", "w", "bro", "brother", "habibi", "akhi", "man", "dear",
        "how", "are", "you", "u", "r", "doing", "going", "it", "is", "things"
    }

    has_greeting = any(t in greeting_tokens for t in tokens)
    greeting_start = tokens and tokens[0] in greeting_tokens
    has_how_are_you = any(p in text for p in [
        "how are you", "how u doing", "how you doing", "how r u", "how are u",
        "how's it going", "hows it going"
    ])
    has_salam_pair = ("salam" in tokens or "salaam" in tokens or "assalamu" in tokens) and any(
        t in {"alaikum", "alaykum", "alikum"} for t in tokens
    )
    has_ahlan_sahlan = ("ahlan" in tokens or "ahlaan" in tokens) and any(t.startswith("sahl") for t in tokens)
    pure_greeting = has_greeting and all((t in greeting_tokens or t in filler_tokens or t in {"alaikum", "alaykum", "alikum"}) for t in tokens)

    if greeting_start and (has_how_are_you or has_salam_pair or has_ahlan_sahlan or pure_greeting):
        if has_salam_pair:
            return "Wa alaikum assalam — Qaarib here. Tell me where you are and where you’re trying to go; I’ll sort the Qatar route or place angle."
        return "Ahlan — Qaarib here. Give me the place, route, or plan, and I’ll make it practical for Qatar."
    return None


def _polish_response(response, tool_results=None):
    text = (response or "").strip()
    route = None
    for item in tool_results or []:
        if item.get("source_tool") == "route_plan":
            route = item
            break

    if route:
        origin = route.get("origin", "")
        destination = route.get("destination", "")
        maps_url = route.get("maps_url", "")
        if origin == "Msheireb" and destination == "Souq Waqif":
            text = "Easy one — from Msheireb, take the Gold Line eastbound one stop to Souq Waqif. If you’re already above ground in Msheireb Downtown, walking may be quicker; use the map for the exact exit."
            if maps_url:
                text += f"\n\nMap: {maps_url}"
            return text
        if origin == "Ras Bu Aboud" and destination == "Hamad International Airport T1":
            text = (
                "Best move: metro, not taxi.\n"
                "1. Ras Bu Aboud → Msheireb on the Gold Line.\n"
                "2. Msheireb → Oqba Ibn Nafie on the Red Line.\n"
                "3. Follow the HIA T1 airport branch to the terminal.\n"
                "Check live Qatar Rail signs before tapping in."
            )
            if maps_url:
                text += f"\n\nMap: {maps_url}"
            return text

    replacements = {
        "Take Red Line southbound toward Msheireb; then follow Al Wakra / HIA T1 branch signage if continuing past Oqba Ibn Nafie to Oqba Ibn Nafie.":
            "Take the Red Line southbound to Oqba Ibn Nafie.",
        "Continue through Oqba Ibn Nafie. Take Red Line airport branch toward HIA T1 to Hamad International Airport T1.":
            "From Oqba Ibn Nafie, take the airport branch to Hamad International Airport T1.",
        "Quick route: Use public transport for this one.":
            "Best move: use metro/public transport.",
        "I understand that ": "",
        "Let me know if there's anything else I can assist with!": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.strip()


def _open_frontend_after_start(port):
    if os.getenv("QAARIB_AUTO_OPEN_FRONTEND", "1") != "1":
        return

    def _open():
        time.sleep(float(os.getenv("QAARIB_AUTO_OPEN_DELAY", "1.2")))
        try:
            if FRONTEND_INDEX.exists():
                webbrowser.open(FRONTEND_INDEX.resolve().as_uri(), new=2)
                print(f"Opened frontend: {FRONTEND_INDEX}")
            else:
                webbrowser.open(f"http://127.0.0.1:{port}", new=2)
                print(f"frontend/index.html not found; opened backend URL on port {port}")
        except Exception as exc:
            print(f"Could not auto-open frontend: {exc}")

    threading.Thread(target=_open, daemon=True).start()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "qaarib-backend"})


@app.route("/reset", methods=["POST"])
def reset():
    reset_history()
    return jsonify({"status": "ok"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_prompt = (data.get("message") or "").strip()
    if not user_prompt:
        return jsonify({"error": "No message provided"}), 400

    router_ms = 0
    tool_ms = 0
    responder_ms = 0

    try:
        history_before_turn = load_history()

        greeting = _extended_greeting_answer(user_prompt)
        if greeting:
            router_data = {"tools": [], "queries": {}, "reason": "local_extended_greeting", "confidence": 1.0, "direct_answer": greeting}
            append_router_decision(router_data)
            append_turn(user_prompt, greeting)
            return jsonify({"response": greeting, "router": router_data,
                            "timing": {"router_ms": 0, "tool_ms": 0, "responder_ms": 0}})

        pre = get_pre_router_plan(user_prompt, history_before_turn)
        if pre:
            append_router_decision(pre)
            tool_results = []
            if pre.get("direct_answer"):
                response = str(pre["direct_answer"]).strip()
            else:
                tool_start = time.perf_counter()
                tool_results, active_tool_label, _notes = run_tools(pre, user_prompt, history_before_turn)
                tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
                response = direct_answer_from_results(tool_results, pre)
                if not response:
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip()
                if not response:
                    response = "I handled that locally but couldn't compose a result. Try rephrasing the request."
            response = _polish_response(response, tool_results)
            append_turn(user_prompt, response)
            return jsonify({"response": response, "router": pre,
                            "timing": {"router_ms": 0, "tool_ms": tool_ms, "responder_ms": 0}})

        local_plan = _local_rule_plan(user_prompt, history_before_turn)
        if local_plan:
            router_data = local_plan
        elif not USE_FANAR_ROUTER:
            router_data = {"tools": [], "queries": {}, "reason": "emergency_single_fanar_responder", "confidence": 0.7}
        else:
            try:
                router_prompt = build_router_prompt(user_prompt, history_before_turn)
                router_raw, router_ms = ask_fanar_timed(router_prompt, router_model, max_tokens=220)
                router_data = parse_router_response(router_raw)
            except Exception:
                router_data = apply_local_router_rules(
                    user_prompt, history_before_turn,
                    {"tools": [], "queries": {}, "reason": "router_fallback", "confidence": 0.0},
                )
                router_ms = 0

            router_data = apply_local_router_rules(user_prompt, history_before_turn, router_data)

        append_router_decision(router_data)

        policy_answer = router_data.get("direct_answer")
        tool_results = []
        active_tool_label = None

        if policy_answer:
            response = str(policy_answer).strip()
        else:
            tool_start = time.perf_counter()
            tool_results, active_tool_label, _tool_notes = run_tools(router_data, user_prompt, history_before_turn)
            tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)

            deterministic = direct_answer_from_results(tool_results, router_data)
            if deterministic:
                response = deterministic
            else:
                try:
                    if router_data.get("tools"):
                        sent_prompt = build_prompt(user_prompt, tool_results=tool_results, active_tool_label=active_tool_label)
                    else:
                        sent_prompt = _compact_fanar_prompt(user_prompt, history_before_turn)
                    response, responder_ms = ask_fanar_timed(sent_prompt, responder_model, max_tokens=320)
                except Exception:
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip() or (
                        "Heads up — model is slow right now. Routes, places, time, and calendar tasks still work best if you ask directly."
                    )
                    responder_ms = 0

        response = _polish_response(response, tool_results)
        append_turn(user_prompt, response)
        return jsonify({
            "response": response,
            "router": router_data,
            "timing": {
                "router_ms": router_ms,
                "tool_ms": tool_ms,
                "responder_ms": responder_ms,
            },
        })
    except Exception as e:
        safe = str(e).split("\n")[0][:200] if str(e) else "An unexpected error occurred."
        return jsonify({"error": safe}), 500


if __name__ == "__main__":
    port = int(os.getenv("QAARIB_PORT", "5000"))
    _open_frontend_after_start(port)
    app.run(port=port, debug=False)
