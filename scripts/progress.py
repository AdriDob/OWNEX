#!/usr/bin/env python3
"""OWNEX progress ledger reporter — three independent metrics.

Parses .ai/PROGRESS.md:
  - module table        -> PRODUCT_COMPLETENESS
  - Operational table   -> OPERATIONAL_READINESS (state-credit per row)
  - Revenue stages      -> REVENUE_VALIDATION (state-credit per stage)

Snapshots are append-only under .ai/progress_history/ (never overwritten).
Regression detection: a module % that drops vs the last snapshot is
flagged REGRESSION unless the state cell carries ``regression-ok``.

Usage:  python3 scripts/progress.py [--update] [--json]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / ".ai" / "PROGRESS.md"
HISTORY = ROOT / ".ai" / "progress_history"
LATEST = HISTORY / "latest.json"
SCHEMA_VERSION = 2

_MODULE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([A-Z_()\- ]+?)\s*\|\s*([^|]*)\|")
_GENERIC_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([A-Z_]+)\s*\|\s*([^|]*)\|")
_COMMIT_RE = re.compile(r"`([0-9a-f]{7,40})`")

_STATE_CREDIT = {
    "DONE": 1.0,
    "VERIFIED": 1.0,
    "ACCEPTED": 1.0,
    "TESTED": 0.75,
    "INTEGRATED": 0.6,
    "IMPLEMENTED": 0.4,
    "IN_PROGRESS": 0.3,
    "PARTIAL": 0.3,
    "PLANNED": 0.1,
    "BLOCKED": 0.0,
    "NOT_STARTED": 0.0,
    "PENDING": 0.0,
    "UNKNOWN": 0.0,
}


def _section(lines: list[str], title: str) -> list[str]:
    """Return raw lines between '## <title>' and the next '## '."""
    out: list[str] = []
    inside = False
    for ln in lines:
        if ln.startswith("## "):
            if inside:
                break
            inside = title.lower() in ln.lower()
            continue
        if inside:
            out.append(ln)
    return out


def _pct_for_state(state: str) -> float:
    return _STATE_CREDIT.get(state.strip().upper(), 0.0)


def _table_pct(lines: list[str], title: str) -> tuple[float, int]:
    rows = 0
    credit = 0.0
    for ln in _section(lines, title):
        m = _GENERIC_ROW.match(ln)
        if not m:
            continue
        state_clean = m.group(2).strip().upper()
        if state_clean in ("ESTADO", "INDICADOR") or set(state_clean) <= {"-", " "}:
            continue
        rows += 1
        credit += _pct_for_state(state_clean)
    return (round(100 * credit / rows, 1) if rows else 0.0), rows


def parse() -> dict:
    lines = PROGRESS.read_text().splitlines()
    modules: dict[str, dict] = {}
    for ln in _section(lines, "## Módulos"):
        m = _MODULE_ROW.match(ln)
        if not m:
            continue
        name, pct, state, rest = m.groups()
        name = name.strip()
        if not name or name == "Módulo" or set(name) <= {"-", " "}:
            continue
        modules[name] = {
            "pct": int(pct),
            "state": state.strip(),
            "evidence": rest.strip(),
            "regression_justified": "regression-ok" in state.lower(),
        }

    op_pct, op_rows = _table_pct(lines, "Operational Readiness")
    rev_pct, rev_rows = _table_pct(lines, "Revenue Validation")
    prod_pct = round(sum(m["pct"] for m in modules.values()) / len(modules), 1) if modules else 0.0
    return {
        "modules": modules,
        "product_completeness": prod_pct,
        "operational_readiness": op_pct,
        "revenue_validation": rev_pct,
        "operational_rows": op_rows,
        "revenue_rows": rev_rows,
    }


def _head_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _check_evidence_commits(modules: dict) -> list[str]:
    """Flag evidence cells citing commit hashes missing from git."""
    missing: list[str] = []
    for name, m in modules.items():
        for h in _COMMIT_RE.findall(m["evidence"]):
            r = subprocess.run(
                ["git", "cat-file", "-e", h],
                cwd=ROOT,
                capture_output=True,
                timeout=10,
            )
            if r.returncode != 0:
                missing.append(f"{name}: commit {h} not found")
    return missing


def _load_latest() -> dict | None:
    if LATEST.exists():
        try:
            return json.loads(LATEST.read_text())
        except Exception:
            return None
    return None


def _append_history(snapshot: dict) -> None:
    HISTORY.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (HISTORY / f"{ts}.json").write_text(json.dumps(snapshot, indent=2))


def report(data: dict, prev: dict | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    lines = [
        f"PRODUCT_COMPLETENESS : {data['product_completeness']:>5.1f}%  ({len(data['modules'])} modules)",
        f"OPERATIONAL_READINESS: {data['operational_readiness']:>5.1f}%  ({data['operational_rows']} items)",
        f"REVENUE_VALIDATION   : {data['revenue_validation']:>5.1f}%  ({data['revenue_rows']} stages)",
        "",
        f"{'MODULE':<52} {'%':>4} {'STATE':<14} {'DELTA':>5}",
        "-" * 80,
    ]
    prev_mods = (prev or {}).get("modules", {})
    for name, m in data["modules"].items():
        old = prev_mods.get(name, {}).get("pct")
        delta = "" if old is None else f"{m['pct'] - old:+d}"
        flag = ""
        if old is not None and m["pct"] < old and not m["regression_justified"]:
            flag = "  REGRESSION"
            warnings.append(f"{name}: {old}% -> {m['pct']}%")
        lines.append(f"{name:<52} {m['pct']:>4} {m['state']:<14} {delta:>5}{flag}")
    lines.append("-" * 80)
    for w in warnings:
        lines.append(f"WARNING: {w}")
    return "\n".join(lines), warnings


def main() -> int:
    update = "--update" in sys.argv
    as_json = "--json" in sys.argv
    data = parse()
    if not data["modules"]:
        print("no modules parsed from", PROGRESS)
        return 1
    prev = _load_latest()
    text, warnings = report(data, prev)
    missing = _check_evidence_commits(data["modules"])
    if as_json:
        print(json.dumps({
            "schema": SCHEMA_VERSION,
            "commit": _head_commit(),
            "product_completeness": data["product_completeness"],
            "operational_readiness": data["operational_readiness"],
            "revenue_validation": data["revenue_validation"],
            "regressions": warnings,
            "missing_evidence_commits": missing,
        }, indent=2))
    else:
        print(text)
        for w in missing:
            print(f"EVIDENCE-MISSING: {w}")
    if update:
        snapshot = {
            "schema": SCHEMA_VERSION,
            "ts": datetime.now(UTC).isoformat(),
            "commit": _head_commit(),
            "product_completeness": data["product_completeness"],
            "operational_readiness": data["operational_readiness"],
            "revenue_validation": data["revenue_validation"],
            "modules": data["modules"],
            "regressions": warnings,
            "missing_evidence_commits": missing,
        }
        _append_history(snapshot)
        LATEST.write_text(json.dumps(snapshot, indent=2))
        print("\nsnapshot -> .ai/progress_history/ + latest.json")
    return 1 if warnings or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
