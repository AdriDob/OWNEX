"""Brave integration — maximum operational integration with PC/Brave under least privilege.

Detects Brave specifically, prefers it, and provides controlled browser automation
that respects platform APIs/OAuth when available and falls back to Playwright only
when allowed and non-sensitive. Never extracts passwords/cookies/tokens.
"""

from __future__ import annotations

import logging
import shutil
import webbrowser
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.browsing.brave")

BRAVE_NAMES = ["brave-browser", "brave", "brave.exe"]
BRAVE_PATHS_WINDOWS = [
    Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    Path(r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
]
BRAVE_PATHS_LINUX = [
    Path("/usr/bin/brave-browser"),
    Path("/usr/bin/brave"),
    Path("/snap/bin/brave"),
]


def detect_brave() -> dict[str, Any]:
    """Detect Brave installation. Returns {installed, path, is_default}."""
    path: Path | None = None
    for p in BRAVE_PATHS_WINDOWS + BRAVE_PATHS_LINUX:
        if p.exists():
            path = p
            break
    if not path:
        for name in BRAVE_NAMES:
            found = shutil.which(name)
            if found:
                path = Path(found)
                break

    is_default = False
    try:
        ctrl = webbrowser.get()
        if ctrl and "brave" in (getattr(ctrl, "name", "") or "").lower():
            is_default = True
    except Exception:
        pass

    return {"installed": path is not None, "path": str(path) if path else None, "is_default": is_default}


def open_in_brave(url: str, prefer_brave: bool = True) -> dict[str, Any]:
    """Open URL in Brave if available, else default browser. Never steals sessions."""
    brave = detect_brave()
    if prefer_brave and brave["installed"] and brave["path"]:
        try:
            # Try to launch Brave explicitly via webbrowser controller
            # Fallback to default browser if Brave controller not registered.
            controller = None
            try:
                controller = webbrowser.get("brave")
            except Exception:
                controller = None
            if controller:
                controller.open(url, new=2, autoraise=True)
                return {"opened": True, "browser": "brave", "url": url}
        except Exception as exc:
            logger.warning("Brave open failed, falling back: %s", exc)

    # Fallback: system default (could still be Brave)
    try:
        webbrowser.open(url, new=2, autoraise=True)
        return {"opened": True, "browser": "default", "url": url}
    except Exception as exc:
        logger.warning("open_in_brave failed: %s", exc)
        return {"opened": False, "browser": None, "url": url, "error": str(exc)}


def browser_context() -> dict[str, Any]:
    """Minimal browser context for work accompaniment (no secrets)."""
    brave = detect_brave()
    return {
        "brave": brave,
        "default_browser": detect_brave()["path"] or "unknown",
        "capabilities": {
            "open_url": True,
            "detect_pages": False,  # requires extension/API — not claimed as automatic
            "automation": "playwright when explicitly allowed and non-sensitive",
        },
        "security_note": "Never extracts passwords/cookies/tokens. Use Identity Vault + Human Gate for auth.",
    }
