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
USE_FANAR_ROUTER = os.getenv("QAARIB_USE_FANAR_ROUTER", "0") == "1"


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _compact_fanar_prompt(user_prompt, history=""):
    # Keep this tiny. During server load, huge system/history prompts are killing latency.
    recent = ""
    if history:
        recent = history[-1200:]
    return f"""
You are Qaarib, a Qatar-focused assistant for the Fanar Hackathon.
Be concise, helpful, and practical. Default to English. Do not mention backend/tool failures.
For Qatar questions, stay Qatar-local. If unsure, say what to check next.

Recent context:
{recent if recent else "No previous context."}

User: {user_prompt}
Qaarib:
""".strip()


def _extended_greeting_answer(user_prompt):
    """Catch natural greetings like 'ahlan wa sahlan' or 'salam bro'."""
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
            return "Wa alaikum assalam — I’m Qaarib, ready for Qatar routes, places, events, and quick local help."
        return "Ahlan wa sahlan — I’m Qaarib, ready for Qatar routes, places, events, and quick local help."
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
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip()
                if not response:
                    response = "I handled that locally but couldn't compose a result. Try rephrasing the request."
            append_turn(user_prompt, response)
            return jsonify({"response": response, "router": pre,
                            "timing": {"router_ms": 0, "tool_ms": tool_ms, "responder_ms": 0}})

        local_plan = _local_rule_plan(user_prompt, history_before_turn)
        if local_plan:
            router_data = local_plan
        elif not USE_FANAR_ROUTER:
            # Emergency mode: skip Fanar-as-router. One Fanar call is already risky;
            # two calls is what caused the UI to hang/fallback under load.
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
                        "I’m under heavy load right now, but I can still help fastest with routes, places, time, and calendar tasks. Try a direct Qatar-local request."
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
        safe = str(e).split("\n")[0][:200] if str(e) else "An unexpected error occurred."
        return jsonify({"error": safe}), 500


if __name__ == "__main__":
    app.run(port=int(os.getenv("QAARIB_PORT", "5000")), debug=False)
