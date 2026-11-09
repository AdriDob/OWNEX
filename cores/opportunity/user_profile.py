"""User profile store — single source for matcher/drafter personalization.

JSON file under OWNEX data dir. Editable via API; consumed by
remote_job_matcher (profile arg) and application_drafter.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_FIELDS = {
    "name", "full_name", "headline", "title", "skills", "experience_years",
    "english_level", "portfolio_url", "location", "payment_methods",
    "availability", "bio", "cv_text",
}


def _path() -> Path:
    from cores.connections.importer import get_config

    return Path(get_config().data_dir) / "user_profile.json"


def get_profile() -> dict[str, Any]:
    p = _path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.warning("user_profile unreadable")
    return {}


def update_profile(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge allowed fields only — unknown keys are dropped, never stored."""
    profile = get_profile()
    for k, v in updates.items():
        if k in ALLOWED_FIELDS:
            profile[k] = v
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    return profile
