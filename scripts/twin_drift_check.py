#!/usr/bin/env python3
"""Twin-tree drift watchdog for OWNEX (core/ vs cores/).

Silent (no stdout = no drift detected) unless the two duplicate trees have
drifted apart, in which case it lists the differing real .py files.
"""

import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

CMD = (
    "diff -rq core cores 2>/dev/null "
    "| grep -E '^Files .* differ' "
    "| grep -vE '__pycache__|\\.pyc|__init__\\.py' "
    "| grep '\\.py' "
    "| awk -F' and ' '{print $2}' "
    "| grep -v __init__"
)

try:
    proc = subprocess.run(
        ["bash", "-c", CMD],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
except Exception as exc:  # pragma: no cover
    print(f"DRIFT-CHECK ERROR: {exc}")
    raise SystemExit(1) from None

files = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
if files:
    print(f"DRIFT core/ vs cores/: {len(files)} archivos .py difieren:\n" + "\n".join(files))
