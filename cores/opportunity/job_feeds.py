"""Real remote-job feeds → remote_job_matcher (v12 Phase 4).

Public, documented, key-free job APIs only:
- Remotive:  https://remotive.com/api/remote-jobs
- Arbeitnow: https://www.arbeitnow.com/api/job-board-api
- RemoteOK:  https://remoteok.com/api  (first element is metadata)

Each fetcher returns normalized job dicts compatible with
remote_job_matcher.match_job(). Network failures return [] — never fake data.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cores.opportunity.remote_job_matcher import JobPreferences, rank_jobs

logger = logging.getLogger(__name__)

TIMEOUT = 15.0
HEADERS = {"User-Agent": "OWNEX/12.0 (+personal job matcher)"}


def _norm(title: str, company: str, url: str, desc: str, source: str, **extra: Any) -> dict[str, Any]:
    return {
        "title": title,
        "company": company,
        "url": url,
        "description": (desc or "")[:2000],
        "source": source,
        "language": "es",  # feeds are EN-heavy; matcher penalizes via english_required/unknown fields
        "remote": True,
        "published_at": extra.pop("published_at", None),
        **extra,
    }


def fetch_remotive(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Remotive public API — remote jobs worldwide."""
    try:
        params = {"limit": min(limit, 100)}
        if query:
            params["search"] = query
        r = httpx.get("https://remotive.com/api/remote-jobs", params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        jobs = []
        for j in (r.json().get("jobs") or [])[:limit]:
            tags = [t.lower() for t in (j.get("tags") or [])]
            salary = j.get("salary") or ""
            jobs.append(
                _norm(
                    j.get("title") or "",
                    j.get("company_name") or "",
                    j.get("url") or "",
                    j.get("description") or "",
                    "remotive",
                    published_at=j.get("publication_date"),
                    salary_raw=salary,
                    english_required=True,  # Remotive board is English-first
                    tags=tags,
                    candidate_ok="argentina" in (j.get("candidate_required_location") or "").lower()
                    or "worldwide" in (j.get("candidate_required_location") or "").lower(),
                )
            )
        return jobs
    except Exception as exc:
        logger.warning("remotive fetch failed: %s", exc)
        return []


def fetch_arbeitnow(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Arbeitnow free job board API."""
    try:
        r = httpx.get("https://www.arbeitnow.com/api/job-board-api", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data") or []
        if query:
            q = query.lower()
            data = [j for j in data if q in (j.get("title") or "").lower() or q in (j.get("company_name") or "").lower()]
        jobs = []
        for j in data[:limit]:
            remote = "remote" in (j.get("remote") and "true" or str(j.get("location") or "")).lower() or bool(j.get("remote"))
            jobs.append(
                _norm(
                    j.get("title") or "",
                    j.get("company_name") or "",
                    j.get("url") or "",
                    j.get("description") or "",
                    "arbeitnow",
                    published_at=j.get("created_at"),
                    remote=remote,
                    tags=[t.lower() for t in (j.get("tags") or [])],
                )
            )
        return jobs
    except Exception as exc:
        logger.warning("arbeitnow fetch failed: %s", exc)
        return []


def fetch_remoteok(query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """RemoteOK public JSON API (first array element is metadata)."""
    try:
        r = httpx.get("https://remoteok.com/api", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data and isinstance(data[0], dict) and "legal" in data[0]:
            data = data[1:]
        jobs = []
        q = query.lower()
        for j in data[: limit * 2]:
            if len(jobs) >= limit:
                break
            title = j.get("position") or ""
            if q and q not in title.lower() and q not in (j.get("company") or "").lower():
                continue
            salary_min = j.get("salary_min")
            jobs.append(
                _norm(
                    title,
                    j.get("company") or "",
                    j.get("url") or f"https://remoteok.com/remote-jobs/{j.get('id')}",
                    j.get("description") or "",
                    "remoteok",
                    published_at=j.get("date"),
                    salary_min=salary_min,
                    tags=[str(t).lower() for t in (j.get("tags") or [])][:10],
                )
            )
        return jobs
    except Exception as exc:
        logger.warning("remoteok fetch failed: %s", exc)
        return []


FEEDS = {"remotive": fetch_remotive, "arbeitnow": fetch_arbeitnow, "remoteok": fetch_remoteok}


def fetch_all(query: str = "", limit_per_feed: int = 50, feeds: list[str] | None = None) -> list[dict[str, Any]]:
    """Fetch from all (or selected) feeds and merge."""
    out: list[dict[str, Any]] = []
    for name, fn in FEEDS.items():
        if feeds and name not in feeds:
            continue
        out.extend(fn(query=query, limit=limit_per_feed))
    return out


def search_remote_jobs(query: str = "", profile: dict[str, Any] | None = None, prefs: JobPreferences | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch real jobs, score with remote_job_matcher, return ranked list."""
    jobs = fetch_all(query=query, limit_per_feed=max(limit, 50))
    return rank_jobs(jobs, profile=profile, prefs=prefs)[:limit]
