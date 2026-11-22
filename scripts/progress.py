#!/usr/bin/env python3
"""OWNEX progress ledger reporter.

Parses .ai/PROGRESS.md module table, computes global %, compares against
.ai/progress_snapshot.json, and prints per-module delta. Run at session
start and end:  python3 scripts/progress.py [--update]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / ".ai" / "PROGRESS.md"
SNAPSHOT = ROOT / ".ai" / "progress_snapshot.json"

_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([A-Z_]+)\s*\|")


def parse() -> dict[str, dict]:
    modules: dict[str, dict] = {}
    for line in PROGRESS.read_text().splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        name, pct, state = m.group(1).strip(), int(m.group(2)), m.group(3)
        if name in ("Módulo",) or set(name) <= {"-", " "}:
            continue
        modules[name] = {"pct": pct, "state": state}
    return modules


def main() -> int:
    update = "--update" in sys.argv
    modules = parse()
    if not modules:
        print("no modules parsed from", PROGRESS)
        return 1

    total = sum(m["pct"] for m in modules.values()) / len(modules)
    prev = {}
    if SNAPSHOT.exists():
        try:
            prev = json.loads(SNAPSHOT.read_text()).get("modules", {})
        except Exception:
            prev = {}

    print(f"{'MODULE':<38} {'%':>4} {'STATE':<14} {'DELTA':>6}")
    print("-" * 66)
    ups = downs = 0
    for name, m in modules.items():
        old = prev.get(name, {}).get("pct")
        delta = "" if old is None else f"{m['pct'] - old:+d}"
        if isinstance(old, int):
            ups += m["pct"] > old
            downs += m["pct"] < old
        print(f"{name:<38} {m['pct']:>4} {m['state']:<14} {delta:>6}")
    print("-" * 66)
    print(f"GLOBAL: {total:.1f}%  ({len(modules)} modules)  ↑{ups} ↓{downs}")

    states: dict[str, int] = {}
    for m in modules.values():
        states[m["state"]] = states.get(m["state"], 0) + 1
    print("states:", ", ".join(f"{k}={v}" for k, v in sorted(states.items())))

    if update:
        SNAPSHOT.write_text(json.dumps({"modules": modules, "global_pct": round(total, 1)}, indent=2))
        print(f"snapshot written → {SNAPSHOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
