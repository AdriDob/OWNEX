"""Open Source Work Categories — Classification and management.

Categorizes open source work opportunities by type and difficulty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.opensource")


class OpenSourceCategory(Enum):
    """Open source work categories."""

    BUG_BOUNTY = "bug_bounty"
    SECURITY_AUDIT = "security_audit"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    LOCALIZATION = "localization"
    TOOLING = "tooling"


class DifficultyLevel(Enum):
    """Difficulty levels for open source work."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class OpenSourceProject:
    """Open source project metadata."""

    name: str
    owner: str
    repository: str
    description: str
    stars: int
    language: str
    category: OpenSourceCategory
    difficulty: DifficultyLevel
    tags: list[str] = field(default_factory=list)
    url: str = ""
    last_updated: str = ""
    contributors: int = 0
    issues_open: int = 0
    issues_good_first: int = 0


@dataclass
class OpenSourceOpportunity:
    """Open source work opportunity."""

    project: OpenSourceProject
    issue_id: int
    title: str
    description: str
    category: OpenSourceCategory
    difficulty: DifficultyLevel
    labels: list[str] = field(default_factory=list)
    url: str = ""
    created_at: str = ""
    comments: int = 0
    assignees: list[str] = field(default_factory=list)


class OpenSourceCategoryManager:
    """Manages open source work categories and recommendations."""

    def __init__(self):
        self._categories = {
            OpenSourceCategory.BUG_BOUNTY: {
                "name": "Bug Bounty",
                "description": "Vulnerability research and PoC generation",
                "skills": ["security", "pentesting", "vulnerability analysis"],
                "platforms": ["hackerone", "bugcrowd", "intigriti"],
            },
            OpenSourceCategory.SECURITY_AUDIT: {
                "name": "Security Audit",
                "description": "Code review and security analysis",
                "skills": ["code review", "security", "static analysis"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.CODE_REVIEW: {
                "name": "Code Review",
                "description": "PR analysis and quality checks",
                "skills": ["code review", "quality assurance", "github"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.TESTING: {
                "name": "Testing",
                "description": "Unit tests, E2E tests, integration tests",
                "skills": ["testing", "pytest", "jest", "cypress"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.DOCUMENTATION: {
                "name": "Documentation",
                "description": "README, API docs, architecture docs",
                "skills": ["technical writing", "documentation", "markdown"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.INFRASTRUCTURE: {
                "name": "Infrastructure",
                "description": "DevOps, CI/CD, deployment",
                "skills": ["devops", "docker", "kubernetes", "ci/cd"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.PERFORMANCE: {
                "name": "Performance",
                "description": "Optimization, profiling, caching",
                "skills": ["performance", "profiling", "optimization"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.ACCESSIBILITY: {
                "name": "Accessibility",
                "description": "WCAG compliance, screen readers",
                "skills": ["a11y", "wcag", "screen readers"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.LOCALIZATION: {
                "name": "Localization",
                "description": "i18n, translations, RTL support",
                "skills": ["i18n", "translation", "localization"],
                "platforms": ["github", "gitlab"],
            },
            OpenSourceCategory.TOOLING: {
                "name": "Tooling",
                "description": "Developer tools, scripts, automation",
                "skills": ["automation", "tooling", "scripts"],
                "platforms": ["github", "gitlab"],
            },
        }

    def get_category_info(self, category: OpenSourceCategory) -> dict[str, Any]:
        """Get category information."""
        return self._categories.get(category, {})

    def list_categories(self) -> list[OpenSourceCategory]:
        """List all available categories."""
        return list(self._categories.keys())

    def get_categories_by_skill(self, skill: str) -> list[OpenSourceCategory]:
        """Get categories that require a specific skill."""
        matching = []
        for category, info in self._categories.items():
            if skill.lower() in [s.lower() for s in info["skills"]]:
                matching.append(category)
        return matching

    def get_categories_by_platform(self, platform: str) -> list[OpenSourceCategory]:
        """Get categories available on a specific platform."""
        matching = []
        for category, info in self._categories.items():
            if platform.lower() in [p.lower() for p in info["platforms"]]:
                matching.append(category)
        return matching

    def recommend_category(
        self,
        skills: list[str],
        platforms: list[str] | None = None,
    ) -> list[tuple[OpenSourceCategory, float]]:
        """Recommend categories based on skills and platform preferences.

        Returns list of (category, score) tuples sorted by score.
        """
        scores = []

        for category, info in self._categories.items():
            score = 0.0

            # Skill matching (70% weight)
            skill_matches = sum(1 for skill in skills if skill.lower() in [s.lower() for s in info["skills"]])
            skill_score = (skill_matches / len(info["skills"])) * 0.7
            score += skill_score

            # Platform matching (30% weight)
            if platforms:
                platform_matches = sum(
                    1 for platform in platforms if platform.lower() in [p.lower() for p in info["platforms"]]
                )
                platform_score = (platform_matches / len(info["platforms"])) * 0.3
                score += platform_score
            else:
                score += 0.3  # Bonus if no platform preference

            scores.append((category, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class OpenSourceContributionTracker:
    """Tracks open source contributions."""

    def __init__(self):
        self._contributions: dict[str, list[dict[str, Any]]] = {}

    def add_contribution(
        self,
        project: str,
        issue_id: int,
        title: str,
        category: OpenSourceCategory,
        status: str = "completed",
    ) -> None:
        """Add a contribution record."""
        if project not in self._contributions:
            self._contributions[project] = []

        self._contributions[project].append(
            {
                "issue_id": issue_id,
                "title": title,
                "category": category.value,
                "status": status,
                "timestamp": str(self._get_timestamp()),
            }
        )

        logger.info(f"[OPENSOURCE] Contribution added: {project}#{issue_id} - {title}")

    def get_contributions(self, project: str | None = None) -> list[dict[str, Any]]:
        """Get contributions, optionally filtered by project."""
        if project:
            return self._contributions.get(project, [])
        return [contrib for contributions in self._contributions.values() for contrib in contributions]

    def get_contribution_stats(self) -> dict[str, Any]:
        """Get contribution statistics."""
        total = sum(len(contribs) for contribs in self._contributions.values())
        by_category: dict[str, int] = {}
        by_project: dict[str, int] = {}

        for project, contributions in self._contributions.items():
            by_project[project] = len(contributions)
            for contrib in contributions:
                category = contrib["category"]
                by_category[category] = by_category.get(category, 0) + 1

        return {
            "total": total,
            "by_category": by_category,
            "by_project": by_project,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()


# Global instances
_category_manager = OpenSourceCategoryManager()
_contribution_tracker = OpenSourceContributionTracker()


def get_category_manager() -> OpenSourceCategoryManager:
    """Get the global category manager instance."""
    return _category_manager


def get_contribution_tracker() -> OpenSourceContributionTracker:
    """Get the global contribution tracker instance."""
    return _contribution_tracker
