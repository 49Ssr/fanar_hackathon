from flask import Flask, request, jsonify
from flask_cors import CORS
from fanar_client import ask_fanar_timed
from chat_session import (
    build_prompt, append_turn, get_turn_index,
    reset_history, make_tool_label, append_tool_result,
    append_router_decision, load_history,
)
from router import build_router_prompt, parse_router_response
from rules.local_rules import (
    improve_web_query, improve_place_query,
    improve_route_query, apply_local_router_rules,
)
from app import run_tools
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
CORS(app)

router_model = os.getenv("FANAR_ROUTER_MODEL", "Fanar")
responder_model = os.getenv("FANAR_RESPONDER_MODEL", "Fanar-C-2-27B")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_prompt = data.get("message", "")
    if not user_prompt:
        return jsonify({"error": "No message provided"}), 400
    try:
        history_before_turn = load_history()
        router_prompt = build_router_prompt(user_prompt, history_before_turn)
        router_raw, _ = ask_fanar_timed(router_prompt, router_model, max_tokens=350)
        router_data = parse_router_response(router_raw)
        router_data = apply_local_router_rules(user_prompt, history_before_turn, router_data)
        append_router_decision(router_data)
        tool_results, active_tool_label, _ = run_tools(router_data, user_prompt, history_before_turn)
        sent_prompt = build_prompt(user_prompt, tool_results=tool_results, active_tool_label=active_tool_label)
        response, _ = ask_fanar_timed(sent_prompt, responder_model, max_tokens=900)
        append_turn(user_prompt, response)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=False)
