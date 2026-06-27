from pathlib import Path
from datetime import datetime
import argparse
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "demo_fallback"
BACKUP_DIR = ROOT / "_demo_backups"


def backup():
    if not TARGET.exists():
        print("demo_fallback folder not found")
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    out = BACKUP_DIR / ("demo_fallback_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in TARGET.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(ROOT))
    print("Backup written:", out)


def latest_backup():
    if not BACKUP_DIR.exists():
        return None
    items = sorted(BACKUP_DIR.glob("demo_fallback_*.zip"))
    return items[-1] if items else None


def restore(path=None):
    src = Path(path) if path else latest_backup()
    if not src or not src.exists():
        print("No backup found")
        return
    if TARGET.exists():
        shutil.rmtree(TARGET)
    with zipfile.ZipFile(src, "r") as z:
        z.extractall(ROOT)
    print("Restored demo_fallback from:", src)


def status():
    print("Target exists:", TARGET.exists())
    print("Backup dir:", BACKUP_DIR)
    print("Latest backup:", latest_backup())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backup", "restore", "status"])
    parser.add_argument("--file")
    args = parser.parse_args(sys.argv[1:])
    if args.command == "backup":
        backup()
    elif args.command == "restore":
        restore(args.file)
    else:
        status()
