from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import os
import time
import re

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

# Reuse the CLI's real execution path instead of maintaining a divergent copy.
# app.py is safe to import: its CLI loop is under if __name__ == "__main__".
from app import run_tools, direct_answer_from_results

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

flask_app = Flask(__name__)
app = flask_app  # keep the conventional name for Flask runners
CORS(app)

# Hackathon load fallback: organisers recommended the ~9B model while Fanar is overloaded.
FANAR_9B_MODEL = "Fanar-C-1-8.7B"
router_model = os.getenv("FANAR_ROUTER_MODEL", FANAR_9B_MODEL)
responder_model = os.getenv("FANAR_RESPONDER_MODEL", FANAR_9B_MODEL)


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _extended_greeting_answer(user_prompt):
    """Catch natural greetings like 'salam alikum brother how u doing'.

    These are not worth a Fanar router call during the demo. Keep this narrow so
    real requests that happen to contain 'salam' still route normally.
    """
    text = _clean(user_prompt)
    if not text:
        return None
    tokens = [t.strip("!?.،,;:") for t in text.split()]
    if len(tokens) > 9:
        return None
    greeting_start = tokens[0] in {"hi", "hello", "hey", "yo", "salam", "salaam", "assalamu", "hala", "ahlan", "marhaba"}
    has_how_are_you = any(p in text for p in ["how are you", "how u doing", "how you doing", "how r u", "how are u", "how's it going", "hows it going"])
    has_salam_pair = ("salam" in tokens or "salaam" in tokens or "assalamu" in tokens) and any(t in {"alaikum", "alaykum", "alikum"} for t in tokens)
    if greeting_start and (has_how_are_you or has_salam_pair):
        return "Wa alaikum assalam — doing good. I’m Qaarib, ready for Qatar routes, places, events, and quick local help."
    return None


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

        # ── Pre-router deterministic direct/route plan ─────────────────────────
        # Greetings, identity, GPS, current time, calendar creation, and routes
        # between known Qatar locations are handled WITHOUT calling Fanar. This
        # is the reliability backbone: these never time out, even if Fanar is down.
        pre = get_pre_router_plan(user_prompt, history_before_turn)
        if pre:
            append_router_decision(pre)
            if pre.get("direct_answer"):
                response = str(pre["direct_answer"]).strip()
            else:
                tool_start = time.perf_counter()
                tool_results, active_tool_label, _notes = run_tools(pre, user_prompt, history_before_turn)
                tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
                response = direct_answer_from_results(tool_results, pre)
                if not response:
                    # Surface the first tool final_answer/summary deterministically.
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip()
                if not response:
                    response = "I handled that locally but couldn't compose a result. Try rephrasing the request."
            append_turn(user_prompt, response)
            return jsonify({"response": response, "router": pre,
                            "timing": {"router_ms": 0, "tool_ms": tool_ms, "responder_ms": 0}})

        # ── Local tool-intent router fast path ──────────────────────────────────
        # For obvious demo intents (places, food, nightlife, photo spots, resorts,
        # URL scrape, etc.) skip the Fanar router and only use Fanar once if we
        # need it to compose tool results. This removes the common 2-call latency.
        local_plan = _local_rule_plan(user_prompt, history_before_turn)
        if local_plan:
            router_data = local_plan
            router_ms = 0
        else:
            # ── Fanar router (open-ended / ambiguous intent) ───────────────────
            try:
                router_prompt = build_router_prompt(user_prompt, history_before_turn)
                router_raw, router_ms = ask_fanar_timed(router_prompt, router_model, max_tokens=300)
                router_data = parse_router_response(router_raw)
            except Exception:
                # Router timed out/failed: fall back to local rules with an empty plan
                # so transit/place rules can still fire deterministically.
                router_data = apply_local_router_rules(
                    user_prompt, history_before_turn,
                    {"tools": [], "queries": {}, "reason": "router_fallback", "confidence": 0.0},
                )
                router_ms = 0
                if not router_data.get("tools") and not router_data.get("direct_answer"):
                    fallback = ("Fanar is taking a moment right now. I can still help with specific local tasks: "
                                "metro routes, current time, calendar events, or named Qatar places. Please restate your request.")
                    append_turn(user_prompt, fallback)
                    return jsonify({"response": fallback, "timing": {"router_ms": router_ms, "tool_ms": 0, "responder_ms": 0}})

            router_data = apply_local_router_rules(user_prompt, history_before_turn, router_data)

        append_router_decision(router_data)

        policy_answer = router_data.get("direct_answer")
        tool_results = []
        active_tool_label = None

        if policy_answer:
            response = str(policy_answer).strip()
            tool_ms = 0
            responder_ms = 0
        else:
            tool_start = time.perf_counter()
            tool_results, active_tool_label, _tool_notes = run_tools(router_data, user_prompt, history_before_turn)
            tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)

            deterministic = direct_answer_from_results(tool_results, router_data)
            if deterministic:
                response = deterministic
                responder_ms = 0
            else:
                try:
                    sent_prompt = build_prompt(user_prompt, tool_results=tool_results, active_tool_label=active_tool_label)
                    response, responder_ms = ask_fanar_timed(sent_prompt, responder_model, max_tokens=500)
                except Exception:
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip() or (
                        "Fanar is taking a moment. For specific tasks like routes, time, or calendar events, try restating the request directly."
                    )
                    responder_ms = 0

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
        err_str = str(e)
        if "timed out" in err_str.lower() or "timeout" in err_str.lower() or "connectionpool" in err_str.lower():
            msg = "Fanar is taking a moment to respond. Try a more specific request or retry shortly."
            return jsonify({"error": msg}), 503
        # Strip raw Python exception internals before sending to frontend
        safe = err_str.split("\n")[0][:200] if err_str else "An unexpected error occurred."
        return jsonify({"error": safe}), 500


if __name__ == "__main__":
    app.run(port=int(os.getenv("QAARIB_PORT", "5000")), debug=False)
