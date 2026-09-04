"""Skill Gap → Training Content Pipeline — Learn to earn.

Bridges the CareerEngine's skill gaps with curated, verifiable learning content.
Generates daily training plans with exercises, resources, and verification.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.learning.training_pipeline")

# ─── Training Content Types ───


@dataclass
class TrainingResource:
    """A single learning resource (video, article, lab, course)."""

    id: str
    title: str
    type: str  # video, article, lab, course, book, practice
    url: str
    provider: str  # youtube, coursera, portswigger, hackerone, etc.
    duration_minutes: int
    difficulty: str  # beginner, intermediate, advanced
    tags: list[str] = field(default_factory=list)
    verified: bool = False  # Community/OWNEX verified quality
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingExercise:
    """A hands-on exercise with verification."""

    id: str
    title: str
    description: str
    skill: str
    type: str  # ctflab, coding, reading, quiz, project
    estimated_minutes: int
    difficulty: str
    verification: dict[str, Any]  # How to verify completion
    resources: list[str] = field(default_factory=list)  # Resource IDs
    success_criteria: str = ""  # What counts as "done"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyTrainingPlan:
    """A day's training plan for a specific skill gap."""

    date: str
    skill: str
    category: str
    exercises: list[TrainingExercise]
    resources: list[TrainingResource]
    total_estimated_minutes: int
    priority: int  # 1=highest
    notes: str = ""


@dataclass
class SkillGapTrainingPlan:
    """Complete training plan for a skill gap over multiple days."""

    skill: str
    category: str
    current_level: str  # beginner, intermediate, advanced
    target_level: str
    daily_plans: list[DailyTrainingPlan]
    total_estimated_hours: float
    resources: list[TrainingResource]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ─── Resource Catalog (Curated) ───

# This is the SSOT for training resources. Expand as needed.
RESOURCE_CATALOG: dict[str, list[TrainingResource]] = {
    # Bug Bounty / Security
    "idor": [
        TrainingResource(
            id="idor-portswigger",
            title="IDOR Vulnerabilities - PortSwigger Web Security Academy",
            type="lab",
            url="https://portswigger.net/web-security/access-control/idor",
            provider="portswigger",
            duration_minutes=60,
            difficulty="intermediate",
            tags=["idor", "access-control", "bug-bounty"],
            verified=True,
        ),
        TrainingResource(
            id="idor-hackerone",
            title="IDOR Bug Bounty Tips - HackerOne",
            type="article",
            url="https://www.hackerone.com/blog/idor-vulnerabilities",
            provider="hackerone",
            duration_minutes=30,
            difficulty="beginner",
            tags=["idor", "bug-bounty", "tips"],
            verified=True,
        ),
    ],
    "xss": [
        TrainingResource(
            id="xss-portswigger",
            title="Cross-Site Scripting (XSS) - PortSwigger",
            type="lab",
            url="https://portswigger.net/web-security/cross-site-scripting",
            provider="portswigger",
            duration_minutes=120,
            difficulty="intermediate",
            tags=["xss", "web-security"],
            verified=True,
        ),
        TrainingResource(
            id="xss-hacker101",
            title="XSS - Hacker101",
            type="video",
            url="https://www.hacker101.com/sessions/xss",
            provider="hacker101",
            duration_minutes=45,
            difficulty="beginner",
            tags=["xss", "web-security"],
            verified=True,
        ),
    ],
    "sql-injection": [
        TrainingResource(
            id="sqli-portswigger",
            title="SQL Injection - PortSwigger",
            type="lab",
            url="https://portswigger.net/web-security/sql-injection",
            provider="portswigger",
            duration_minutes=120,
            difficulty="intermediate",
            tags=["sql-injection", "web-security"],
            verified=True,
        ),
        TrainingResource(
            id="sqli-hackerone",
            title="SQL Injection for Bug Bounty - HackerOne",
            type="article",
            url="https://www.hackerone.com/blog/sql-injection",
            provider="hackerone",
            duration_minutes=30,
            difficulty="intermediate",
            tags=["sql-injection", "bug-bounty"],
            verified=True,
        ),
    ],
    "ssrf": [
        TrainingResource(
            id="ssrf-portswigger",
            title="Server-Side Request Forgery (SSRF) - PortSwigger",
            type="lab",
            url="https://portswigger.net/web-security/ssrf",
            provider="portswigger",
            duration_minutes=90,
            difficulty="intermediate",
            tags=["ssrf", "web-security"],
            verified=True,
        ),
    ],
    "auth-bypass": [
        TrainingResource(
            id="auth-bypass-portswigger",
            title="Authentication Bypass - PortSwigger",
            type="lab",
            url="https://portswigger.net/web-security/authentication",
            provider="portswigger",
            duration_minutes=90,
            difficulty="intermediate",
            tags=["auth-bypass", "authentication"],
            verified=True,
        ),
    ],
    # Dev Skills
    "python": [
        TrainingResource(
            id="python-realpython",
            title="Python Tutorials - Real Python",
            type="article",
            url="https://realpython.com/",
            provider="realpython",
            duration_minutes=180,
            difficulty="beginner",
            tags=["python", "programming"],
            verified=True,
        ),
        TrainingResource(
            id="python-automate",
            title="Automate the Boring Stuff with Python",
            type="book",
            url="https://automatetheboringstuff.com/",
            provider="automatetheboringstuff",
            duration_minutes=600,
            difficulty="beginner",
            tags=["python", "automation"],
            verified=True,
        ),
    ],
    "go": [
        TrainingResource(
            id="go-tour",
            title="A Tour of Go",
            type="course",
            url="https://go.dev/tour/welcome/1",
            provider="golang.org",
            duration_minutes=120,
            difficulty="beginner",
            tags=["go", "programming"],
            verified=True,
        ),
        TrainingResource(
            id="go-by-example",
            title="Go by Example",
            type="article",
            url="https://gobyexample.com/",
            provider="gobyexample",
            duration_minutes=180,
            difficulty="beginner",
            tags=["go", "programming"],
            verified=True,
        ),
    ],
    "typescript": [
        TrainingResource(
            id="ts-handbook",
            title="TypeScript Handbook",
            type="article",
            url="https://www.typescriptlang.org/docs/handbook/intro.html",
            provider="typescriptlang",
            duration_minutes=120,
            difficulty="beginner",
            tags=["typescript", "programming"],
            verified=True,
        ),
    ],
    "docker": [
        TrainingResource(
            id="docker-docs",
            title="Docker Documentation",
            type="article",
            url="https://docs.docker.com/",
            provider="docker",
            duration_minutes=180,
            difficulty="beginner",
            tags=["docker", "containers"],
            verified=True,
        ),
    ],
    "kubernetes": [
        TrainingResource(
            id="k8s-docs",
            title="Kubernetes Documentation",
            type="article",
            url="https://kubernetes.io/docs/home/",
            provider="kubernetes",
            duration_minutes=240,
            difficulty="intermediate",
            tags=["kubernetes", "containers", "orchestration"],
            verified=True,
        ),
    ],
    "aws": [
        TrainingResource(
            id="aws-skill-builder",
            title="AWS Skill Builder",
            type="course",
            url="https://skillbuilder.aws/",
            provider="aws",
            duration_minutes=600,
            difficulty="beginner",
            tags=["aws", "cloud"],
            verified=True,
        ),
    ],
    # AI/ML
    "ml-fundamentals": [
        TrainingResource(
            id="ml-coursera-ng",
            title="Machine Learning - Andrew Ng (Coursera)",
            type="course",
            url="https://www.coursera.org/learn/machine-learning",
            provider="coursera",
            duration_minutes=3600,
            difficulty="beginner",
            tags=["ml", "ai"],
            verified=True,
        ),
        TrainingResource(
            id="ml-fastai",
            title="Practical Deep Learning for Coders - fast.ai",
            type="course",
            url="https://course.fast.ai/",
            provider="fastai",
            duration_minutes=2400,
            difficulty="intermediate",
            tags=["ml", "deep-learning", "pytorch"],
            verified=True,
        ),
    ],
    "llm-prompting": [
        TrainingResource(
            id="prompt-engineering-guide",
            title="Prompt Engineering Guide",
            type="article",
            url="https://github.com/dair-ai/Prompt-Engineering-Guide",
            provider="github",
            duration_minutes=120,
            difficulty="beginner",
            tags=["llm", "prompting", "ai"],
            verified=True,
        ),
    ],
    # Bug Bounty Platforms
    "hackerone": [
        TrainingResource(
            id="h1-docs",
            title="HackerOne Documentation",
            type="article",
            url="https://docs.hackerone.com/",
            provider="hackerone",
            duration_minutes=60,
            difficulty="beginner",
            tags=["hackerone", "bug-bounty", "platform"],
            verified=True,
        ),
    ],
    "bugcrowd": [
        TrainingResource(
            id="bc-docs",
            title="Bugcrowd Documentation",
            type="article",
            url="https://docs.bugcrowd.com/",
            provider="bugcrowd",
            duration_minutes=60,
            difficulty="beginner",
            tags=["bugcrowd", "bug-bounty", "platform"],
            verified=True,
        ),
    ],
}


# ─── Exercise Templates ───

EXERCISE_TEMPLATES: dict[str, list[TrainingExercise]] = {
    "idor": [
        TrainingExercise(
            id="idor-lab-1",
            title="IDOR Lab - Basic Object Reference",
            description="Complete the PortSwigger IDOR lab: Basic object reference manipulation",
            skill="idor",
            type="ctflab",
            estimated_minutes=45,
            difficulty="intermediate",
            verification={
                "type": "lab_completion",
                "platform": "portswigger",
                "lab_url": "https://portswigger.net/web-security/access-control/idor/lab-object-reference",
            },
            success_criteria="Lab shows 'Solved' status",
            resources=["idor-portswigger"],
        ),
        TrainingExercise(
            id="idor-lab-2",
            title="IDOR Lab - UUID/GUID Manipulation",
            description="Complete the PortSwigger IDOR lab: UUID/GUID manipulation",
            skill="idor",
            type="ctflab",
            estimated_minutes=60,
            difficulty="intermediate",
            verification={
                "type": "lab_completion",
                "platform": "portswigger",
                "lab_url": "https://portswigger.net/web-security/access-control/idor/lab-uuid-manipulation",
            },
            success_criteria="Lab shows 'Solved' status",
            resources=["idor-portswigger"],
        ),
        TrainingExercise(
            id="idor-practice-1",
            title="Practice: Find IDOR in Demo App",
            description="Deploy the OWASP WebGoat locally and find the IDOR in the 'Access Control' section",
            skill="idor",
            type="ctflab",
            estimated_minutes=90,
            difficulty="intermediate",
            verification={
                "type": "screenshot",
                "description": "Screenshot showing successful IDOR exploit in WebGoat",
            },
            success_criteria="Screenshot shows successful unauthorized access via IDOR",
            resources=["idor-portswigger", "idor-hackerone"],
        ),
    ],
    "xss": [
        TrainingExercise(
            id="xss-lab-1",
            title="Reflected XSS Lab",
            description="Complete the PortSwigger Reflected XSS lab",
            skill="xss",
            type="ctflab",
            estimated_minutes=45,
            difficulty="beginner",
            verification={
                "type": "lab_completion",
                "platform": "portswigger",
                "lab_url": "https://portswigger.net/web-security/cross-site-scripting/reflected/lab-basic-reflected-xss",
            },
            success_criteria="Lab shows 'Solved' status",
            resources=["xss-portswigger"],
        ),
        TrainingExercise(
            id="xss-lab-2",
            title="Stored XSS Lab",
            description="Complete the PortSwigger Stored XSS lab",
            skill="xss",
            type="ctflab",
            estimated_minutes=60,
            difficulty="intermediate",
            verification={
                "type": "lab_completion",
                "platform": "portswigger",
                "lab_url": "https://portswigger.net/web-security/cross-site-scripting/stored/lab-stored-xss-basic",
            },
            success_criteria="Lab shows 'Solved' status",
            resources=["xss-portswigger"],
        ),
    ],
    "python": [
        TrainingExercise(
            id="python-script-1",
            title="Write a Port Scanner in Python",
            description="Write a basic TCP port scanner using Python sockets",
            skill="python",
            type="coding",
            estimated_minutes=60,
            difficulty="beginner",
            verification={
                "type": "code_review",
                "criteria": "Script scans ports 1-1000 on localhost and outputs open ports",
            },
            success_criteria="Script runs and outputs open ports correctly",
            resources=["python-realpython"],
        ),
        TrainingExercise(
            id="python-script-2",
            title="Automate Bug Bounty Recon",
            description="Write a Python script that automates subdomain enumeration using crt.sh",
            skill="python",
            type="coding",
            estimated_minutes=90,
            difficulty="intermediate",
            verification={
                "type": "code_review",
                "criteria": "Script takes domain as input, queries crt.sh, outputs unique subdomains",
            },
            success_criteria="Script runs and finds subdomains for a test domain",
            resources=["python-realpython", "python-automate"],
        ),
    ],
}


# ─── Training Pipeline Engine ───


class TrainingPipeline:
    """Generates training plans from skill gaps."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        base = os.environ.get("OWNEX_DATA_DIR")
        self.data_dir = (
            Path(data_dir)
            if data_dir
            else (Path(base) if base else Path(__file__).resolve().parents[3] / "data") / "training"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.training_file = self.data_dir / "training_plans.json"
        self.progress_file = self.data_dir / "training_progress.json"

    def generate_plan_for_gap(
        self,
        skill: str,
        category: str,
        current_level: str = "beginner",
        target_level: str = "intermediate",
        available_hours_per_week: float = 10.0,
    ) -> SkillGapTrainingPlan:
        """Generate a complete training plan for a skill gap."""

        # Get resources for this skill
        resources = RESOURCE_CATALOG.get(skill, [])
        if not resources:
            # Fallback: generic resources
            resources = [
                TrainingResource(
                    id=f"{skill}-generic",
                    title=f"Learn {skill.title()}",
                    type="article",
                    url=f"https://www.google.com/search?q=learn+{skill}",
                    provider="web",
                    duration_minutes=120,
                    difficulty=current_level,
                    tags=[skill],
                )
            ]

        # Get exercises for this skill
        exercises = EXERCISE_TEMPLATES.get(skill, [])

        # Filter by level
        level_order = {"beginner": 0, "intermediate": 1, "advanced": 2}
        current_idx = level_order.get(current_level, 0)
        target_idx = level_order.get(target_level, 1)

        # Build daily plans
        daily_plans: list[DailyTrainingPlan] = []
        days_needed = max(1, (target_idx - current_idx + 1) * 3)  # ~3 days per level step

        for day in range(days_needed):
            day_exercises = []
            day_resources = []

            # Assign exercises for this day
            if exercises:
                ex_idx = day % len(exercises)
                day_exercises.append(exercises[ex_idx])

            # Assign resources for this day
            res_idx = day % len(resources) if resources else 0
            if resources:
                day_resources.append(resources[res_idx])

            total_minutes = sum(e.estimated_minutes for e in day_exercises)
            total_minutes += sum(r.duration_minutes for r in day_resources)

            daily_plans.append(
                DailyTrainingPlan(
                    date=(datetime.now(UTC)).strftime("%Y-%m-%d"),
                    skill=skill,
                    category=category,
                    exercises=day_exercises,
                    resources=day_resources,
                    total_estimated_minutes=total_minutes,
                    priority=1,
                    notes=f"Day {day + 1} of {skill} training",
                )
            )

        total_hours = sum(p.total_estimated_minutes for p in daily_plans) / 60

        return SkillGapTrainingPlan(
            skill=skill,
            category=category,
            current_level=current_level,
            target_level=target_level,
            daily_plans=daily_plans,
            total_estimated_hours=round(total_hours, 1),
            resources=resources,
        )

    def get_plan(self, skill: str, category: str) -> SkillGapTrainingPlan | None:
        """Load a saved training plan."""
        try:
            with open(self.training_file, encoding="utf-8") as f:
                data = json.load(f)
            key = f"{category}:{skill}"
            if key in data:
                return SkillGapTrainingPlan(**data[key])
        except Exception:
            pass
        return None

    def save_plan(self, plan: SkillGapTrainingPlan) -> None:
        """Save a training plan."""
        try:
            data = {}
            if self.training_file.exists():
                with open(self.training_file, encoding="utf-8") as f:
                    data = json.load(f)
            key = f"{plan.category}:{plan.skill}"
            plan.updated_at = datetime.now(UTC).isoformat()
            data[key] = plan.__dict__
            with open(self.training_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning(f"Could not save training plan: {exc}")

    def record_completion(self, skill: str, exercise_id: str, success: bool, notes: str = "") -> None:
        """Record exercise completion for progress tracking."""
        try:
            progress = {}
            if self.progress_file.exists():
                with open(self.progress_file, encoding="utf-8") as f:
                    progress = json.load(f)
            key = skill
            if key not in progress:
                progress[key] = {"completed": [], "failed": [], "total_time": 0}
            entry = {
                "exercise_id": exercise_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "success": success,
                "notes": notes,
            }
            if success:
                progress[key]["completed"].append(entry)
            else:
                progress[key]["failed"].append(entry)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"Could not record completion: {exc}")

    def get_progress(self, skill: str) -> dict[str, Any]:
        """Get progress for a skill."""
        try:
            with open(self.progress_file, encoding="utf-8") as f:
                return json.load(f).get(skill, {"completed": [], "failed": [], "total_time": 0})
        except Exception:
            return {"completed": [], "failed": [], "total_time": 0}


# Global instance
_training_pipeline: TrainingPipeline | None = None


def get_training_pipeline() -> TrainingPipeline:
    global _training_pipeline
    if _training_pipeline is None:
        _training_pipeline = TrainingPipeline()
    return _training_pipeline


# ─── API Functions ───


def generate_training_plan(
    skill: str,
    category: str,
    current_level: str = "beginner",
    target_level: str = "intermediate",
    hours_per_week: float = 10.0,
) -> dict[str, Any]:
    """Generate a training plan for a skill gap."""
    pipeline = get_training_pipeline()
    plan = pipeline.generate_plan_for_gap(skill, category, current_level, target_level)
    pipeline.save_plan(plan)
    return plan.__dict__


def get_training_plan(skill: str, category: str) -> dict[str, Any] | None:
    """Get a saved training plan."""
    pipeline = get_training_pipeline()
    plan = pipeline.get_plan(skill, category)
    return plan.__dict__ if plan else None


def record_training_completion(skill: str, exercise_id: str, success: bool, notes: str = "") -> dict[str, Any]:
    """Record exercise completion."""
    pipeline = get_training_pipeline()
    pipeline.record_completion(skill, exercise_id, success, notes)
    return {"success": True}


def get_training_progress(skill: str) -> dict[str, Any]:
    """Get training progress for a skill."""
    pipeline = get_training_pipeline()
    return pipeline.get_progress(skill)


def list_resources(skill: str | None = None) -> dict[str, list[dict]]:
    """List available training resources."""
    if skill:
        return {skill: [r.__dict__ for r in RESOURCE_CATALOG.get(skill, [])]}
    return {k: [r.__dict__ for r in v] for k, v in RESOURCE_CATALOG.items()}


def list_exercises(skill: str | None = None) -> dict[str, list[dict]]:
    """List available training exercises."""
    if skill:
        return {skill: [e.__dict__ for e in EXERCISE_TEMPLATES.get(skill, [])]}
    return {k: [e.__dict__ for e in v] for k, v in EXERCISE_TEMPLATES.items()}
