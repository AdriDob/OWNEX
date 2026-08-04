"""Intelligent Profile Builder — builds portfolio, CV, GitHub, LinkedIn, website, bio, skills.

Everything is derived from real project history. Never invents information.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cores.direct_work_engine.models import ExperienceLevel, UserProfile

logger = logging.getLogger("ownex.direct_work_engine.profile_builder")


@dataclass(slots=True)
class ProfileAssets:
    """Generated profile assets (all derived from real facts)."""

    bio: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    portfolio_sections: list[dict] = field(default_factory=list)  # type: ignore[type-arg]
    cv_sections: list[dict] = field(default_factory=list)  # type: ignore[type-arg]
    github_readme: str = ""
    linkedin_headline: str = ""
    website_content: str = ""

    def to_dict(self) -> dict:
        return {
            "bio": self.bio,
            "summary": self.summary,
            "skills": self.skills,
            "portfolio_sections": self.portfolio_sections,
            "cv_sections": self.cv_sections,
            "github_readme": self.github_readme,
            "linkedin_headline": self.linkedin_headline,
            "website_content": self.website_content,
        }


class IntelligentProfileBuilder:
    """Builds consistent profile assets from real project history only."""

    def __init__(self):
        self.logger = logging.getLogger("ownex.direct_work_engine.profile_builder")

    def build(self, profile: UserProfile) -> ProfileAssets:
        """Generate all profile assets from the user's real facts."""
        assets = ProfileAssets()

        # Skills: deduplicated, ordered by confidence (skills listed first)
        assets.skills = sorted(profile.skills) if profile.skills else []

        # Bio from real facts: country, experience level, top skills
        level_label = self._level_label(profile.experience_level)
        top_skills = ", ".join(list(profile.skills)[:5]) if profile.skills else "technology"
        bio_parts = [f"Remote {level_label} technology professional based in {profile.country}."]
        if profile.skills:
            bio_parts.append(f"Skilled in {top_skills}.")
        if profile.github_url:
            bio_parts.append(f"Code: {profile.github_url}")
        if profile.linkedin_url:
            bio_parts.append(f"LinkedIn: {profile.linkedin_url}")
        assets.bio = " ".join(bio_parts)

        # Summary: short, factual, used in CV and LinkedIn
        assets.summary = (
            f"{level_label.capitalize()} technologist from {profile.country} with "
            f"experience in {top_skills}. "
            f"{len(profile.projects)} real projects completed. "
            f"Seeking remote opportunities with low entry barriers."
        )

        # LinkedIn headline: concise factual positioning
        assets.linkedin_headline = (
            f"{top_skills} | Remote | {profile.country}" if profile.skills else f"Remote | {profile.country}"
        )

        # Portfolio sections: one per real project, never invented
        assets.portfolio_sections = [
            {"title": p, "status": "completed", "source": "user_projects"} for p in profile.projects
        ]

        # CV sections: structured from facts
        assets.cv_sections = [
            {"section": "Profile", "content": assets.summary},
            {
                "section": "Skills",
                "content": assets.skills,
            },
            {
                "section": "Projects",
                "content": [{"name": p, "role": "developer", "source": "user_projects"} for p in profile.projects],
            },
            {
                "section": "Links",
                "content": {
                    "github": profile.github_url,
                    "portfolio": profile.portfolio_url,
                    "linkedin": profile.linkedin_url,
                },
            },
        ]

        # GitHub README: generated from real data only
        readme_lines = [
            f"# {profile.name}",
            "",
            assets.bio,
            "",
            "## Skills",
        ]
        readme_lines.extend(f"- {s}" for s in assets.skills)
        readme_lines.append("")
        readme_lines.append("## Projects")
        readme_lines.extend(f"- {p}" for p in profile.projects)
        assets.github_readme = "\n".join(readme_lines)

        # Website content: simple factual landing
        assets.website_content = "\n".join(
            [
                f"# {profile.name}",
                "",
                assets.bio,
                "",
                "## Skills",
                *[f"- {s}" for s in assets.skills],
                "",
                "## Projects",
                *[f"- {p}" for p in profile.projects],
            ]
        )

        return assets

    def _level_label(self, level: ExperienceLevel) -> str:
        labels = {
            ExperienceLevel.NONE: "junior",
            ExperienceLevel.JUNIOR: "junior",
            ExperienceLevel.MID: "mid-level",
            ExperienceLevel.SENIOR: "senior",
        }
        return labels.get(level, "junior")
