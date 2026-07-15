from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from database import db
from database.models import KnowledgeAsset, MetricEvent, MetricRollup

logger = logging.getLogger("orion.core.evolution.engine")

_OBSERVE_BATCH_SIZE = 50


class EvolutionEngine:
    """Central nervous system for ORION's self-improvement.

    Designed as the Observability → Analysis → Experimentation → Learning
    loop that continuously finds and eliminates efficiency losses across all
    ORION domains (CATEYE, ATLAS, ODYSSEY, HERMES, Core).

    Layers (built incrementally):
        1. Observe  — persist structured metrics + raw telemetry
        2. Analyze  — detect bottlenecks, patterns, inefficiencies
        3. Experiment — propose & track controlled changes
        4. Learn    — generate & validate KnowledgeAssets
    """

    def __init__(self) -> None:
        self._running = False
        self._metric_buffer: list[dict[str, Any]] = []

    # ── Observe layer ─────────────────────────────────────────────

    def record_event(
        self,
        module: str,
        event_type: str,
        *,
        duration_ms: float | None = None,
        status: str = "success",
        pipeline: str | None = None,
        tool: str | None = None,
        cpu_percent: float | None = None,
        memory_mb: float | None = None,
        target_id: int | None = None,
        finding_id: int | None = None,
        report_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Persist a single metric event atomically.

        Returns the new MetricEvent.id.
        """
        session = db.SessionLocal()
        try:
            event = MetricEvent(
                module=module,
                pipeline=pipeline,
                tool=tool,
                event_type=event_type,
                duration_ms=duration_ms,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                status=status,
                target_id=target_id,
                finding_id=finding_id,
                report_id=report_id,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event.id
        except Exception:
            session.rollback()
            logger.exception("Failed to record metric event")
            return -1
        finally:
            session.close()

    def record_event_buffered(self, **kwargs: Any) -> None:
        """Buffer a metric event for batch insert (higher throughput)."""
        self._metric_buffer.append(kwargs)
        if len(self._metric_buffer) >= _OBSERVE_BATCH_SIZE:
            self.flush_metric_buffer()

    def flush_metric_buffer(self) -> int:
        """Batch-insert all buffered metric events.

        Returns the number of rows inserted.
        """
        if not self._metric_buffer:
            return 0
        batch = self._metric_buffer[:]
        self._metric_buffer.clear()
        session = db.SessionLocal()
        try:
            rows = []
            for kw in batch:
                rows.append(
                    MetricEvent(
                        module=kw.get("module", "unknown"),
                        pipeline=kw.get("pipeline"),
                        tool=kw.get("tool"),
                        event_type=kw.get("event_type", "unknown"),
                        duration_ms=kw.get("duration_ms"),
                        cpu_percent=kw.get("cpu_percent"),
                        memory_mb=kw.get("memory_mb"),
                        status=kw.get("status", "success"),
                        target_id=kw.get("target_id"),
                        finding_id=kw.get("finding_id"),
                        report_id=kw.get("report_id"),
                        metadata_json=json.dumps(kw["metadata"]) if kw.get("metadata") else None,
                    )
                )
            session.add_all(rows)
            session.commit()
            return len(rows)
        except Exception:
            session.rollback()
            logger.exception("Failed to flush metric buffer")
            return 0
        finally:
            session.close()

    def query_events(
        self,
        *,
        module: str | None = None,
        event_type: str | None = None,
        pipeline: str | None = None,
        tool: str | None = None,
        status: str | None = None,
        target_id: int | None = None,
        finding_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query metric events with optional filters."""
        session = db.SessionLocal()
        try:
            q = session.query(MetricEvent)
            if module:
                q = q.filter(MetricEvent.module == module)
            if event_type:
                q = q.filter(MetricEvent.event_type == event_type)
            if pipeline:
                q = q.filter(MetricEvent.pipeline == pipeline)
            if tool:
                q = q.filter(MetricEvent.tool == tool)
            if status:
                q = q.filter(MetricEvent.status == status)
            if target_id is not None:
                q = q.filter(MetricEvent.target_id == target_id)
            if finding_id is not None:
                q = q.filter(MetricEvent.finding_id == finding_id)
            if since:
                q = q.filter(MetricEvent.timestamp >= since)
            if until:
                q = q.filter(MetricEvent.timestamp <= until)
            q = q.order_by(MetricEvent.timestamp.desc()).offset(offset).limit(limit)
            return [_metric_event_to_dict(e) for e in q.all()]
        finally:
            session.close()

    def count_events(self, **filters: Any) -> int:
        """Count metric events matching filters."""
        session = db.SessionLocal()
        try:
            q = session.query(MetricEvent)
            for field, value in filters.items():
                if hasattr(MetricEvent, field) and value is not None:
                    q = q.filter(getattr(MetricEvent, field) == value)
            return q.count()
        finally:
            session.close()

    def get_summary(
        self,
        *,
        granularity: str = "daily",
        module: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Return pre-aggregated metric rollups."""
        session = db.SessionLocal()
        try:
            q = session.query(MetricRollup).filter(MetricRollup.granularity == granularity)
            if module:
                q = q.filter(MetricRollup.module == module)
            q = q.order_by(MetricRollup.period_start.desc()).limit(limit)
            return [_metric_rollup_to_dict(r) for r in q.all()]
        finally:
            session.close()

    # ── Knowledge layer ───────────────────────────────────────────

    def create_asset(
        self,
        asset_type: str,
        domain: str,
        title: str,
        *,
        description: str = "",
        source: str = "own_data",
        source_url: str | None = None,
        source_confidence: float = 0.5,
        content: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """Create a new KnowledgeAsset.

        Returns the new asset id (or -1 on failure).
        """
        session = db.SessionLocal()
        try:
            asset = KnowledgeAsset(
                asset_type=asset_type,
                domain=domain,
                title=title,
                description=description,
                source=source,
                source_url=source_url,
                source_confidence=max(0.0, min(1.0, source_confidence)),
                content_json=json.dumps(content) if content else None,
                evidence_json=json.dumps(evidence) if evidence else None,
                tags_json=json.dumps(tags) if tags else None,
                status="draft",
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            return asset.id
        except Exception:
            session.rollback()
            logger.exception("Failed to create knowledge asset")
            return -1
        finally:
            session.close()

    def get_assets(
        self,
        *,
        domain: str | None = None,
        asset_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query knowledge assets with optional filters."""
        session = db.SessionLocal()
        try:
            q = session.query(KnowledgeAsset)
            if domain:
                q = q.filter(KnowledgeAsset.domain == domain)
            if asset_type:
                q = q.filter(KnowledgeAsset.asset_type == asset_type)
            if status:
                q = q.filter(KnowledgeAsset.status == status)
            q = q.order_by(KnowledgeAsset.updated_at.desc()).offset(offset).limit(limit)
            return [_knowledge_asset_to_dict(a) for a in q.all()]
        finally:
            session.close()

    def get_asset(self, asset_id: int) -> dict[str, Any] | None:
        """Get a single knowledge asset by id."""
        session = db.SessionLocal()
        try:
            a = session.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
            return _knowledge_asset_to_dict(a) if a else None
        finally:
            session.close()

    def update_asset_status(
        self,
        asset_id: int,
        status: str,
        *,
        impact_score: float | None = None,
        observation_count: int | None = None,
        opportunity_cost_hours: float | None = None,
    ) -> bool:
        """Update a knowledge asset's lifecycle status.

        Lifecycle: draft → hypothesis → validated → production → deprecated.
        Promotions record timestamps and increment validation_count.
        """
        valid = {"draft", "hypothesis", "validated", "production", "deprecated"}
        if status not in valid:
            logger.warning("Invalid status '%s' — must be one of %s", status, valid)
            return False
        session = db.SessionLocal()
        try:
            a = session.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
            if not a:
                return False
            old = a.status
            a.status = status
            if impact_score is not None:
                a.impact_score = impact_score
            if observation_count is not None:
                a.observation_count = observation_count
            if opportunity_cost_hours is not None:
                a.opportunity_cost_hours = opportunity_cost_hours
            if status in ("validated", "production"):
                a.last_validated = datetime.now(timezone.utc)
                a.validation_count = (a.validation_count or 0) + 1
            if status == "production":
                a.hit_count = (a.hit_count or 0) + 1
            logger.info("[EVOLUTION] Asset %d: %s → %s", asset_id, old, status)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def delete_asset(self, asset_id: int) -> bool:
        """Delete a knowledge asset by id."""
        session = db.SessionLocal()
        try:
            a = session.query(KnowledgeAsset).filter(KnowledgeAsset.id == asset_id).first()
            if not a:
                return False
            session.delete(a)
            session.commit()
            return True
        finally:
            session.close()


# ── Singleton access ─────────────────────────────────────────

_engine: EvolutionEngine | None = None


def get_evolution_engine() -> EvolutionEngine:
    global _engine
    if _engine is None:
        _engine = EvolutionEngine()
    return _engine


def init_evolution_engine() -> EvolutionEngine:
    """Initialize and return the Evolution Engine singleton.

    Call once at boot time.  Creates tables if they don't exist.
    """
    global _engine
    _engine = EvolutionEngine()
    logger.info("[EVOLUTION] Engine initialized — Observe layer ready")
    return _engine


# ── Serialization helpers ──────────────────────────────────


def _metric_event_to_dict(e: MetricEvent) -> dict[str, Any]:
    return {
        "id": e.id,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "module": e.module,
        "pipeline": e.pipeline,
        "tool": e.tool,
        "event_type": e.event_type,
        "duration_ms": e.duration_ms,
        "cpu_percent": e.cpu_percent,
        "memory_mb": e.memory_mb,
        "status": e.status,
        "target_id": e.target_id,
        "finding_id": e.finding_id,
        "report_id": e.report_id,
        "metadata": _try_json(e.metadata_json),
        "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
    }


def _metric_rollup_to_dict(r: MetricRollup) -> dict[str, Any]:
    return {
        "id": r.id,
        "granularity": r.granularity,
        "period_start": r.period_start.isoformat() if r.period_start else None,
        "module": r.module,
        "pipeline": r.pipeline,
        "tool": r.tool,
        "event_type": r.event_type,
        "status": r.status,
        "count": r.count,
        "avg_duration_ms": r.avg_duration_ms,
        "p50_duration_ms": r.p50_duration_ms,
        "p95_duration_ms": r.p95_duration_ms,
        "min_duration_ms": r.min_duration_ms,
        "max_duration_ms": r.max_duration_ms,
        "total_duration_ms": r.total_duration_ms,
        "avg_cpu_percent": r.avg_cpu_percent,
        "avg_memory_mb": r.avg_memory_mb,
        "success_count": r.success_count,
        "failure_count": r.failure_count,
        "total_human_hours_saved": r.total_human_hours_saved,
    }


def _knowledge_asset_to_dict(a: KnowledgeAsset) -> dict[str, Any]:
    return {
        "id": a.id,
        "asset_type": a.asset_type,
        "domain": a.domain,
        "title": a.title,
        "description": a.description,
        "source": a.source,
        "source_url": a.source_url,
        "source_confidence": a.source_confidence,
        "content": _try_json(a.content_json),
        "evidence": _try_json(a.evidence_json),
        "impact_score": a.impact_score,
        "hit_count": a.hit_count,
        "reuse_count": a.reuse_count,
        "status": a.status,
        "last_validated": a.last_validated.isoformat() if a.last_validated else None,
        "validation_count": a.validation_count,
        "observation_count": a.observation_count,
        "evidence_summary": a.evidence_summary,
        "opportunity_cost_hours": a.opportunity_cost_hours,
        "implementation_effort": a.implementation_effort,
        "risk_level": a.risk_level,
        "tags": _try_json(a.tags_json),
        "version": a.version,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _try_json(value: str | None) -> Any:
    if not value:
        return None
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        return json.loads(value)
    return value
