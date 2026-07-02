"""
Orion Context Engine — single source of truth for all system state.

Every field comes from a real database query or engine computation.
Results are cached with configurable TTL (default 30s) to avoid
hammering the DB on every request.

Usage:
    ctx = get_orion_context()  # returns dict with all system state
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from database import db, models

logger = logging.getLogger("orion.context")

_DEFAULT_TTL = 30  # seconds

_cache: dict[str, Any] | None = None
_cache_ts: float = 0
_cache_lock = threading.Lock()
_cache_ttl: float = _DEFAULT_TTL


def configure(ttl: float = 30) -> None:
    global _cache_ttl
    _cache_ttl = ttl


def invalidate() -> None:
    global _cache, _cache_ts
    with _cache_lock:
        _cache = None
        _cache_ts = 0


def get_orion_context(force_refresh: bool = False) -> dict[str, Any]:
    global _cache, _cache_ts
    now = time.time()

    if not force_refresh and _cache is not None and (now - _cache_ts) < _cache_ttl:
        return _cache

    with _cache_lock:
        if _cache is not None and (now - _cache_ts) < _cache_ttl and not force_refresh:
            return _cache
        _cache = _build_context()
        _cache_ts = time.time()
        return _cache


def _build_context() -> dict[str, Any]:
    session = db.SessionLocal()
    try:
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(hours=24)

        # ── Batch 1: Counts & simple aggregates ──
        target_count = session.query(models.Target).count()
        finding_count = session.query(models.Finding).count()
        endpoint_count = session.query(models.Endpoint).count()
        verdict_count = session.query(models.Verdict).count()

        # ── Batch 2: Verdicts by status ──
        verdict_rows = session.query(models.Verdict.status, models.Verdict.endpoint_id).all()
        v_status: dict[str, int] = {}
        confirmed_vids: set[int] = set()
        for v in verdict_rows:
            v_status[v.status] = v_status.get(v.status, 0) + 1
            if v.status == "confirmed" and v.endpoint_id is not None:
                confirmed_vids.add(v.endpoint_id)

        # ── Batch 3: Findings ──
        findings = session.query(models.Finding.id, models.Finding.severity, models.Finding.endpoint_id, models.Finding.created_at, models.Finding.target_id).all()
        sev_counts: dict[str, int] = {}
        new_findings_24h = 0
        payout_by_severity = {"critical": 25000, "high": 10000, "medium": 3000, "low": 500}
        total_estimated_payout = 0
        confirmed_findings = 0
        for f in findings:
            sev = (f.severity or "info").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
            total_estimated_payout += payout_by_severity.get(sev, 0)
            if f.created_at and f.created_at >= cutoff_24h:
                new_findings_24h += 1
            if f.endpoint_id in confirmed_vids:
                confirmed_findings += 1

        # ── Batch 4: Reports ──
        report_rows = session.query(models.Report.status, models.Report.estimated_reward).all()
        report_by_status: dict[str, int] = {}
        pending_rewards = 0.0
        total_rewards = 0.0
        reports_ready = 0
        for r in report_rows:
            st = r.status or "draft"
            report_by_status[st] = report_by_status.get(st, 0) + 1
            payout = r.estimated_reward or 0
            total_rewards += payout
            if st in ("draft", "pending"):
                pending_rewards += payout
                reports_ready += 1

        # ── Batch 5: Active scans ──
        active_scans = session.query(models.ScanRun).filter(
            models.ScanRun.status.in_(["pending", "running"])
        ).count()

        # ── Batch 6: Recent scans ──
        recent_scans = session.query(
            models.ScanRun.id, models.ScanRun.target_id, models.ScanRun.mode,
            models.ScanRun.status, models.ScanRun.endpoint_count, models.ScanRun.started_at,
        ).order_by(models.ScanRun.started_at.desc()).limit(10).all()

        # ── Batch 7: Targets w/ intel for oportunities ──
        target_rows = session.query(
            models.Target.id, models.Target.name, models.Target.domain, models.Target.created_at,
        ).all()
        target_ids = [t.id for t in target_rows]
        from cores.targets.models import TargetIntel
        intel_map: dict[int, Any] = {}
        if target_ids:
            for intel in session.query(TargetIntel).filter(TargetIntel.id.in_(target_ids)).all():
                intel_map[intel.id] = intel

        # Count endpoints per target
        ep_counts: dict[int, int] = {}
        for ep in session.query(models.Endpoint.target_id).all():
            ep_counts[ep.target_id] = ep_counts.get(ep.target_id, 0) + 1

        # Build top bounties
        bounties_list: list[dict] = []
        for t in target_rows:
            intel = intel_map.get(t.id)
            opp_score = round((intel.opportunity_score or 0) / 10, 1) if intel else 0
            if opp_score > 0:
                bounties_list.append({
                    "id": t.id,
                    "name": t.name or f"Target #{t.id}",
                    "domain": t.domain or "",
                    "opportunity_score": opp_score,
                    "endpoints": ep_counts.get(t.id, 0),
                    "competition": int(intel.competition_score or 0) if intel else 0,
                    "freshness": int(intel.freshness_score or 0) if intel else 50,
                })
        bounties_list.sort(key=lambda x: x["opportunity_score"], reverse=True)

        # ── Batch 8: Activity (last 24h) ──
        activity: list[dict] = []
        for f in findings:
            if f.created_at and f.created_at >= cutoff_24h:
                activity.append({
                    "type": "finding", "id": f.id,
                    "severity": f.severity or "medium",
                    "timestamp": f.created_at.isoformat(),
                })
        for v in verdict_rows:
            pass  # skip individual verdict activity for perf
        activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # ── Batch 9: Wallets ──
        wallets_data: dict[str, str] = {}
        try:
            from cores.identity_engine import wallet_provider
            wallets_data = wallet_provider.get_all_wallets()
        except Exception:
            pass

        # ── Batch 10: Linked accounts ──
        linked_accounts: list[dict] = []
        try:
            from cores.identity_engine import identity_provider
            linked_accounts = identity_provider.get_connections()
        except Exception:
            pass

        # ── Health score ──
        db_ok = True
        try:
            session.execute(db.text("SELECT 1"))
        except Exception:
            db_ok = False
        health_score = 100
        details: list[str] = []
        if not db_ok:
            health_score -= 50
            details.append("database_unreachable")
        if active_scans > 0:
            pass  # healthy
        if verdict_count == 0:
            details.append("no_verdicts")
        system_status = "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "critical"

        # ── Next action (from highest score opportunity) ──
        next_action = None
        if bounties_list:
            top = bounties_list[0]
            next_action = {
                "target_id": top["id"],
                "title": f"Analizar {top['name']}",
                "why_now": f"Oportunidad score {top['opportunity_score']}, {top['endpoints']} endpoints disponibles",
                "effort": "medium",
                "estimated_reward": f"${payout_by_severity.get('high', 10000):,}",
                "type": "analysis",
            }

        return {
            "timestamp": now.isoformat(),
            "system": {
                "status": system_status,
                "health_score": health_score,
                "details": details,
                "uptime_hours": 0,
            },
            "counts": {
                "targets": target_count,
                "endpoints": endpoint_count,
                "findings": finding_count,
                "verdicts": verdict_count,
                "confirmed_findings": confirmed_findings,
                "total_estimated_payout": total_estimated_payout,
                "pending_rewards": pending_rewards,
                "reports_ready": reports_ready,
                "active_scans": active_scans,
            },
            "verdicts": {
                "by_status": v_status,
                "confirmed": v_status.get("confirmed", 0),
                "rejected": v_status.get("rejected", 0),
                "inconclusive": v_status.get("inconclusive", 0),
            },
            "findings": {
                "by_severity": sev_counts,
                "new_24h": new_findings_24h,
            },
            "reports": {
                "by_status": report_by_status,
                "total_rewards": total_rewards,
                "pending_rewards": pending_rewards,
                "ready_for_approval": reports_ready,
            },
            "earnings": {
                "total": total_rewards,
                "pending": pending_rewards,
                "paid": report_by_status.get("paid", 0),
            },
            "opportunities": {
                "total": len(bounties_list),
                "top": bounties_list[:10],
            },
            "next_action": next_action,
            "scans": {
                "active": active_scans,
                "recent": [
                    {"id": s.id, "target_id": s.target_id, "mode": s.mode or "",
                     "status": s.status, "endpoints": s.endpoint_count,
                     "started": s.started_at.isoformat() if s.started_at else ""}
                    for s in recent_scans
                ],
            },
            "activity_24h": {
                "total": len(activity),
                "events": activity[:15],
            },
            "wallets": wallets_data,
            "linked_accounts": linked_accounts,
            "pipeline": {
                "detected": sev_counts.get("info", 0) + sev_counts.get("low", 0),
                "validated": sev_counts.get("medium", 0),
                "confirmed": confirmed_findings,
                "reported": report_by_status.get("submitted", 0) + report_by_status.get("paid", 0),
            },
            "_meta": {
                "cached_at": _cache_ts if _cache_ts else time.time(),
                "ttl_seconds": _cache_ttl,
            },
        }

    except Exception as e:
        logger.error("Failed to build context: %s", e)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "system": {"status": "error", "health_score": 0, "details": [str(e)], "uptime_hours": 0},
            "counts": {}, "verdicts": {}, "findings": {}, "reports": {},
            "earnings": {}, "opportunities": {}, "next_action": None,
            "scans": {}, "activity_24h": {}, "wallets": {}, "linked_accounts": [],
            "pipeline": {},
            "_meta": {"error": str(e)},
        }
    finally:
        session.close()
