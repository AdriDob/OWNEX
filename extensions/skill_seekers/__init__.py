from __future__ import annotations

import logging

logger = logging.getLogger("ownex.skill_seekers")

try:
    from skill_seekers import SkillSeekers

    _SKILL_SEEKERS_AVAILABLE = True
except ImportError:
    _SKILL_SEEKERS_AVAILABLE = False
    logger.warning("skill-seekers not installed — Skill Seekers extension disabled")
