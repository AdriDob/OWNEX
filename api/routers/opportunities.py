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

    prefs = JobPreferences(
        salary_min_usd=salary_min,
        max_tech_tests=max_tech_tests,
        payment_methods=tuple(p.strip().lower() for p in payment_methods.split(",") if p.strip()),
    )
    jobs = search_remote_jobs(query=q, prefs=prefs, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}
