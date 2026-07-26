"""AI Bounty Monitor — tracks known AI bounty programs and detects new challenges."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.ai_bounty.publisher import AIBountyEventPublisher

logger = logging.getLogger("orion.ai_bounty.monitor")

AI_BOUNTY_PROGRAMS: dict[str, dict[str, Any]] = {
    "imbue": {
        "name": "Imbue AI Bounty",
        "url": "https://imbue.com/bounty-program/",
        "description": "Break our agent — find vulnerabilities in autonomous AI agents",
        "payout_range": "$5,000 - $50,000",
        "focus_areas": ["prompt_injection", "agent_safety", "data_leakage", "tool_misuse"],
        "last_checked": None,
    },
    "anthropic": {
        "name": "Anthropic Red Teaming",
        "url": "https://www.anthropic.com/red-teaming",
        "description": "Red teaming AI safety measures and alignment research",
        "payout_range": "$500 - $15,000",
        "focus_areas": ["jailbreak", "prompt_injection", "bias", "safety_filter_bypass"],
        "last_checked": None,
    },
    "openai": {
        "name": "OpenAI Bug Bounty",
        "url": "https://openai.com/bug-bounty-program/",
        "description": "Security vulnerabilities in OpenAI products and API",
        "payout_range": "$200 - $20,000",
        "focus_areas": ["ssrf", "idor", "authentication", "authorization", "xss"],
        "last_checked": None,
    },
    "google_ai": {
        "name": "Google AI Red Team",
        "url": "https://bughunters.google.com/about/rules/ai-red-team",
        "description": "Vulnerabilities in Google AI products and infrastructure",
        "payout_range": "$500 - $30,000",
        "focus_areas": ["ai_red_team", "prompt_injection", "data_exposure", "model_manipulation"],
        "last_checked": None,
    },
}


@dataclass
class AIBountyChallenge:
    """A detected challenge from an AI bounty program."""

    platform: str
    challenge_id: str
    title: str
    url: str
    description: str = ""
    focus_areas: list[str] = field(default_factory=list)
    payout_range: str = ""
    targets: list[str] = field(default_factory=list)
    severity: str = "medium"
    detected_at: str = ""
    status: str = "new"  # new, scanning, scanned, reporting, done

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "challenge_id": self.challenge_id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "focus_areas": self.focus_areas,
            "payout_range": self.payout_range,
            "targets": self.targets,
            "severity": self.severity,
            "detected_at": self.detected_at,
            "status": self.status,
        }


class AIBountyMonitor:
    """Monitors AI bounty platforms for new challenges.

    Since AI bounty programs don't have standardized APIs, this monitor
    maintains a known program list and detects changes via periodic checks.
    The actual web scraping integration is incremental — the initial version
    uses the known program catalog and manual target input.
    """

    def __init__(self) -> None:
        self._programs: dict[str, dict[str, Any]] = dict(AI_BOUNTY_PROGRAMS)
        self._detected: dict[str, AIBountyChallenge] = {}
        self._publisher = AIBountyEventPublisher()

    def get_programs(self) -> list[dict[str, Any]]:
        return [
            {
                "platform_id": pid,
                "name": info["name"],
                "url": info["url"],
                "description": info["description"],
                "payout_range": info["payout_range"],
                "focus_areas": info["focus_areas"],
            }
            for pid, info in self._programs.items()
        ]

    def register_challenge(
        self,
        platform: str,
        challenge_id: str,
        title: str,
        url: str = "",
        description: str = "",
        targets: list[str] | None = None,
        focus_areas: list[str] | None = None,
        payout_range: str = "",
        severity: str = "medium",
    ) -> AIBountyChallenge:
        key = f"{platform}:{challenge_id}"
        existing = self._detected.get(key)
        if existing:
            existing.status = "new"
            return existing

        challenge = AIBountyChallenge(
            platform=platform,
            challenge_id=challenge_id,
            title=title,
            url=url,
            description=description,
            focus_areas=focus_areas or self._programs.get(platform, {}).get("focus_areas", []),
            payout_range=payout_range or self._programs.get(platform, {}).get("payout_range", ""),
            targets=targets or [],
            severity=severity,
            detected_at=datetime.now(timezone.utc).isoformat(),
            status="new",
        )
        self._detected[key] = challenge
        self._programs[platform]["last_checked"] = datetime.now(timezone.utc).isoformat()

        self._publisher.challenge_detected(
            platform=platform,
            challenge_id=challenge_id,
            title=title,
            url=url,
            severity=severity,
        )
        logger.info("New AI bounty challenge detected: %s/%s", platform, challenge_id)
        return challenge

    def get_challenges(
        self,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[AIBountyChallenge]:
        results = list(self._detected.values())
        if platform:
            results = [c for c in results if c.platform == platform]
        if status:
            results = [c for c in results if c.status == status]
        return sorted(results, key=lambda c: c.detected_at, reverse=True)

    def get_challenge(self, platform: str, challenge_id: str) -> AIBountyChallenge | None:
        return self._detected.get(f"{platform}:{challenge_id}")

    def update_challenge_status(self, platform: str, challenge_id: str, status: str) -> bool:
        challenge = self.get_challenge(platform, challenge_id)
        if challenge is None:
            return False
        challenge.status = status
        return True

    def mark_scanned(self, platform: str, challenge_id: str) -> None:
        self.update_challenge_status(platform, challenge_id, "scanned")

    def get_stats(self) -> dict[str, Any]:
        total = len(self._detected)
        by_status: dict[str, int] = {}
        by_platform: dict[str, int] = {}
        for c in self._detected.values():
            by_status[c.status] = by_status.get(c.status, 0) + 1
            by_platform[c.platform] = by_platform.get(c.platform, 0) + 1
        return {
            "total_challenges": total,
            "by_status": by_status,
            "by_platform": by_platform,
            "programs_tracked": len(self._programs),
        }
