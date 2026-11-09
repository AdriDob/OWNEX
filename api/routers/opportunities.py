from fastapi import APIRouter, Query

from api.schemas.models import PaginatedResponse
from api.services.data_service import list_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=PaginatedResponse)
def get_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    sort_by: str = Query("roi"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_opportunities(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/profile")
def get_user_profile():
    """Current user profile used by matcher/drafter (real data only)."""
    from cores.opportunity.user_profile import get_profile

    return {"profile": get_profile()}


@router.put("/profile")
def put_user_profile(body: dict):
    """Update user profile — only whitelisted fields are stored."""
    from cores.opportunity.user_profile import update_profile

    return {"profile": update_profile(body)}


@router.get("/remote-jobs/search")
def remote_jobs_search(
    q: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
    salary_min: float = Query(0, ge=0),
    max_tech_tests: int = Query(1, ge=0, le=10),
    payment_methods: str = Query(""),
):
    """Search real remote jobs (Remotive/Arbeitnow/RemoteOK) ranked by remote_job_matcher."""
    from cores.opportunity.job_feeds import search_remote_jobs
    from cores.opportunity.remote_job_matcher import JobPreferences
    from cores.opportunity.user_profile import get_profile

    profile = get_profile()
    prefs = JobPreferences(
        salary_min_usd=salary_min,
        max_tech_tests=max_tech_tests,
        payment_methods=tuple(p.strip().lower() for p in payment_methods.split(",") if p.strip()),
    )
    jobs = search_remote_jobs(query=q, profile=profile or None, prefs=prefs, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/remote-jobs/save")
def remote_jobs_save(body: dict):
    """Save a remote job (+optional match) into the application tracker."""
    from cores.opportunity.job_tracker import save_job

    job = body.get("job") or {}
    if not job.get("title"):
        return {"error": "job.title required"}
    entry = save_job(job, body.get("match"))
    return {"saved": True, "id": entry["id"], "status": entry["status"]}


@router.get("/remote-jobs/saved")
def remote_jobs_saved(status: str = ""):
    """List tracked remote jobs, optionally filtered by pipeline status."""
    from cores.opportunity.job_tracker import list_jobs

    jobs = list_jobs(status or None)
    return {"jobs": jobs, "count": len(jobs)}


@router.post("/remote-jobs/{job_id}/draft")
def remote_jobs_draft(job_id: str, body: dict):
    """Generate a DRAFT application (cover letter + gap notes) from real profile data.

    Requires profile in body: {name, skills[], experience_years, ...}.
    Output is always requires_approval — nothing is ever submitted.
    """
    from cores.opportunity.application_drafter import draft_application
    from cores.opportunity.job_tracker import list_jobs
    from cores.opportunity.user_profile import get_profile

    entry = next((j for j in list_jobs() if j["id"] == job_id), None)
    if entry is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="job not found")
    profile = body.get("profile") or get_profile() or {}
    draft = draft_application(entry["job"], profile)
    return {"id": job_id, **draft}


@router.post("/remote-jobs/{job_id}/transition")
def remote_jobs_transition(job_id: str, body: dict):
    """Advance a tracked job: saved→analyzed→prepared→approved→applied→accepted/rejected."""
    from cores.opportunity.job_tracker import transition

    try:
        entry = transition(job_id, str(body.get("status") or ""), str(body.get("note") or ""))
    except (ValueError, KeyError) as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": entry["id"], "status": entry["status"]}
