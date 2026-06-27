from pathlib import Path

root = Path(__file__).resolve().parents[1]

index_path = root / "frontend" / "index.html"
html = index_path.read_text(encoding="utf-8")
if "voice_location.js" not in html:
    html = html.replace(
        "</div><!-- /#chat-ui -->\n</body>",
        "</div><!-- /#chat-ui -->\n<script src=\"voice_waveform.js\"></script>\n<script src=\"voice_location.js\"></script>\n</body>",
    )
index_path.write_text(html, encoding="utf-8")

server_path = root / "backend" / "server.py"
s = server_path.read_text(encoding="utf-8")
start = s.index("def _qcri_answer")
end = s.index("\n\ndef _smalltalk_answer", start)
s = s[:start] + 'def _qcri_answer(user_prompt, history=""):\n    return None' + s[end:]
start = s.index("def _polish_response")
end = s.index("\n\ndef _open_frontend_after_start", start)
s = s[:start] + '''def _polish_response(response, tool_results=None):
    text = (response or "").strip()
    replacements = {
        "Quick route: Use public transport for this one.": "Best move: use metro/public transport.",
        "I understand that ": "",
        "Let me know if there's anything else I can assist with!": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text.strip()''' + s[end:]
server_path.write_text(s, encoding="utf-8")
print("Remaining local fixes applied")
