#!/usr/bin/env python3
"""OWNEX Doctor — quick diagnostic for platform health."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone


def check_python() -> dict[str, str]:
    return {
        "name": "Python",
        "status": "ok",
        "detail": f"{sys.version.split()[0]} on {sys.platform}",
    }


def check_module(name: str) -> dict[str, str]:
    try:
        importlib.import_module(name)
        return {"name": name, "status": "ok", "detail": "imported"}
    except Exception as e:
        return {"name": name, "status": "error", "detail": str(e)}


checks = [
    check_python(),
    check_module("fastapi"),
    check_module("uvicorn"),
    check_module("sqlalchemy"),
    check_module("httpx"),
    check_module("api"),
    check_module("core.capabilities.registry"),
    check_module("core.events.event_bus"),
    check_module("core.sensors.base"),
    check_module("extensions.playwright.playwright_sensor"),
]

print("OWNEX Doctor")
print(f"Time: {datetime.now(timezone.utc).isoformat()}")
print()

all_ok = True
for c in checks:
    icon = "✓" if c["status"] == "ok" else "✗"
    print(f"  {icon} {c['name']}: {c['detail']}")
    if c["status"] != "ok":
        all_ok = False

print()
if all_ok:
    print("System ready.")
else:
    print("Some checks failed. Run: pip install -e .")
    sys.exit(1)
