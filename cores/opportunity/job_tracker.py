"""Remote job tracker — save ranked jobs, track application pipeline (v12 §9.3).

Statuses: saved → analyzed → prepared → approved → applied → accepted/rejected/withdrawn.
Human approval is mandatory before 'applied' (no auto-submission ever).
Store: JSON file under OWNEX data dir (same convention as other connection stores).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VALID_STATUSES = {"saved", "analyzed", "prepared", "approved", "applied", "accepted", "rejected", "withdrawn"}
TRANSITIONS = {
    "saved": {"analyzed", "withdrawn"},
    "analyzed": {"prepared", "withdrawn"},
    "prepared": {"approved", "withdrawn"},
    "approved": {"applied", "withdrawn"},
    "applied": {"accepted", "rejected", "withdrawn"},
    "accepted": set(),
    "rejected": set(),
    "withdrawn": set(),
}


def _store_path() -> Path:
    from cores.connections.importer import get_config

    return Path(get_config().data_dir) / "remote_jobs" / "tracker.json"


def _load() -> dict[str, Any]:
    p = _store_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.warning("remote_jobs tracker unreadable, starting fresh")
    return {"jobs": {}}


def _save(state: dict[str, Any]) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def save_job(job: dict[str, Any], match: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist a job + its matcher result. Idempotent by URL (or title+company)."""
    state = _load()
    key = str(job.get("url") or f"{job.get('title')}|{job.get('company')}")
    entry = state["jobs"].get(key)
    if entry is None:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "job": job,
            "match": match or job.get("match"),
            "status": "saved",
            "history": [{"at": datetime.now(UTC).isoformat(), "to": "saved"}],
            "created_at": datetime.now(UTC).isoformat(),
        }
        state["jobs"][key] = entry
        _save(state)
    return entry


def list_jobs(status: str | None = None) -> list[dict[str, Any]]:
    jobs = list(_load()["jobs"].values())
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    jobs.sort(key=lambda j: (j.get("match") or {}).get("score", 0), reverse=True)
    return jobs


def transition(job_id: str, to_status: str, note: str = "") -> dict[str, Any]:
    """Advance a saved job through the pipeline. Enforces valid transitions."""
    if to_status not in VALID_STATUSES:
        raise ValueError(f"invalid status {to_status!r}; valid: {sorted(VALID_STATUSES)}")
    state = _load()
    for entry in state["jobs"].values():
        if entry["id"] != job_id:
            continue
        frm = entry["status"]
        if to_status != frm and to_status not in TRANSITIONS.get(frm, set()):
            raise ValueError(f"cannot transition {frm} → {to_status}")
        entry["status"] = to_status
        entry["history"].append({"at": datetime.now(UTC).isoformat(), "from": frm, "to": to_status, "note": note})
        _save(state)
        return entry
    raise KeyError(f"job {job_id} not found")


def gap_analysis(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Compare job requirements vs profile — honest gaps, no invented skills."""
    req = job.get("requirements") or job.get("description") or ""
    skills = {str(s).lower() for s in (profile.get("skills") or [])}
    exp_years = float(profile.get("experience_years") or 0)
    gaps: list[str] = []
    matched: list[str] = []
    # keyword overlap on skills mentioned in description/tags
    text = " ".join([str(req), " ".join(str(t) for t in (job.get("tags") or []))]).lower()
    for skill in skills:
        if skill and skill in text:
            matched.append(skill)
    req_exp = job.get("experience_years_required")
    if req_exp is not None:
        try:
            if float(req_exp) > exp_years:
                gaps.append(f"experience: requires {float(req_exp):g}y, profile {exp_years:g}y")
        except (TypeError, ValueError):
            pass
    if job.get("portfolio_required") and not profile.get("portfolio_url"):
        gaps.append("portfolio required but none on profile")
    if job.get("english_required") and not profile.get("english_level"):
        gaps.append("english required, level unknown")
    if not matched and skills:
        gaps.append("no profile skills detected in job description")
    return {"matched_skills": sorted(matched), "gaps": gaps, "profile": {"experience_years": exp_years, "skills_count": len(skills)}}
