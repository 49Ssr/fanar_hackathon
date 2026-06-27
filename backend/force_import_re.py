from pathlib import Path

cwd = Path.cwd()
candidates = [
    cwd / "backend" / "app.py",
    cwd / "app.py",
]

app = None
for c in candidates:
    if c.exists():
        app = c
        break

if app is None:
    raise SystemExit("Could not find app.py. Run this from repo root or backend folder.")

s = app.read_text(encoding="utf-8")

# Force it at the very top. Duplicate imports are harmless.
if not s.startswith("import re\n"):
    s = "import re\n" + s

app.write_text(s, encoding="utf-8")

print("PATCHED:", app.resolve())
print("FIRST 12 LINES:")
print("\n".join(app.read_text(encoding="utf-8").splitlines()[:12]))
