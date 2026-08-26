"""Job Search Integration — ai-job-search patterns integrated into OWNEX DWE.

Extracts the best patterns from MadsLorentzen/ai-job-search (35.3k stars, MIT)
and integrates them into OWNEX's Direct Work Engine for traditional employment
and freelance applications alongside bug bounty and dev bounties.

Patterns integrated (spec: FINAL RELEASE + user request):
1. Fit Evaluation Framework → score jobs against user profile (5 dimensions)
2. Application Tracking → track from submitted to outcome
3. CV Generation Bridge → Profile Kit generates platform-specific application text

NOT duplicated from OWNEX: opportunity discovery (already has 139 sources),
EV scoring (EconomicEngine), payment tracking (RevenueTracker).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.job_search_integration")


class ApplicationStatus(StrEnum):
    DISCOVERED = "discovered"
    EVALUATED = "evaluated"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER_RECEIVED = "offer_received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"


class FitDimension(StrEnum):
    """5-dimension fit evaluation (adapted from ai-job-search §04)."""

    SKILLS_MATCH = "skills_match"  # overlap between your skills and requirements
    EXPERIENCE_LEVEL = "experience_level"  # seniority alignment
    COMPENSATION = "compensation"  # pay vs expectations
    LOCATION_REMOTE = "location_remote"  # remote/geo compatibility
    CAREER_GROWTH = "career_growth"  # learning + advancement potential


# Weights per dimension (sum = 1.0), adapted for Argentina-based remote workers
_FIT_WEIGHTS = {
    FitDimension.SKILLS_MATCH: 0.30,
    FitDimension.EXPERIENCE_LEVEL: 0.20,
    FitDimension.COMPENSATION: 0.25,
    FitDimension.LOCATION_REMOTE: 0.15,
    FitDimension.CAREER_GROWTH: 0.10,
}


@dataclass(slots=True)
class JobFitEvaluation:
    """Result of evaluating a job posting against the user's profile."""

    opportunity_id: str
    title: str
    platform: str
    overall_fit_score: float  # 0–100
    dimensions: dict[str, float]  # per-dimension scores 0–100
    strengths: list[str]
    gaps: list[str]
    recommendation: str  # APPLY / CONSIDER / SKIP
    reasoning: str
    evaluated_at: str


@dataclass(slots=True)
class TrackedApplication:
    """A tracked job application (from discovered to outcome)."""

    opportunity_id: str
    title: str
    company: str
    platform: str
    url: str
    status: str = ApplicationStatus.DISCOVERED.value
    fit_score: float = 0.0
    applied_at: str | None = None
    last_update: str | None = None
    notes: str = ""
    salary_range: str = ""
    interview_stage: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class JobSearchIntegration:
    """Integrates ai-job-search patterns into OWNEX DWE."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or Path(os.getenv("OWNEX_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
        self._apps_path = self._data_dir / "job_applications.json"

    # ── Fit Evaluation ──

    def evaluate_fit(
        self,
        opportunity: dict[str, Any],
        profile: dict[str, Any],
    ) -> JobFitEvaluation:
        """Evaluate how well a job matches the user's profile.

        Uses the 5-dimension framework from ai-job-search adapted
        for remote-first Argentina-based workers.
        """
        opp_skills = set(s.lower() for s in opportunity.get("skills", []))
        profile_skills = set(s.lower() for s in profile.get("skills", []))

        # Skills match
        if opp_skills:
            overlap = opp_skills & profile_skills
            skills_score = len(overlap) / len(opp_skills) * 100
        else:
            skills_score = 50.0

        # Experience level match
        required_exp = opportunity.get("experience_level", "").lower()
        user_exp = profile.get("experience_level", "mid").lower()
        exp_order = {"none": 0, "entry": 1, "junior": 1, "mid": 2, "senior": 3}
        req_level = exp_order.get(required_exp, 2)
        usr_level = exp_order.get(user_exp, 2)
        if usr_level >= req_level:
            exp_score = min(100.0, 80.0 + (usr_level - req_level) * 10)
        else:
            gap = req_level - usr_level
            exp_score = max(20.0, 80.0 - gap * 30)

        # Compensation
        reward = opportunity.get("payment", 0)
        comp_score = min(100.0, max(0.0, (reward / 3000) * 100)) if reward else 50.0

        # Location/remote
        remote = opportunity.get("remote", True)
        country = opportunity.get("country", "")
        geo_score = 100.0 if remote else (60.0 if country.lower() == "argentina" else 30.0)

        # Career growth (heuristic based on category)
        growth_cats = {"ai_engineering", "llm_engineering", "security_research", "ml_engineering"}
        category = opportunity.get("category", "")
        growth_score = 80.0 if category in growth_cats else 50.0

        dims = {
            FitDimension.SKILLS_MATCH.value: round(skills_score, 1),
            FitDimension.EXPERIENCE_LEVEL.value: round(exp_score, 1),
            FitDimension.COMPENSATION.value: round(comp_score, 1),
            FitDimension.LOCATION_REMOTE.value: round(geo_score, 1),
            FitDimension.CAREER_GROWTH.value: round(growth_score, 1),
        }

        overall = sum(dims[d] * _FIT_WEIGHTS[FitDimension(d)] for d in dims)

        strengths = []
        gaps = []
        if skills_score >= 70:
            strengths.append(f"Strong skill overlap ({len(opp_skills & profile_skills)}/{len(opp_skills)} matched)")
        elif skills_score < 40:
            missing = opp_skills - profile_skills
            if missing:
                gaps.append(f"Missing skills: {', '.join(sorted(missing)[:5])}")

        if comp_score >= 70:
            strengths.append(f"Compensation ${reward:,.0f} above average")
        elif comp_score < 40 and reward:
            gaps.append(f"Pay ${reward:,.0f} below target range")

        if geo_score >= 80:
            strengths.append("Fully remote / Argentina compatible")
        elif not remote:
            gaps.append("Not remote")

        if overall >= 75:
            rec = "APPLY"
        elif overall >= 55:
            rec = "CONSIDER"
        else:
            rec = "SKIP"

        return JobFitEvaluation(
            opportunity_id=str(opportunity.get("id", "")),
            title=opportunity.get("title", ""),
            platform=opportunity.get("platform", ""),
            overall_fit_score=round(overall, 1),
            dimensions=dims,
            strengths=strengths,
            gaps=gaps,
            recommendation=rec,
            reasoning=f"Skills {skills_score:.0f}% · Exp {exp_score:.0f}% · Comp {comp_score:.0f}% · Remote {geo_score:.0f}%",
            evaluated_at=datetime.now(UTC).isoformat(),
        )

    # ── Application Tracking ──

    def track_application(self, evaluation: JobFitEvaluation, url: str = "") -> TrackedApplication:
        """Add an application to the tracker."""
        apps = self._load_apps()
        app = TrackedApplication(
            opportunity_id=evaluation.opportunity_id,
            title=evaluation.title,
            company="",
            platform=evaluation.platform,
            url=url,
            status=ApplicationStatus.APPLIED.value,
            fit_score=evaluation.overall_fit_score,
            applied_at=datetime.now(UTC).isoformat(),
            last_update=datetime.now(UTC).isoformat(),
        )
        apps.append(app.to_dict())
        self._save_apps(apps)
        return app

    def update_status(self, opportunity_id: str, new_status: str, notes: str = "") -> bool:
        apps = self._load_apps()
        for a in apps:
            if a["opportunity_id"] == opportunity_id:
                a["status"] = new_status
                a["last_update"] = datetime.now(UTC).isoformat()
                if notes:
                    a["notes"] = notes
                if new_status == ApplicationStatus.INTERVIEWING.value:
                    a["interview_stage"] += 1
                self._save_apps(apps)
                return True
        return False

    def get_pipeline(self) -> dict[str, list[dict]]:
        """Get all applications grouped by status."""
        apps = self._load_apps()
        by_status: dict[str, list] = {}
        for a in apps:
            by_status.setdefault(a["status"], []).append(a)
        return by_status

    def get_stats(self) -> dict:
        apps = self._load_apps()
        total = len(apps)
        if not total:
            return {"total": 0}
        statuses = {}
        for a in apps:
            statuses[a["status"]] = statuses.get(a["status"], 0) + 1
        interviewed = sum(v for k, v in statuses.items() if "interview" in k or "offer" in k or "accepted" in k)
        rejected = statuses.get(ApplicationStatus.REJECTED.value, 0)
        return {
            "total": total,
            "by_status": statuses,
            "interview_rate": round(interviewed / max(total, 1), 2),
            "rejection_rate": round(rejected / max(total, 1), 2),
        }

    # ── Persistence ──

    def _load_apps(self) -> list[dict]:
        if not self._apps_path.exists():
            return []
        try:
            return json.loads(self._apps_path.read_text())
        except Exception:
            return []

    def _save_apps(self, apps: list[dict]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._apps_path.write_text(json.dumps(apps, indent=2, ensure_ascii=False))


# ── Singleton ──

_integration: JobSearchIntegration | None = None


def get_job_search_integration() -> JobSearchIntegration:
    global _integration
    if _integration is None:
        _integration = JobSearchIntegration()
    return _integration
