from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import os
import time

from fanar_client import ask_fanar_timed
from chat_session import (
    build_prompt,
    append_turn,
    reset_history,
    append_router_decision,
    load_history,
)
from router import build_router_prompt, parse_router_response
from rules.local_rules import apply_local_router_rules

# Reuse the CLI's real execution path instead of maintaining a divergent copy.
# app.py is safe to import: its CLI loop is under if __name__ == "__main__".
from app import run_tools, direct_answer_from_results

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()

flask_app = Flask(__name__)
app = flask_app  # keep the conventional name for Flask runners
CORS(app)

router_model = os.getenv("FANAR_ROUTER_MODEL", "Fanar")
responder_model = os.getenv("FANAR_RESPONDER_MODEL", "Fanar-C-2-27B")


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

        router_prompt = build_router_prompt(user_prompt, history_before_turn)
        router_raw, router_ms = ask_fanar_timed(router_prompt, router_model, max_tokens=350)
        router_data = parse_router_response(router_raw)
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
                sent_prompt = build_prompt(user_prompt, tool_results=tool_results, active_tool_label=active_tool_label)
                response, responder_ms = ask_fanar_timed(sent_prompt, responder_model, max_tokens=900)

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
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=int(os.getenv("QAARIB_PORT", "5000")), debug=False)
