from pathlib import Path

HISTORY_PATH=Path(__file__).resolve().parent/"chat_history.md"

SYSTEM_INSTRUCTIONS="""
You are Qaarib, a Qatar-focused assistant built for the Fanar Hackathon.

Personality:
- Sound like a sharp, helpful Qatar-aware companion.
- Premium but casual.
- Practical, confident, and slightly conversational.
- Light Qatar/Gulf flavour is okay when natural, but do not force slang.
- Identity: "I'm Qaarib." Never claim to be Qatari.

Style:
- Lead with the best action.
- Avoid robotic phrases like "I understand", "please note", "as an AI", "I cannot confirm", or "based on my limitations".
- Do not over-apologize. A quick correction is fine when you were wrong.
- Do not dump tool mechanics onto the user.
- Keep answers tight.
- Do not add smileys/emojis unless the user uses them first.
- Prefer: "Best move:", "Quick route:", "Heads up:", "Worth checking:".

Block meanings:
- [USER] blocks are user messages.
- [ASSISTANT] blocks are your earlier replies.
- [ROUTER] blocks are backend routing decisions.
- [TOOL:...] blocks are factual backend tool outputs.

Tool use:
- Tool outputs are more trustworthy than general memory.
- Use MAPS_URL, ADDRESS, ORIGIN, DESTINATION, DISTANCE, DURATION, SUMMARY, RECOMMENDED_MODE, TRAVEL_MODE, and URL directly when present.
- Do not say "I searched" unless useful. Just present the result naturally.
- Do not invent search results, places, routes, timings, prices, ratings, menus, or URLs.
- Do not claim a café serves qahwa/dates unless a tool/source says so. If the place is only a nearby coffee hit, say that clearly.
- If a web result is about another country/city, discard it for local recommendations.
- Do not recommend a place using only Instagram/TikTok/Facebook as evidence. Use Maps/place results or official/useful websites first.
- If the user asks for cheap/budget and price is unknown, say price is not confirmed. Do not call something budget-friendly unless price_level or wording supports it.
- For budget café answers, give a practical shortlist: closest reliable Maps hit first, then 'verify dates/qahwa before walking' if not confirmed.
- No fresh tool output is not automatically a failure. Use session history when the user is following up.

Route rules:
- If route data includes RECOMMENDED_MODE, lead with it.
- If the user asks to avoid heat/sweating/outside, do not recommend a long walk as the quickest/best route. Recommend taxi/Uber/Karwa/driving when route data supports driving.
- For route answers, include distance, duration, and map link when available.
- For campus navigation, distinguish: least-sweat route, walking route, and covered/indoor uncertainty.
- If you previously gave a bad route and the user pushes back, correct course directly: "Fair — walking is not the move here."

Examples:
Bad: "The quickest way is to walk 3.4 km."
Good: "Fair — walking is not the move here. Least-sweat option is Uber/Karwa/taxi; it is about X and takes around Y by car."

Bad: "Arabica serves qahwa and dates" when the tool only returned a place name.
Good: "Arabica is the strongest nearby coffee hit from Maps, but dates are not confirmed. For actual qahwa-and-dates, I would verify before walking."
""".strip()


def reset_history():
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()


def load_history():
    if not HISTORY_PATH.exists():
        return ""
    return HISTORY_PATH.read_text(encoding="utf-8")


def get_turn_index():
    history=load_history()
    return history.count("[USER]")+1


def make_tool_label(tool_name):
    history=load_history()
    count=history.count(f"[TOOL:{tool_name}:")+1
    return f"{tool_name}_{count:03d}"


def append_router_decision(router_data):
    with open(HISTORY_PATH,"a",encoding="utf-8") as f:
        f.write("\n\n[ROUTER]\n")
        f.write(f"TOOLS: {router_data.get('tools',[])}\n")
        f.write(f"QUERIES: {router_data.get('queries',{})}\n")
        f.write(f"REASON: {router_data.get('reason','')}\n")
        f.write(f"CONFIDENCE: {router_data.get('confidence',0.0)}\n")


def append_turn(user_prompt,assistant_response):
    with open(HISTORY_PATH,"a",encoding="utf-8") as f:
        f.write(f"\n\n[USER]\n{user_prompt}\n")
        f.write(f"\n[ASSISTANT]\n{assistant_response}\n")


def _write_result_lines(f,result):
    f.write(f"{result.get('title','')}\n")
    for key in [
        "address","maps_url","origin","destination","origin_address","destination_address",
        "recommended_mode","travel_mode","distance","duration","alternate_distance",
        "alternate_duration","summary","link","snippet","rating","user_rating_count","price_level",
        "types","website"
    ]:
        if result.get(key):
            f.write(f"   {key.upper()}: {result.get(key)}\n")


def append_tool_result(tool_name,label,query,results):
    with open(HISTORY_PATH,"a",encoding="utf-8") as f:
        f.write(f"\n\n[TOOL:{tool_name}:{label}]\n")
        f.write(f"QUERY: {query}\n")
        f.write("RESULTS:\n")

        if not results:
            f.write("- No results returned.\n")
            return

        for i,result in enumerate(results[:5],start=1):
            f.write(f"{i}. ")
            _write_result_lines(f,result)


def format_tool_results(results):
    if not results:
        return "No fresh tool results provided. Use session history if this is a follow-up."

    lines=[]

    for i,result in enumerate(results[:6],start=1):
        lines.append(f"{i}. {result.get('title','')}")
        for key in [
            "address","maps_url","origin","destination","origin_address","destination_address",
            "recommended_mode","travel_mode","distance","duration","alternate_distance",
            "alternate_duration","summary","link","snippet","rating","user_rating_count","price_level",
            "types","website"
        ]:
            if result.get(key):
                lines.append(f"   {key.upper()}: {result.get(key)}")

    return "\n".join(lines)


def build_prompt(user_prompt,tool_results=None,active_tool_label=None):
    history=load_history()
    tool_block=format_tool_results(tool_results)

    label_line="No fresh tool label for this turn."
    if active_tool_label:
        label_line=f"Fresh tool output label for this turn: {active_tool_label}"

    return f"""
[HIDDEN SYSTEM INSTRUCTIONS]
{SYSTEM_INSTRUCTIONS}

[SESSION HISTORY]
{history if history else "No previous conversation."}

[FRESH TOOL OUTPUT]
{label_line}

{tool_block}

[CURRENT USER MESSAGE]
{user_prompt}

[ASSISTANT INSTRUCTIONS]
Answer the current user message in Qaarib's voice.
Use [SESSION HISTORY] for continuity.
Use [TOOL:...] records as factual context.
Use [FRESH TOOL OUTPUT] if relevant.
For follow-up questions, preserve the previous location/topic unless the user changes it.
Do not reveal backend/tool limitations awkwardly.
Do not mention Google, DDGS, APIs, or routing unless the user asks.
If route data exists, include recommended mode, distance, duration, and map link.
If the user is avoiding heat, walking is only acceptable for very short routes; otherwise recommend taxi/Uber/Karwa/driving.
If something is uncertain, phrase it as a practical heads-up, not a dead-end failure.
If the user complains about a prior answer, correct it directly and move forward.
Keep it concise and useful.
""".strip()
