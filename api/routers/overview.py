from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func as sa_func

# Import HHD tracker
from core.system.hhd_tracker import get_hhd_summary, init_hhd_tracker
from cores.engine.unified_scoring import score as unified_score
from cores.engine.unified_scoring import score_target as unified_score_target
from cores.gateway.schemas import safe_response
from cores.targets.models import TargetIntel
from database import db, models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["overview"])

# Initialize HHD tracker on module load
init_hhd_tracker()


@router.get("/overview")
def get_overview():
    session = db.SessionLocal()
    try:
        target_count = session.query(models.Target).count()
        endpoint_count = session.query(models.Endpoint).count()
        finding_count = session.query(models.Finding).count()
        active_scans = session.query(models.ScanRun).filter(models.ScanRun.status.in_(["pending", "running"])).count()
        confirmed_count = session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count()

        # Risk/vector distribution — deduplicate by (path, method) to minimise scoring calls
        high_signal = 0
        total_risk = 0.0
        risk_buckets: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        vector_dist: dict[str, int] = {}
        endpoint_target_ids: dict[int, int] = {}
        _score_cache: dict[tuple[str, str], dict[str, Any]] = {}

        for ep in session.query(
            models.Endpoint.path,
            models.Endpoint.method,
            models.Endpoint.params,
            models.Endpoint.target_id,
            models.Endpoint.id,
        ).all():
            ep_params = {}
            if ep.params:
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    ep_params = json.loads(ep.params)
            key = (ep.path or "/", ep.method or "GET")
            if key not in _score_cache:
                _score_cache[key] = unified_score(*key, ep_params)
            s = _score_cache[key]
            rs = s.get("risk_score", 0)
            total_risk += rs
            endpoint_target_ids[ep.id] = ep.target_id
            if rs >= 50:
                risk_buckets["critical"] += 1
                high_signal += 1
            elif rs >= 25:
                risk_buckets["high"] += 1
                high_signal += 1
            elif rs >= 10:
                risk_buckets["medium"] += 1
            elif rs >= 1:
                risk_buckets["low"] += 1
            else:
                risk_buckets["info"] += 1
            vec = s.get("vector", "Unknown")
            vector_dist[vec] = vector_dist.get(vec, 0) + 1

        avg_risk = round(total_risk / max(endpoint_count, 1), 1)

        # Severity counts — SQL GROUP BY
        severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for row in (
            session.query(models.Finding.severity, sa_func.count(models.Finding.id))
            .group_by(models.Finding.severity)
            .all()
        ):
            sev = (row[0] or "info").lower()
            severity_counts[sev] = row[1]

        # Pipeline stages — single query for finding + verdict status
        pipeline_stages = {"detected": 0, "validated": 0, "confirmed": 0, "reported": 0}
        confirmed_ep_ids = {
            v[0]
            for v in session.query(models.Verdict.endpoint_id)
            .filter(
                models.Verdict.status == "confirmed",
                models.Verdict.endpoint_id.isnot(None),
            )
            .distinct()
            .all()
        }
        validated_ep_ids = {
            v[0]
            for v in session.query(models.Verdict.endpoint_id)
            .filter(
                models.Verdict.status != "confirmed",
                models.Verdict.endpoint_id.isnot(None),
            )
            .distinct()
            .all()
        } - confirmed_ep_ids

        for f in session.query(models.Finding.endpoint_id).all():
            eid = f.endpoint_id
            if eid in confirmed_ep_ids:
                pipeline_stages["confirmed"] += 1
                pipeline_stages["reported"] += 1
            elif eid in validated_ep_ids:
                pipeline_stages["validated"] += 1
            else:
                pipeline_stages["detected"] += 1

        # Top targets — one query per target is unavoidable for scoring, but limit to 10
        targets = session.query(models.Target).limit(10).all()
        top_targets = []
        for t in targets:
            ep_count = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).count()
            ep_paths = [
                row[0] for row in session.query(models.Endpoint.path).filter(models.Endpoint.target_id == t.id).all()
            ]
            roi = unified_score_target(
                {
                    "api_count": ep_count,
                    "has_graphql": any("/graphql" in (p or "").lower() for p in ep_paths),
                    "has_admin": any("admin" in (p or "").lower() for p in ep_paths),
                    "has_api": any("/api/" in p for p in ep_paths if p),
                    "has_exports": any("export" in (p or "").lower() for p in ep_paths),
                    "source": (t.name or "").lower(),
                }
            )
            top_targets.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "domain": t.domain,
                    "endpoint_count": ep_count,
                    "roi_score": round(roi.get("roi_score", 0), 2),
                    "path": ep_paths[0] if ep_paths else "/",
                }
            )

        # Platform distribution for opportunities + endpoint counts per platform type (insight for Forge)
        platform_counts: dict[str, int] = {}
        for t in targets:
            # Simplified: use target name as platform indicator (actual implementation would fetch from source)
            name = t.name or "Unknown"
            platform_counts[name] = platform_counts.get(name, 0) + 1

        # Target categories count (derived from target.name prefix)
        category_counts: dict[str, int] = {}
        for t in targets:
            # Example category based on first word of name
            first_word = (t.name or "").split()[0].lower() if t.name else "other"
            category_counts[first_word] = category_counts.get(first_word, 0) + 1

        # Build result payload for overview
        result = {
            "targets": target_count,
            "endpoints": endpoint_count,
            "findings": finding_count,
            "confirmed": confirmed_count,
            "active_scans": active_scans,
            "avg_risk_score": avg_risk,
            "risk_distribution": risk_buckets,
            "platform_distribution": platform_counts,
            "category_distribution": category_counts,
            "severity_counts": severity_counts,
            "pipeline_stages": pipeline_stages,
            "top_targets": top_targets,
            "vector_distribution": vector_dist,
            "high_signal_endpoints": high_signal,
        }

        return safe_response(result)
    finally:
        session.close()


@router.get("/system/health")
def get_system_health():
    session = db.SessionLocal()
    try:
        target_count = session.query(models.Target).count()
        endpoint_count = session.query(models.Endpoint).count()
        finding_count = session.query(models.Finding).count()
        verdict_count = session.query(models.Verdict).count()
        intel_count = session.query(TargetIntel).count()

        confirmed_verdicts = session.query(models.Verdict).filter(models.Verdict.status == "confirmed").count()
        active_scans = session.query(models.ScanRun).filter(models.ScanRun.status.in_(["pending", "running"])).count()

        last_scan = session.query(models.ScanRun).order_by(models.ScanRun.started_at.desc()).first()
        last_finding = session.query(models.Finding).order_by(models.Finding.created_at.desc()).first()

        result = {
            "status": "healthy",
            "uptime_hint": "API is running",
            "database": {
                "targets": target_count,
                "endpoints": endpoint_count,
                "findings": finding_count,
                "verdicts": verdict_count,
                "intel_programs": intel_count,
            },
            "pipeline": {
                "confirmed_verdicts": confirmed_verdicts,
                "active_scans": active_scans,
            },
            "last_activity": {
                "last_scan": last_scan.started_at.isoformat() if last_scan and last_scan.started_at else None,
                "last_finding": last_finding.created_at.isoformat()
                if last_finding and last_finding.created_at
                else None,
            },
            "human_time": get_hhd_summary(),
        }

        from cores.system_health import collect_health

        try:
            detailed = collect_health()
            result["detailed"] = detailed.to_dict()
        except Exception as e:
            logger.warning("Health check collection failed: %s", e)

        # Add loop engine status
        try:
            from core.loop.startup import get_loop_status

            result["loop_engines"] = get_loop_status()
        except Exception as e:
            logger.warning("Loop engine status failed: %s", e)

        # Add temp manager status
        try:
            from core.system.temp_manager import get_temp_manager

            result["temp_manager"] = get_temp_manager().health()
        except Exception as e:
            logger.warning("Temp manager status failed: %s", e)

        return safe_response(result)
    finally:
        session.close()
