from __future__ import annotations

import sys
from pathlib import Path

from core.self_heal.engine import SelfHealEngine

project_dir = Path(__file__).resolve().parent.parent.parent

engine = SelfHealEngine(str(project_dir))
report = engine.heal()
print(report.summary)

print("\nValidating critical imports...")
for m in engine.validate_imports():
    status = "✓" if m["status"] == "ok" else "✗"
    msg = m.get("error", "")
    print(f"  {status} {m['module']} {msg}")

print(f"\nHeal complete: {report.fixed}/{report.total} actions taken")
sys.exit(0)
