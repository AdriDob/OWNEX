from __future__ import annotations

import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent.parent

from core.self_update.engine import SelfUpdateEngine

engine = SelfUpdateEngine(str(project_dir))

info = engine.check_for_update()
print(f"Current: {info.current_version}")
print(f"Behind: {info.commits_behind} commits")
print(f"Update available: {info.has_update}")

if info.has_update:
    print("\nUpdating...")
    result = engine.update(auto_restart=False)
    print(f"Success: {result.success}")
    print(f"Pulled: {result.pulled}")
    print(f"Deps installed: {result.dependencies_installed}")
    if result.error:
        print(f"Error: {result.error}")
else:
    print("Already up to date.")
sys.exit(0)
