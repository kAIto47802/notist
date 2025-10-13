import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL_BASE = "https://kaito47802.github.io/NotifyState"

target = ROOT / "_static" / "versions.json"

tags = subprocess.run(["git", "tag"], text=True, capture_output=True).stdout.split()

versions = [
    {"version": "dev", "name": "dev", "url": f"{URL_BASE}/dev/"},
] + [
    {"version": v, "name": v, "url": f"{URL_BASE}/{v}/"}
    if i
    else {"version": v, "name": f"{v} (latest)", "url": URL_BASE}
    for i, v in enumerate(sorted(tags, reverse=True))
]

target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(versions, indent=2))

print(f"Wrote {target}")
