from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.evolution.analyze import AnalyzeEngine
from core.evolution.rollup import RollupEngine
from database import db
from database.db import init_db
from database.models import Finding, KnowledgeAsset, MetricEvent, MetricRollup, Verdict


@pytest.fixture(autouse=True, scope="session")
def _ensure_tables():
    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    session = db.SessionLocal()
    try:
        session.query(MetricRollup).delete()
        session.query(MetricEvent).delete()
        session.query(KnowledgeAsset).delete()
        session.query(Finding).delete()
        session.query(Verdict).delete()
        session.commit()
    finally:
        session.close()
    yield
    session = db.SessionLocal()
    try:
        session.query(MetricRollup).delete()
        session.query(MetricEvent).delete()
        session.query(KnowledgeAsset).delete()
        session.query(Finding).delete()
        session.query(Verdict).delete()
        session.commit()
    finally:
        session.close()


def _insert_events(rows: list[dict]) -> None:
    session = db.SessionLocal()
    try:
        for kw in rows:
            e = MetricEvent(**{k: v for k, v in kw.items() if k != "_"})
            session.add(e)
        session.commit()
    finally:
        session.close()


# ── RollupEngine tests ────────────────────────────────


def test_rollup_empty() -> None:
    engine = RollupEngine()
    result = engine.run_hourly()
    assert result["groups"] == 0
    assert result["events"] == 0


def test_rollup_hourly_basic() -> None:
    now = datetime.now(UTC)
    hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    _insert_events(
        [
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "katana",
                "duration_ms": 1000.0,
                "timestamp": hour_start + timedelta(minutes=5),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "katana",
                "duration_ms": 2000.0,
                "timestamp": hour_start + timedelta(minutes=10),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "httpx",
                "duration_ms": 500.0,
                "timestamp": hour_start + timedelta(minutes=15),
            },
        ]
    )

    engine = RollupEngine()
    result = engine.run_hourly()
    assert result["groups"] >= 2
    assert result["events"] == 3


def test_rollup_daily() -> None:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    _insert_events(
        [
            {
                "module": "hermes",
                "event_type": "background_job",
                "duration_ms": 5000.0,
                "timestamp": day_start + timedelta(hours=2),
            },
        ]
    )

    engine = RollupEngine()
    result = engine.run_daily()
    assert result["groups"] >= 1
    assert result["events"] == 1


def test_rollup_duration_stats() -> None:
    now = datetime.now(UTC)
    hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    _insert_events(
        [
            {
                "module": "cateye",
                "event_type": "pipeline_stage",
                "pipeline": "recon",
                "duration_ms": 100.0,
                "timestamp": hour_start + timedelta(minutes=1),
            },
            {
                "module": "cateye",
                "event_type": "pipeline_stage",
                "pipeline": "recon",
                "duration_ms": 200.0,
                "timestamp": hour_start + timedelta(minutes=2),
            },
            {
                "module": "cateye",
                "event_type": "pipeline_stage",
                "pipeline": "recon",
                "duration_ms": 300.0,
                "timestamp": hour_start + timedelta(minutes=3),
            },
        ]
    )

    engine = RollupEngine()
    engine.run_hourly()

    session = db.SessionLocal()
    try:
        rollup = (
            session.query(MetricRollup)
            .filter(
                MetricRollup.granularity == "hourly",
                MetricRollup.event_type == "pipeline_stage",
            )
            .first()
        )
        assert rollup is not None
        assert rollup.count == 3
        assert rollup.avg_duration_ms == 200.0
        assert rollup.min_duration_ms == 100.0
        assert rollup.max_duration_ms == 300.0
        assert rollup.p50_duration_ms == 200.0
    finally:
        session.close()


# ── AnalyzeEngine tests ───────────────────────────────


def test_analyze_empty() -> None:
    engine = AnalyzeEngine()
    results = engine.run_full_cycle()
    assert results["level_1"]["event_count"] == 0
    assert len(results["level_2"]["bottlenecks"]) == 0
    assert len(results["level_4"]["assets_created"]) == 0


def test_analyze_descriptive_stats() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=14)
    _insert_events(
        [
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "katana",
                "duration_ms": 500.0,
                "timestamp": cutoff + timedelta(hours=1),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "katana",
                "duration_ms": 1500.0,
                "timestamp": cutoff + timedelta(hours=2),
            },
            {
                "module": "hermes",
                "event_type": "background_job",
                "duration_ms": 3000.0,
                "timestamp": cutoff + timedelta(hours=3),
                "status": "failed",
            },
        ]
    )

    engine = AnalyzeEngine()
    stats = engine._level_1_descriptive_stats(cutoff)
    assert stats["event_count"] == 3
    assert stats["by_tool"]["katana"]["count"] == 2
    assert stats["by_status"]["failed"] == 1
    assert stats["by_status"]["success"] == 2


def test_bottleneck_detection_no_data() -> None:
    cutoff = datetime.now(UTC)
    engine = AnalyzeEngine()
    result = engine._level_2_bottlenecks(cutoff)
    assert result["bottlenecks"] == []


def test_bottleneck_detection_with_tool() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=14)
    _insert_events(
        [
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "slow_tool",
                "duration_ms": 50_000.0,
                "timestamp": cutoff + timedelta(hours=1),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "slow_tool",
                "duration_ms": 60_000.0,
                "timestamp": cutoff + timedelta(hours=2),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "slow_tool",
                "duration_ms": 55_000.0,
                "timestamp": cutoff + timedelta(hours=3),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "slow_tool",
                "duration_ms": 45_000.0,
                "timestamp": cutoff + timedelta(hours=4),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "slow_tool",
                "duration_ms": 50_000.0,
                "timestamp": cutoff + timedelta(hours=5),
            },
            {
                "module": "cateye",
                "event_type": "tool_execution",
                "tool": "fast_tool",
                "duration_ms": 100.0,
                "timestamp": cutoff + timedelta(hours=1),
            },
        ]
    )

    engine = AnalyzeEngine()
    result = engine._level_2_bottlenecks(cutoff)
    bottlenecks = {b["name"]: b for b in result["bottlenecks"]}
    assert "slow_tool" in bottlenecks
    assert bottlenecks["slow_tool"]["status"] == "warning"
    assert bottlenecks["slow_tool"]["runs"] >= 5
    assert bottlenecks["slow_tool"]["total_hours"] > 0.05


def test_pattern_mining_empty() -> None:
    cutoff = datetime.now(UTC)
    engine = AnalyzeEngine()
    result = engine._level_3_patterns(cutoff)
    assert result["pattern_count"] >= 0  # some stats may have 0 observations


def test_asset_proposal_empty() -> None:
    engine = AnalyzeEngine()
    engine.run_full_cycle()
    # Should not crash on empty data
    assert "level_4" in engine.results


def test_rollup_has_correct_schema() -> None:
    now = datetime.now(UTC)
    hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    _insert_events(
        [
            {
                "module": "cateye",
                "event_type": "api_call",
                "duration_ms": 250.0,
                "timestamp": hour_start + timedelta(minutes=30),
                "status": "success",
            },
            {
                "module": "cateye",
                "event_type": "api_call",
                "duration_ms": 750.0,
                "timestamp": hour_start + timedelta(minutes=31),
                "status": "failed",
            },
        ]
    )

    engine = RollupEngine()
    engine.run_hourly()

    session = db.SessionLocal()
    try:
        rollups = session.query(MetricRollup).all()
        assert len(rollups) >= 1
        for r in rollups:
            assert r.granularity == "hourly"
            assert r.count > 0
            assert r.period_start is not None
    finally:
        session.close()


def test_rollup_empty_does_not_insert() -> None:
    engine = RollupEngine()
    result = engine.run_hourly()
    assert result["groups"] == 0

    session = db.SessionLocal()
    try:
        count = session.query(MetricRollup).count()
        assert count == 0
    finally:
        session.close()
