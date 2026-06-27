from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import os
import time
import re
import threading
import webbrowser
import requests

from fanar_client import ask_fanar_timed
from chat_session import build_prompt, append_turn, reset_history, append_router_decision, load_history
from router import build_router_prompt, parse_router_response
from rules.local_rules import apply_local_router_rules, get_pre_router_plan, _local_rule_plan
from app import run_tools, direct_answer_from_results

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_INDEX = FRONTEND_DIR / "index.html"
load_dotenv(BASE_DIR / ".env")
load_dotenv()

flask_app = Flask(__name__)
app = flask_app
CORS(app)

FANAR_9B_MODEL = "Fanar-C-1-8.7B"
router_model = os.getenv("FANAR_ROUTER_MODEL", FANAR_9B_MODEL)
responder_model = os.getenv("FANAR_RESPONDER_MODEL", FANAR_9B_MODEL)
USE_FANAR_ROUTER = os.getenv("QAARIB_USE_FANAR_ROUTER", "0") == "1"
AURA_TTS_ENABLED = os.getenv("FANAR_AURA_TTS_ENABLED", "1") == "1"
AURA_TTS_MODEL = os.getenv("FANAR_AURA_TTS_MODEL", "Fanar-Aura-TTS-2")
AURA_TTS_VOICE = os.getenv("FANAR_AURA_TTS_VOICE", "Hamad")
AURA_TTS_FORMAT = os.getenv("FANAR_AURA_TTS_FORMAT", "mp3")
AURA_TTS_TIMEOUT = int(os.getenv("FANAR_AURA_TTS_TIMEOUT", "12"))
FANAR_API_KEY = os.getenv("FANAR_API_KEY")


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _location_context(location):
    if not isinstance(location, dict):
        return ""
    try:
        lat = float(location.get("lat"))
        lng = float(location.get("lng"))
    except Exception:
        return ""
    acc = location.get("accuracy")
    acc_text = f" accuracy={acc}m" if acc else ""
    return f"\n\n[CURRENT_LOCATION]\nlat={lat:.6f} lng={lng:.6f}{acc_text}\nUse this as the user's current location for 'here', 'near me', or 'my location' route/place requests."


def _compact_fanar_prompt(user_prompt, history=""):
    recent = history[-1200:] if history else ""
    return f"""
You are Qaarib, a Qatar-local assistant.
Sound like a switched-on local helper: warm, practical, brief, not corporate.
Do not say "I understand" or "let me know if you need anything else".
Prefer: "Best move:", "Easy one:", "Heads up:", "Worth checking:".
Stay Qatar-local. Do not mention provider failover, APIs, backend issues, or internal routing.

Hard Qatar transit facts:
- QCRI/HBKU is in Education City.
- Education City access is on the Green Line, especially Qatar National Library / Education City stations depending exact building and entrance.
- QCRI is not on the Red Line or Gold Line.
- Legtaifiya is on the Red Line and links to Lusail Tram; it is not on the Green Line.
- DECC is on the Red Line, not the Education City/QCRI stop.
- If corrected by the user, do not invent bus routes or new stations. Lock to known facts or ask to verify.

Recent context:
{recent if recent else "No previous context."}

User: {user_prompt}
Qaarib:
""".strip()


def _qcri_answer(user_prompt, history=""):
    text = _clean(user_prompt)
    h = _clean(history)
    qcri_context = any(x in text or x in h[-2500:] for x in ["qcri", "hbku", "education city", "qatar computing research institute"])
    correction = any(x in text for x in ["wrong", "not on", "wtf", "no", "incorrect", "again"])
    if any(x in text for x in ["where qcri", "where is qcri", "do you know where qcri", "hbku qcri", "qatar computing research institute"]):
        return "Yes — QCRI is in Education City, within HBKU/Qatar Foundation.\nMetro-wise, think Green Line: Qatar National Library or Education City station, depending which entrance/building you’re using.\nNot Red Line, not Gold Line."
    if qcri_context and correction:
        return "Fair — lock this in: QCRI/HBKU is Education City.\nUse the Green Line side: Qatar National Library / Education City area.\nNot Red Line, not Gold Line, not Legtaifiya, and not DECC. I shouldn’t have guessed bus routes there."
    return None


def _smalltalk_answer(user_prompt, location=None):
    text = _clean(user_prompt)
    if any(x in text for x in ["how are u", "how are you", "how r u", "how you doing", "how u doing"]):
        return "Alhamdulillah, doing good. What’s the move — route, place, event, or something Qatar-local?"
    location_phrases = [
        "do you know where i am", "where am i", "can you tell where i am",
        "where am i located", "where am i right now", "where am i rn",
        "my current location", "what is my location", "what's my location",
        "where exactly am i", "locate me", "near which building", "what building am i",
    ]
    if any(p in text for p in location_phrases):
        if isinstance(location, dict) and location.get("lat") and location.get("lng"):
            lat = float(location["lat"]); lng = float(location["lng"])
            return (f"I’ve got your browser location: roughly {lat:.5f}, {lng:.5f} "
                    f"(accuracy depends on your device). I can’t name the exact building from coordinates alone, "
                    f"but I can use this for ‘near me’ places or ‘from here’ routes — just tell me where you want to go.")
        return "I don’t get your live location unless your browser shares it or you tell me a landmark. Drop the area and I’ll work from there."
    return None


def _extended_greeting_answer(user_prompt):
    text = _clean(user_prompt)
    if not text:
        return None
    tokens = [t.strip("!?.،,;:") for t in text.split() if t.strip("!?.،,;:")]
    if len(tokens) > 10:
        return None
    greeting_tokens = {"hi", "hello", "hey", "yo", "salam", "salaam", "assalamu", "hala", "ahlan", "ahlaan", "marhaba", "sahlan", "sahla", "sahlain"}
    filler_tokens = {"wa", "wala", "w", "bro", "brother", "habibi", "akhi", "man", "dear", "how", "are", "you", "u", "r", "doing", "going", "it", "is", "things"}
    has_greeting = any(t in greeting_tokens for t in tokens)
    greeting_start = tokens and tokens[0] in greeting_tokens
    has_how_are_you = any(p in text for p in ["how are you", "how u doing", "how you doing", "how r u", "how are u", "how's it going", "hows it going"])
    has_salam_pair = ("salam" in tokens or "salaam" in tokens or "assalamu" in tokens) and any(t in {"alaikum", "alaykum", "alikum"} for t in tokens)
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
            return text + (f"\n\nMap: {maps_url}" if maps_url else "")
        if origin == "Ras Bu Aboud" and destination == "Hamad International Airport T1":
            text = "Best move: metro, not taxi.\n1. Ras Bu Aboud → Msheireb on the Gold Line.\n2. Msheireb → Oqba Ibn Nafie on the Red Line.\n3. Follow the HIA T1 airport branch to the terminal.\nCheck live Qatar Rail signs before tapping in."
            return text + (f"\n\nMap: {maps_url}" if maps_url else "")
    replacements = {
        "Take Red Line southbound toward Msheireb; then follow Al Wakra / HIA T1 branch signage if continuing past Oqba Ibn Nafie to Oqba Ibn Nafie.": "Take the Red Line southbound to Oqba Ibn Nafie.",
        "Continue through Oqba Ibn Nafie. Take Red Line airport branch toward HIA T1 to Hamad International Airport T1.": "From Oqba Ibn Nafie, take the airport branch to Hamad International Airport T1.",
        "Quick route: Use public transport for this one.": "Best move: use metro/public transport.",
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
            webbrowser.open(f"http://127.0.0.1:{port}/", new=2)
            print(f"Opened frontend: http://127.0.0.1:{port}/")
        except Exception as exc:
            print(f"Could not auto-open frontend: {exc}")
    threading.Thread(target=_open, daemon=True).start()


@app.route("/", methods=["GET"])
def frontend_index():
    if not FRONTEND_INDEX.exists():
        return "frontend/index.html not found", 404
    html = FRONTEND_INDEX.read_text(encoding="utf-8")
    if "voice_location.js" not in html:
        html = html.replace("</body>", '<script src="/voice_location.js"></script>\n</body>')
    return Response(html, mimetype="text/html")


@app.route("/aura_tts", methods=["POST"])
def aura_tts():
    if not AURA_TTS_ENABLED or not FANAR_API_KEY:
        return jsonify({"error": "Fanar Aura TTS unavailable"}), 503
    data = request.get_json(silent=True) or {}
    text = re.sub(r"\s+", " ", (data.get("text") or "")).strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    text = text[:700]
    try:
        r = requests.post(
            "https://api.fanar.qa/v1/audio/speech",
            headers={"Authorization": f"Bearer {FANAR_API_KEY}", "Content-Type": "application/json"},
            json={"model": AURA_TTS_MODEL, "input": text, "voice": AURA_TTS_VOICE, "response_format": AURA_TTS_FORMAT, "stream": False},
            timeout=AURA_TTS_TIMEOUT,
        )
        r.raise_for_status()
        mimetype = "audio/wav" if AURA_TTS_FORMAT == "wav" else "audio/mpeg"
        return Response(r.content, mimetype=mimetype, headers={"Cache-Control": "no-store"})
    except Exception as exc:
        print(f"Fanar Aura TTS failed: {str(exc)[:180]}")
        return jsonify({"error": "Fanar Aura TTS failed or is not authorized"}), 503


@app.route("/<path:filename>", methods=["GET"])
def frontend_asset(filename):
    if filename in {"chat", "reset", "health", "aura_tts"}:
        return "not found", 404
    path = FRONTEND_DIR / filename
    if path.exists() and path.is_file():
        return send_from_directory(FRONTEND_DIR, filename)
    return "not found", 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "qaarib-backend"})


@app.route("/reset", methods=["POST"])
def reset():
    reset_history()
    return jsonify({"status": "ok"})



def _build_widgets(router_data, tool_results):
    """Turn detected elements (router tools) + structured tool output into
    widget descriptors the frontend can render as cards. Data-driven: the widget
    type follows the tool the backend actually chose, not hardcoded per prompt.
    """
    widgets = []
    tools = (router_data or {}).get("tools", []) or []
    results = tool_results or []

    for r in results:
        if not isinstance(r, dict):
            continue
        # Route card — from route_plan tool output.
        if r.get("origin") and r.get("destination") and (r.get("travel_mode") or r.get("recommended_mode")):
            legs = []
            mode = r.get("recommended_mode", "")
            if mode:
                legs = [s.strip() for s in re.split(r"\+|→|->", mode) if s.strip()]
            widgets.append({
                "type": "route",
                "origin": r.get("origin", ""),
                "destination": r.get("destination", ""),
                "mode": r.get("travel_mode", ""),
                "legs": legs,
                "distance": r.get("distance", ""),
                "duration": r.get("duration", ""),
                "maps_url": r.get("maps_url", ""),
                "summary": r.get("summary", "") or r.get("final_answer", ""),
            })
        # Place card — from place_lookup tool output.
        elif r.get("title") and (r.get("address") or r.get("rating")):
            widgets.append({
                "type": "place",
                "name": r.get("title", ""),
                "address": r.get("address", ""),
                "rating": r.get("rating", ""),
                "rating_count": r.get("user_rating_count", ""),
                "price_level": r.get("price_level", ""),
                "maps_url": r.get("maps_url", ""),
                "website": r.get("website", ""),
            })
        # Calendar card — from calendar_event tool output.
        elif r.get("event_title") or (r.get("title") and r.get("start")):
            widgets.append({
                "type": "calendar",
                "title": r.get("event_title") or r.get("title", ""),
                "start": str(r.get("start", "")),
                "end": str(r.get("end", "")),
                "link": r.get("html_link") or r.get("maps_url", ""),
            })

    return widgets


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_prompt = (data.get("message") or "").strip()
    location = data.get("location")
    if not user_prompt:
        return jsonify({"error": "No message provided"}), 400

    router_ms = tool_ms = responder_ms = 0
    try:
        base_history = load_history()
        loc_ctx = _location_context(location)
        history_before_turn = base_history + loc_ctx
        enriched_prompt = user_prompt + loc_ctx

        direct = _qcri_answer(user_prompt, history_before_turn) or _smalltalk_answer(user_prompt, location) or _extended_greeting_answer(user_prompt)
        if direct:
            router_data = {"tools": [], "queries": {}, "reason": "local_direct_answer", "confidence": 1.0, "direct_answer": direct}
            append_router_decision(router_data)
            append_turn(user_prompt, direct)
            return jsonify({"response": direct, "router": router_data, "widgets": [], "timing": {"router_ms": 0, "tool_ms": 0, "responder_ms": 0}})

        pre = get_pre_router_plan(enriched_prompt, history_before_turn)
        if pre:
            append_router_decision(pre)
            tool_results = []
            if pre.get("direct_answer"):
                response = str(pre["direct_answer"]).strip()
            else:
                tool_start = time.perf_counter()
                tool_results, active_tool_label, _notes = run_tools(pre, enriched_prompt, history_before_turn)
                tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
                response = direct_answer_from_results(tool_results, pre)
                if not response:
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip() or "I handled that locally but couldn't compose a result. Try rephrasing the request."
            response = _polish_response(response, tool_results)
            append_turn(user_prompt, response)
            return jsonify({"response": response, "router": pre, "widgets": _build_widgets(pre, tool_results), "timing": {"router_ms": 0, "tool_ms": tool_ms, "responder_ms": 0}})

        local_plan = _local_rule_plan(enriched_prompt, history_before_turn)
        if local_plan:
            router_data = local_plan
        elif not USE_FANAR_ROUTER:
            router_data = {"tools": [], "queries": {}, "reason": "emergency_single_fanar_responder", "confidence": 0.7}
        else:
            try:
                router_prompt = build_router_prompt(enriched_prompt, history_before_turn)
                router_raw, router_ms = ask_fanar_timed(router_prompt, router_model, max_tokens=220)
                router_data = parse_router_response(router_raw)
            except Exception:
                router_data = apply_local_router_rules(enriched_prompt, history_before_turn, {"tools": [], "queries": {}, "reason": "router_fallback", "confidence": 0.0})
                router_ms = 0
            router_data = apply_local_router_rules(enriched_prompt, history_before_turn, router_data)

        append_router_decision(router_data)
        policy_answer = router_data.get("direct_answer")
        tool_results = []
        active_tool_label = None
        if policy_answer:
            response = str(policy_answer).strip()
        else:
            tool_start = time.perf_counter()
            tool_results, active_tool_label, _tool_notes = run_tools(router_data, enriched_prompt, history_before_turn)
            tool_ms = round((time.perf_counter() - tool_start) * 1000, 2)
            deterministic = direct_answer_from_results(tool_results, router_data)
            if deterministic:
                response = deterministic
            else:
                try:
                    sent_prompt = build_prompt(enriched_prompt, tool_results=tool_results, active_tool_label=active_tool_label) if router_data.get("tools") else _compact_fanar_prompt(enriched_prompt, history_before_turn)
                    response, responder_ms = ask_fanar_timed(sent_prompt, responder_model, max_tokens=320)
                except Exception:
                    parts = [r.get("final_answer") or r.get("summary", "") for r in (tool_results or []) if r.get("final_answer") or r.get("summary")]
                    response = "\n".join(p for p in parts if p).strip() or "Heads up — model is slow right now. Routes, places, time, and calendar tasks still work best if you ask directly."
                    responder_ms = 0

        response = _polish_response(response, tool_results)
        append_turn(user_prompt, response)
        return jsonify({"response": response, "router": router_data, "widgets": _build_widgets(router_data, tool_results), "timing": {"router_ms": router_ms, "tool_ms": tool_ms, "responder_ms": responder_ms}})
    except Exception as e:
        safe = str(e).split("\n")[0][:200] if str(e) else "An unexpected error occurred."
        return jsonify({"error": safe}), 500


if __name__ == "__main__":
    port = int(os.getenv("QAARIB_PORT", "5000"))
    _open_frontend_after_start(port)
    app.run(port=port, debug=False)
