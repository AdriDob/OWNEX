from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.skill_seekers.connector")

try:
    from skill_seekers import SkillSeekers as SkillSeekersClient

    _SKILL_SEEKERS_AVAILABLE = True
except ImportError:
    _SKILL_SEEKERS_AVAILABLE = False
    SkillSeekersClient = None  # type: ignore[assignment]


class SkillSeekersConnector(IConnector):
    """Connector to Skill Seekers — documentation-to-skills converter.

    Transforms documentation websites, GitHub repos, and PDFs into
    AI agent skills with automatic conflict detection.
    """

    connector_id = "skill_seekers"
    app_id = "ownex"
    display_name = "Skill Seekers"

    def __init__(self) -> None:
        self._connected = False
        self._client: SkillSeekersClient | None = None

    async def connect(self) -> bool:
        if not _SKILL_SEEKERS_AVAILABLE:
            logger.warning("skill-seekers not installed")
            return False
        try:
            skills_dir = os.environ.get(
                "OWNEX_SKILLS_DIR",
                str(Path.home() / ".ownex" / "skills"),
            )
            Path(skills_dir).mkdir(parents=True, exist_ok=True)
            self._client = SkillSeekersClient(output_dir=skills_dir)
            self._connected = True
            logger.info("Skill Seekers connected")
            return True
        except Exception as exc:
            logger.error("Skill Seekers connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return []

    async def extract_from_url(self, url: str) -> list[dict[str, Any]]:
        """Extract skills from a documentation URL."""
        if not self._client:
            return []
        try:
            skills = self._client.extract_from_url(url)
            return skills if isinstance(skills, list) else []
        except Exception as exc:
            logger.error("Skill Seekers extract URL failed: %s", exc)
            return []

    async def extract_from_github(self, repo_url: str) -> list[dict[str, Any]]:
        """Extract skills from a GitHub repository."""
        if not self._client:
            return []
        try:
            skills = self._client.extract_from_github(repo_url)
            return skills if isinstance(skills, list) else []
        except Exception as exc:
            logger.error("Skill Seekers extract GitHub failed: %s", exc)
            return []

    async def detect_conflicts(self, skill_dir: str | None = None) -> list[dict[str, Any]]:
        """Detect conflicting instructions across all learned skills."""
        if not self._client:
            return []
        try:
            conflicts = self._client.detect_conflicts(skill_dir)
            return conflicts if isinstance(conflicts, list) else []
        except Exception as exc:
            logger.error("Skill Seekers conflict detection failed: %s", exc)
            return []


async def on_skill_learn(event: object) -> None:
    if not _SKILL_SEEKERS_AVAILABLE:
        return
    connector = SkillSeekersConnector()
    await connector.connect()
    url = getattr(event, "url", "") or getattr(event, "source", "")
    if url:
        if "github" in url:
            result = await connector.extract_from_github(url)
        else:
            result = await connector.extract_from_url(url)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_doc_ingest(event: object) -> None:
    if not _SKILL_SEEKERS_AVAILABLE:
        return
    connector = SkillSeekersConnector()
    await connector.connect()
    url = getattr(event, "url", "") or getattr(event, "data", "")
    if url:
        result = await connector.extract_from_url(url)
        if result and hasattr(event, "set_result"):
            event.set_result(result)
