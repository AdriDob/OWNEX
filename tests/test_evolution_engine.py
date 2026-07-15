from __future__ import annotations

import pytest

from core.evolution.engine import EvolutionEngine, get_evolution_engine, init_evolution_engine
from database import db
from database.db import init_db
from database.models import KnowledgeAsset, MetricEvent


@pytest.fixture(autouse=True, scope="session")
def _ensure_tables():
    """Create tables once per session."""
    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure a clean slate for each test."""
    session = db.SessionLocal()
    try:
        session.query(MetricEvent).delete()
        session.query(KnowledgeAsset).delete()
        session.commit()
    finally:
        session.close()
    yield
    session = db.SessionLocal()
    try:
        session.query(MetricEvent).delete()
        session.query(KnowledgeAsset).delete()
        session.commit()
    finally:
        session.close()


def test_engine_singleton() -> None:
    e1 = get_evolution_engine()
    e2 = get_evolution_engine()
    assert e1 is e2


def test_engine_init() -> None:
    engine = init_evolution_engine()
    assert engine is not None
    assert isinstance(engine, EvolutionEngine)


def test_record_event() -> None:
    engine = get_evolution_engine()
    event_id = engine.record_event(
        module="cateye",
        event_type="tool_execution",
        tool="katana",
        duration_ms=1234.5,
        status="success",
    )
    assert event_id > 0

    events = engine.query_events(module="cateye", limit=10)
    assert len(events) >= 1
    assert events[0]["module"] == "cateye"
    assert events[0]["tool"] == "katana"
    assert events[0]["duration_ms"] == 1234.5


def test_record_event_with_metadata() -> None:
    engine = get_evolution_engine()
    event_id = engine.record_event(
        module="cateye",
        event_type="pipeline_stage",
        pipeline="recon",
        duration_ms=5000.0,
        status="success",
        target_id=42,
        metadata={"depth": 3, "urls_found": 150},
    )
    assert event_id > 0

    events = engine.query_events(event_type="pipeline_stage", limit=10)
    matching = [e for e in events if e["id"] == event_id]
    assert len(matching) == 1
    assert matching[0]["target_id"] == 42
    assert matching[0]["metadata"]["depth"] == 3


def test_query_events_with_filters() -> None:
    engine = get_evolution_engine()
    engine.record_event(module="cateye", event_type="tool_execution", tool="nuclei", duration_ms=100.0)
    engine.record_event(module="cateye", event_type="tool_execution", tool="httpx", duration_ms=200.0)
    engine.record_event(module="hermes", event_type="background_job", tool="backup", duration_ms=300.0)

    cateye_events = engine.query_events(module="cateye", limit=10)
    assert len(cateye_events) == 2

    nuclei_events = engine.query_events(tool="nuclei", limit=10)
    assert len(nuclei_events) == 1

    hermes_events = engine.query_events(module="hermes", limit=10)
    assert len(hermes_events) == 1


def test_count_events() -> None:
    engine = get_evolution_engine()
    assert engine.count_events() == 0
    engine.record_event(module="cateye", event_type="test")
    engine.record_event(module="cateye", event_type="test")
    assert engine.count_events() == 2
    assert engine.count_events(module="cateye") == 2
    assert engine.count_events(module="hermes") == 0


def test_record_event_buffered_and_flush() -> None:
    engine = get_evolution_engine()
    for i in range(10):
        engine.record_event_buffered(
            module="cateye",
            event_type="test_buffered",
            duration_ms=float(i * 10),
        )
    assert len(engine._metric_buffer) == 10

    flushed = engine.flush_metric_buffer()
    assert flushed == 10
    assert len(engine._metric_buffer) == 0
    assert engine.count_events(event_type="test_buffered") == 10


def test_record_event_failure_returns_minus_one() -> None:
    engine = get_evolution_engine()
    # Empty module should still work (defaults to "unknown")
    result = engine.record_event(module="", event_type="")
    assert result > 0  # should succeed with defaults


def test_create_knowledge_asset() -> None:
    engine = get_evolution_engine()
    asset_id = engine.create_asset(
        asset_type="heuristic",
        domain="cateye",
        title="React + GraphQL → IDOR probability +17%",
        description="Findings from fintech programs show React+GraphQL stack correlates with higher IDOR rates",
        source="own_data",
        source_confidence=0.75,
        content={"baseline": 0.12, "with_stack": 0.29, "sample_size": 412},
        tags=["idor", "react", "graphql", "fintech"],
    )
    assert asset_id > 0

    assets = engine.get_assets(domain="cateye", limit=10)
    assert len(assets) == 1
    assert assets[0]["asset_type"] == "heuristic"
    assert assets[0]["title"].startswith("React")
    assert assets[0]["tags"] == ["idor", "react", "graphql", "fintech"]


def test_create_and_retrieve_knowledge_asset() -> None:
    engine = get_evolution_engine()
    asset_id = engine.create_asset(
        asset_type="pattern",
        domain="cateye",
        title="/internal/export → high ROI",
    )
    assert asset_id > 0

    asset = engine.get_asset(asset_id)
    assert asset is not None
    assert asset["id"] == asset_id
    assert asset["title"] == "/internal/export → high ROI"
    assert asset["status"] == "draft"


def test_get_nonexistent_asset() -> None:
    engine = get_evolution_engine()
    assert engine.get_asset(99999) is None


def test_update_asset_status() -> None:
    engine = get_evolution_engine()
    asset_id = engine.create_asset(
        asset_type="rule",
        domain="cateye",
        title="Skip Dalfox if Content-Type != text/html",
    )
    assert asset_id > 0

    ok = engine.update_asset_status(asset_id, "validated", impact_score=0.85)
    assert ok is True

    asset = engine.get_asset(asset_id)
    assert asset["status"] == "validated"
    assert asset["impact_score"] == 0.85
    assert asset["validation_count"] >= 1


def test_update_nonexistent_asset_status() -> None:
    engine = get_evolution_engine()
    ok = engine.update_asset_status(99999, "validated")
    assert ok is False


def test_delete_asset() -> None:
    engine = get_evolution_engine()
    asset_id = engine.create_asset(
        asset_type="template",
        domain="cross",
        title="Test template",
    )
    assert asset_id > 0
    assert engine.get_asset(asset_id) is not None

    ok = engine.delete_asset(asset_id)
    assert ok is True
    assert engine.get_asset(asset_id) is None


def test_delete_nonexistent_asset() -> None:
    engine = get_evolution_engine()
    assert engine.delete_asset(99999) is False


def test_get_assets_with_filters() -> None:
    engine = get_evolution_engine()
    engine.create_asset(asset_type="heuristic", domain="cateye", title="H1")
    engine.create_asset(asset_type="statistic", domain="cateye", title="S1")
    engine.create_asset(asset_type="heuristic", domain="atlas", title="H2")

    cateye = engine.get_assets(domain="cateye")
    assert len(cateye) == 2

    heuristics = engine.get_assets(asset_type="heuristic")
    assert len(heuristics) == 2

    cateye_heuristics = engine.get_assets(domain="cateye", asset_type="heuristic")
    assert len(cateye_heuristics) == 1

    atlas = engine.get_assets(domain="atlas")
    assert len(atlas) == 1


def test_get_empty_summary() -> None:
    engine = get_evolution_engine()
    summary = engine.get_summary(granularity="daily")
    assert summary == []


def test_metric_event_timestamps() -> None:
    engine = get_evolution_engine()
    eid = engine.record_event(module="cateye", event_type="test_ts")
    assert eid > 0

    events = engine.query_events(limit=1)
    assert len(events) == 1
    assert events[0]["timestamp"] is not None
    assert events[0]["recorded_at"] is not None


def test_overflow_module_name() -> None:
    engine = get_evolution_engine()
    long_name = "x" * 500
    eid = engine.record_event(module=long_name, event_type="test_long")
    assert eid > 0
