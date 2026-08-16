"""Mission Control data service — in-process facade over OWNEX/Rastro engines.

Exposes a single MissionControlData service consumed by the native GUI.
The data comes from:
  - cores.direct_work_engine.engine.DirectWorkEngine (opportunity/workbank)
  - cores.opportunity (OpportunityEngine singleton)
  - database/ (targets/endpoints/findings/scan runs)
  - core.system.hhd_tracker (human-time summary)
  - cores.engine.unified_scoring (risk scoring)
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, TypeVar

from cores.direct_work_engine.engine import DirectWorkEngine
from cores.opportunity import get_engine as get_opportunity_engine
from cores.system.hhd_tracker import get_hhd_summary

from .base import AsyncResult, ServiceError, service_call

logger = logging.getLogger("ownex.native.services.mission")

T = TypeVar("T")


def _iso(dt: datetime | str | float | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    try:
        if isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(float(dt), tz=UTC)
        elif dt.tzinfo is None:  # type: ignore[union-attr]
            dt = dt.replace(tzinfo=UTC)  # type: ignore[union-attr]
        return dt.isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _run_async(result: AsyncResult, ok_fn: Any) -> Any:
    """Unwrap an AsyncResult envelope, raising ServiceError on failure."""
    if not result.ok:
        raise ServiceError(result.error or "service call failed")
    return result.payload


class MissionControlData:
    """Single in-process source for Mission Control views."""

    def __init__(self) -> None:
        self._direct_work: DirectWorkEngine | None = None
        self._opportunity: Any = None

    def _ensure_engines(self) -> None:
        if self._direct_work is None:
            self._direct_work = DirectWorkEngine()
            self._register_adapters(self._direct_work)
        if self._opportunity is None:
            self._opportunity = get_opportunity_engine()

    @staticmethod
    def _register_adapters(engine: DirectWorkEngine) -> None:
        try:
            from api.adapters.legacy import build_default_adapters

            for adapter in build_default_adapters():
                if adapter.source.platform not in engine.discovery.adapters:
                    engine.register_adapter(adapter)
        except Exception as exc:
            logger.warning("Could not register discovery adapters: %s", exc)

    # -- status / health -------------------------------------------------
    def get_status(self) -> dict[str, Any]:
        self._ensure_engines()

        def _work() -> dict[str, Any]:
            st: dict[Any, Any] = self._direct_work.get_status() or {}  # type: ignore[attr-defined,union-attr]
            opp_status: dict[Any, Any] = {}
            if hasattr(self._opportunity, "get_status"):
                opp_status = self._opportunity.get_status() or {}  # type: ignore[attr-defined,union-attr,call-arg]
            return {
                "running": st.get("running", False),
                "engine_running": bool(st.get("running", False)),
                "opportunity_engine": opp_status,
                "stats": st.get("stats", {}),
                "last_cycle_at": st.get("stats", {}).get("last_cycle_at"),
            }

        with service_call():
            return _work()

    # -- targets ---------------------------------------------------------
    def get_targets(self, limit: int = 10) -> list[dict[str, Any]]:
        def _work() -> list[dict[str, Any]]:
            from cores.engine.unified_scoring import score_target
            from database import db, models

            session = db.SessionLocal()
            try:
                targets_out = []
                for t in session.query(models.Target).limit(limit).all():
                    ep_count = session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).count()
                    roi = score_target(
                        {
                            "api_count": ep_count,
                            "has_graphql": False,
                            "has_admin": False,
                            "has_api": True,
                            "has_exports": False,
                            "source": (t.name or "").lower(),
                        }
                    )
                    targets_out.append(
                        {
                            "id": t.id,
                            "name": t.name,
                            "domain": t.domain,
                            "endpoint_count": ep_count,
                            "roi_score": round(roi.get("roi_score", 0), 2),
                            "active": getattr(t, "active", True),
                        }
                    )
                return targets_out
            finally:
                session.close()

        with service_call():
            return _work()

    # -- findings --------------------------------------------------------
    def get_findings(self, limit: int = 20, status_filter: str | None = None) -> list[dict[str, Any]]:
        def _work() -> list[dict[str, Any]]:
            from database import db, models

            session = db.SessionLocal()
            try:
                q = session.query(models.Finding).order_by(models.Finding.created_at.desc())
                if status_filter:
                    q = q.filter(models.Finding.status == status_filter)
                findings = []
                for f in q.limit(limit).all():
                    findings.append(
                        {
                            "id": f.id,
                            "title": f.title,
                            "severity": f.severity,
                            "status": f.status,
                            "target_id": f.target_id,
                            "created_at": _iso(f.created_at),  # type: ignore[arg-type]
                            "updated_at": _iso(f.updated_at),  # type: ignore[arg-type]
                            "cvss": f.cvss_score,
                            "cwe": f.cwe,
                        }
                    )
                return findings
            finally:
                session.close()

        with service_call():
            return _work()

    # -- opportunities ---------------------------------------------------
    def get_opportunities(self, mode: str = "balanced", limit: int = 8) -> list[dict[str, Any]]:
        self._ensure_engines()

        def _work() -> list[dict[str, Any]]:
            import asyncio

            from cores.direct_work_engine.models import UserProfile

            profile = UserProfile(name="Rastro User")
            opps_raw = asyncio.run(self._direct_work.discovery.discover_all()) or []  # type: ignore[union-attr]
            ranked = (
                self._direct_work.recommender.recommend(  # type: ignore[union-attr]
                    opps_raw, profile, limit=limit, mode=mode
                )
                or []
            )
            out = []
            for r in ranked[:limit]:
                opp = r.opportunity if hasattr(r, "opportunity") else r
                d: dict[str, Any] = {
                    "id": getattr(opp, "id", None),
                    "title": getattr(opp, "title", ""),
                    "platform": getattr(opp, "platform", None),
                    "category": getattr(opp, "category", None),
                    "reward": getattr(opp, "reward", None),
                    "reward_usd": getattr(opp, "reward_usd", 0),
                    "barrier_score": getattr(opp, "barrier_score", 0),
                    "success_probability": getattr(opp, "acceptance_probability", 0),
                    "time_to_payment_days": getattr(opp, "time_to_payment_days", None),
                    "employment_type": getattr(opp, "employment_type", None),
                    "remote": getattr(opp, "remote", True),
                    "url": getattr(opp, "url", ""),
                }
                d["rank"] = getattr(r, "rank", None)
                d["score"] = getattr(r, "final_score", getattr(r, "score", 0))
                d["why"] = getattr(r, "reasoning", getattr(r, "reasoning", {})) or {}
                out.append(d)
            return out

        with service_call():
            return _work()

    # -- workbank --------------------------------------------------------
    def get_workbank(self) -> dict[str, Any]:
        self._ensure_engines()

        def _work() -> dict[str, Any]:
            from cores.direct_work_engine.workbank import get_workbank

            bank = get_workbank()
            data = bank.to_dict()
            ready = data.get("items", [])
            # WorkItem dataclasses -> dicts for the view layer.
            ready_items = []
            for i in ready:
                if hasattr(i, "__dataclass_fields__"):
                    ready_items.append(asdict(i))
                else:
                    ready_items.append(dict(i) if isinstance(i, dict) else {"id": str(i)})
            return {
                "summary": data,
                "targets": data.get("targets", []),
                "ready_to_deliver": data.get("ready_to_deliver", [])
                if isinstance(data.get("ready_to_deliver"), int)
                else ready_items,
            }

        with service_call():
            return _work()

    # -- activity/timeline ----------------------------------------------
    def get_activity(self, limit: int = 30) -> list[dict[str, Any]]:
        def _work() -> list[dict[str, Any]]:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            events = bus.get_history(limit=limit) or []  # type: ignore[attr-defined]
            out = []
            for e in events:
                if isinstance(e, dict):
                    out.append(
                        {
                            "id": e.get("id"),
                            "event_type": e.get("event_type", e.get("type", "")),
                            "severity": e.get("severity", "info"),
                            "title": e.get("title", e.get("event_type", "")),
                            "detail": e.get("detail", e.get("data", {})),
                            "timestamp": _iso(e.get("timestamp")),
                        }
                    )
                elif hasattr(e, "timestamp"):
                    out.append(
                        {
                            "id": getattr(e, "id", id(e)),
                            "event_type": getattr(e, "event_type", getattr(e, "type", "")),
                            "severity": getattr(e, "severity", "info"),
                            "title": getattr(e, "title", getattr(e, "event_type", "")),
                            "detail": getattr(e, "data", {}),
                            "timestamp": _iso(getattr(e, "timestamp", None)),
                        }
                    )
            return out

        try:
            with service_call():
                return _work()
        except ServiceError:
            logger.warning("event bus history unavailable")
            return []

    # -- consolidated dashboard -----------------------------------------
    def get_dashboard(self) -> dict[str, Any]:
        def _work() -> dict[str, Any]:
            status = self.get_status()
            targets = self.get_targets()
            findings = self.get_findings()
            opps = self.get_opportunities()
            workbank = self.get_workbank()
            activity = self.get_activity()
            summary = status.get("stats", {})
            return {
                "generated_at": datetime.now(UTC).isoformat(),
                "status": status,
                "targets": targets,
                "findings": findings,
                "opportunities": opps,
                "workbank": workbank,
                "activity": activity,
                "hhd": get_hhd_summary(),
                "counts": {
                    "targets": len(targets),
                    "findings": summary.get("total_opportunities_seen", 0),
                    "confirmed": summary.get("cycles_completed", 0),
                    "opps": len(opps),
                    "ready_to_deliver": workbank.get("ready_to_deliver", 0)
                    if isinstance(workbank.get("ready_to_deliver"), int)
                    else len(workbank.get("ready_to_deliver", [])),
                },
            }

        with service_call():
            return _work()


# Singleton instance — same pattern as routers' get_engine()
_mission: MissionControlData | None = None


def get_mission() -> MissionControlData:
    global _mission
    if _mission is None:
        _mission = MissionControlData()
    return _mission
