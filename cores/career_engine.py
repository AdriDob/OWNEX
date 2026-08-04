"""Career Engine — continuous learning, skill-gap detection, roadmap, interview prep.

Learns continuously what the user needs: detects missing skills per category,
generates a prioritized learning roadmap, prepares interview questions, and
produces a daily training plan. Everything derives from the real UserProfile —
never invents information.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from cores.direct_work_engine.models import OpportunityCategory, UserProfile

logger = logging.getLogger("ownex.career_engine")

# Required skills per category (curated, realistic market requirements).
CATEGORY_REQUIRED_SKILLS: dict[OpportunityCategory, set[str]] = {
    OpportunityCategory.BUG_BOUNTY: {"web", "http", "burp_suite", "owasp", "recon"},
    OpportunityCategory.DEV_BOUNTY: {"python", "git", "web", "problem_solving"},
    OpportunityCategory.SECURITY_RESEARCH: {"web", "http", "burp_suite", "owasp", "exploit_dev"},
    OpportunityCategory.OSS_BOUNTIES: {"git", "open_source", "code_review"},
    OpportunityCategory.OPEN_SOURCE: {"git", "open_source", "code_review"},
    OpportunityCategory.SOFTWARE_ENGINEERING: {"python", "git", "algorithms", "system_design"},
    OpportunityCategory.BACKEND: {"python", "sql", "rest_api", "docker", "git"},
    OpportunityCategory.FRONTEND: {"javascript", "html", "css", "react", "git"},
    OpportunityCategory.FULL_STACK: {"python", "javascript", "sql", "rest_api", "docker", "git"},
    OpportunityCategory.DEVOPS: {"linux", "docker", "kubernetes", "ci_cd", "terraform", "git"},
    OpportunityCategory.INFRASTRUCTURE: {"linux", "docker", "kubernetes", "networking", "terraform"},
    OpportunityCategory.CLOUD: {"aws", "gcp", "azure", "terraform", "docker", "linux"},
    OpportunityCategory.AI_ENGINEERING: {"python", "llm", "prompting", "rag", "ml"},
    OpportunityCategory.ML_ENGINEERING: {"python", "ml", "pandas", "sklearn", "pytorch"},
    OpportunityCategory.LLM_ENGINEERING: {"python", "llm", "prompting", "rag", "transformers"},
    OpportunityCategory.PROMPT_ENGINEERING: {"prompting", "llm", "rag", "python"},
    OpportunityCategory.BROWSER_AUTOMATION: {"python", "playwright", "selenium", "scraping"},
    OpportunityCategory.QA_AUTOMATION: {"python", "pytest", "selenium", "playwright", "ci_cd"},
    OpportunityCategory.DATA_ENGINEERING: {"python", "sql", "pandas", "spark", "airflow"},
    OpportunityCategory.WEB_SCRAPING: {"python", "scraping", "playwright", "html", "http"},
    OpportunityCategory.TECHNICAL_WRITING: {"english", "markdown", "technical_writing"},
    OpportunityCategory.DOCUMENTATION: {"english", "markdown", "technical_writing"},
    OpportunityCategory.AI_EVALUATION: {"llm", "prompting", "english", "python"},
    OpportunityCategory.DATA_ANNOTATION: {"english", "attention_to_detail"},
    OpportunityCategory.SYNTHETIC_DATA: {"python", "data_generation", "english"},
    OpportunityCategory.CODE_REVIEW: {"git", "code_review", "security"},
    OpportunityCategory.GAME_DEVELOPMENT: {"unity", "csharp", "unreal", "cpp", "godot", "gameplay", "git"},
    OpportunityCategory.REVERSE_ENGINEERING: {"assembly", "debugging", "disassembly", "memory"},
    OpportunityCategory.MALWARE_ANALYSIS: {"assembly", "debugging", "sandbox", "forensics"},
    OpportunityCategory.EMBEDDED: {"c", "cplusplus", "microcontrollers", "rtos"},
    OpportunityCategory.IOT: {"c", "python", "mqtt", "networking", "microcontrollers"},
    OpportunityCategory.MOBILE_DEVELOPMENT: {"kotlin", "swift", "flutter", "android", "ios"},
    OpportunityCategory.DESKTOP_DEVELOPMENT: {"python", "qt", "tauri", "electron"},
    OpportunityCategory.API_DEVELOPMENT: {"rest_api", "openapi", "python", "sql"},
    OpportunityCategory.SDK_DEVELOPMENT: {"rest_api", "python", "javascript", "documentation"},
    OpportunityCategory.BLOCKCHAIN_DEVELOPMENT: {"solidity", "web3", "ethereum", "cryptography"},
    OpportunityCategory.SMART_CONTRACTS: {"solidity", "ethereum", "hardhat", "security"},
    OpportunityCategory.COMPETITIONS: {"algorithms", "problem_solving", "data_structures", "git"},
}

# Common interview questions per category (realistic, official-style).
INTERVIEW_QUESTIONS: dict[OpportunityCategory, list[str]] = {
    OpportunityCategory.BUG_BOUNTY: [
        "Explain IDOR and how you would test for it.",
        "Walk through your recon methodology for a new scope.",
        "How do you differentiate a real vulnerability from a false positive?",
    ],
    OpportunityCategory.BACKEND: [
        "Design a rate limiter (system design).",
        "Explain the CAP theorem with examples.",
        "How do you handle database migrations safely?",
    ],
    OpportunityCategory.FRONTEND: [
        "Explain React's reconciliation algorithm.",
        "How do you optimize a slow page load?",
        "Describe a11y best practices you apply by default.",
    ],
    OpportunityCategory.FULL_STACK: [
        "Walk me through the full lifecycle of an API request.",
        "How do you secure a REST API end to end?",
        "Describe your approach to designing a database schema.",
    ],
    OpportunityCategory.DEVOPS: [
        "Explain how Docker layers work.",
        "Design a CI/CD pipeline for a monorepo.",
        "How do you handle secrets management?",
    ],
    OpportunityCategory.CLOUD: [
        "Explain the difference between availability zones and regions.",
        "Design a cost-optimized autoscaling setup.",
        "How do you secure a public S3 bucket?",
    ],
    OpportunityCategory.AI_ENGINEERING: [
        "Explain RAG and its failure modes.",
        "How do you evaluate an LLM output?",
        "Describe a prompt-injection defense strategy.",
    ],
    OpportunityCategory.ML_ENGINEERING: [
        "Explain bias-variance tradeoff.",
        "How do you detect data leakage in a pipeline?",
        "Describe model drift and how you monitor it.",
    ],
    OpportunityCategory.LLM_ENGINEERING: [
        "Explain temperature, top-p, and their tradeoffs.",
        "How would you build a knowledge base assistant?",
        "What are the main LLM security risks?",
    ],
    OpportunityCategory.PROMPT_ENGINEERING: [
        "Design a prompt to extract structured data reliably.",
        "How do you reduce hallucination in few-shot prompts?",
    ],
    OpportunityCategory.BROWSER_AUTOMATION: [
        "How do you handle dynamic content in scraping?",
        "Design a robust selector strategy.",
        "How do you bypass anti-bot measures ethically?",
    ],
    OpportunityCategory.QA_AUTOMATION: [
        "How do you design a flaky-test prevention strategy?",
        "Explain the testing pyramid.",
        "How do you test async UIs deterministically?",
    ],
    OpportunityCategory.DATA_ENGINEERING: [
        "Explain the difference between ELT and ETL.",
        "How do you handle late-arriving data?",
        "Design a data pipeline that scales.",
    ],
    OpportunityCategory.WEB_SCRAPING: [
        "How do you respect robots.txt while scraping at scale?",
        "Design a retry strategy for flaky sources.",
    ],
    OpportunityCategory.GAME_DEVELOPMENT: [
        "Explain the game loop and fixed timestep.",
        "How do you optimize draw calls in Unity?",
        "Describe how you handle network replication (client prediction).",
    ],
}

# Daily training focus areas per category (practice drills).
DAILY_TRAINING: dict[OpportunityCategory, list[str]] = {
    OpportunityCategory.BUG_BOUNTY: ["1 lab on OWASP Top 10", "recon on 1 target", "write 1 report draft"],
    OpportunityCategory.BACKEND: ["1 API design exercise", "1 SQL query kata", "1 code review"],
    OpportunityCategory.FRONTEND: ["1 component build", "1 a11y audit", "1 perf profile"],
    OpportunityCategory.FULL_STACK: ["1 full feature", "1 API + UI wiring", "1 schema design"],
    OpportunityCategory.DEVOPS: ["1 Dockerfile optimization", "1 CI pipeline tweak", "1 infra diagram"],
    OpportunityCategory.AI_ENGINEERING: ["1 RAG prototype", "1 prompt eval batch", "1 LLM security test"],
    OpportunityCategory.ML_ENGINEERING: ["1 model training", "1 feature engineering pass", "1 drift check"],
    OpportunityCategory.GAME_DEVELOPMENT: ["1 gameplay mechanic", "1 optimization pass", "1 build test"],
    OpportunityCategory.COMPETITIONS: ["1 timed algorithm kata", "1 contest problem recap", "1 data structure drill"],
    OpportunityCategory.REVERSE_ENGINEERING: ["1 crackme", "1 disassembly pass", "1 debugger session"],
    OpportunityCategory.MALWARE_ANALYSIS: ["1 sample triage", "1 sandbox behavior pass", "1 YARA rule"],
}


@dataclass(slots=True)
class SkillGap:
    skill: str
    category: OpportunityCategory
    priority: str = "medium"  # high | medium | low


@dataclass(slots=True)
class CareerRoadmap:
    """Prioritized learning roadmap derived from skill gaps."""

    items: list[SkillGap] = field(default_factory=list)
    total_gaps: int = 0
    generated_at: str = ""

    @property
    def high_priority(self) -> list[SkillGap]:
        return [g for g in self.items if g.priority == "high"]


@dataclass(slots=True)
class DailyTrainingPlan:
    focus_skills: list[str] = field(default_factory=list)
    drills: list[str] = field(default_factory=list)
    interview_questions: list[str] = field(default_factory=list)
    estimated_minutes: int = 30
    date: str = ""


class CareerEngine:
    """Detects gaps, builds roadmaps, prepares interviews, and schedules daily training."""

    def __init__(self):
        self.logger = logging.getLogger("ownex.career_engine")

    def detect_skill_gaps(
        self, profile: UserProfile, categories: list[OpportunityCategory] | None = None
    ) -> list[SkillGap]:
        """Compare user skills against required skills per category."""
        categories = categories or list(CATEGORY_REQUIRED_SKILLS.keys())
        user_skills = {s.lower() for s in profile.skills}
        gaps: list[SkillGap] = []

        for category in categories:
            required = CATEGORY_REQUIRED_SKILLS.get(category, set())
            for skill in required:
                if skill.lower() not in user_skills:
                    gaps.append(SkillGap(skill=skill, category=category))

        # Priority: skills shared across many categories rank high.
        if gaps:
            from collections import Counter

            counts = Counter(g.skill for g in gaps)
            for gap in gaps:
                gap.priority = "high" if counts[gap.skill] >= 2 else "medium"

        return gaps

    def build_roadmap(self, profile: UserProfile, categories: list[OpportunityCategory] | None = None) -> CareerRoadmap:
        """Generate a prioritized learning roadmap."""
        gaps = self.detect_skill_gaps(profile, categories)
        # High-priority gaps first, then by category frequency.
        gaps.sort(key=lambda g: (0 if g.priority == "high" else 1, g.skill))
        return CareerRoadmap(items=gaps, total_gaps=len(gaps), generated_at=datetime.now(UTC).isoformat())

    def prepare_interview(self, category: OpportunityCategory) -> list[str]:
        """Return curated interview questions for a category."""
        return INTERVIEW_QUESTIONS.get(category, [])

    def build_daily_training(
        self, profile: UserProfile, categories: list[OpportunityCategory] | None = None
    ) -> DailyTrainingPlan:
        """Build today's training plan from the top skill gaps."""
        roadmap = self.build_roadmap(profile, categories)
        top_gaps = roadmap.items[:3]

        drills: list[str] = []
        focus_skills: list[str] = []
        interview_questions: list[str] = []

        for gap in top_gaps:
            focus_skills.append(gap.skill)
            drills.extend(DAILY_TRAINING.get(gap.category, [])[:1])
            interview_questions.extend(self.prepare_interview(gap.category)[:1])

        return DailyTrainingPlan(
            focus_skills=focus_skills,
            drills=list(dict.fromkeys(drills))[:5],
            interview_questions=list(dict.fromkeys(interview_questions))[:3],
            date=datetime.now(UTC).date().isoformat(),
        )

    def analyze_profile(self, profile: UserProfile) -> dict:
        """Produce a full career analysis summary."""
        roadmap = self.build_roadmap(profile)
        return {
            "name": profile.name,
            "skills_count": len(profile.skills),
            "skill_gaps": roadmap.total_gaps,
            "high_priority_gaps": [g.skill for g in roadmap.high_priority],
            "top_categories": sorted(
                {(g.category.value, sum(1 for x in roadmap.items if x.category == g.category)) for g in roadmap.items},
                key=lambda pair: pair[1],
                reverse=True,
            )[:5],
            "generated_at": roadmap.generated_at,
        }


def register_capabilities() -> None:
    """Register Career Engine capabilities in the CapabilityRegistry (auto-integration)."""
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        reg.unregister("career_analysis", "career_engine")
        reg.register(
            "career_analysis",
            "career_engine",
            {
                "capabilities": [
                    "detect_skill_gaps",
                    "build_roadmap",
                    "prepare_interview",
                    "build_daily_training",
                    "analyze_profile",
                ]
            },
            description="Continuous learning, skill-gap detection, roadmap, interview prep, daily training",
        )
        logger.info("Career Engine registered in CapabilityRegistry")
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not register Career Engine in CapabilityRegistry: %s", exc)


def register_all_capabilities() -> None:
    """Register all OWNEX modules in the CapabilityRegistry (idempotent)."""
    from cores.direct_work_engine.engine import register_capabilities as register_dwe

    register_dwe()
    register_capabilities()
