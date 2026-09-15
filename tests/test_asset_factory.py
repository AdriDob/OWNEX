"""ASSET_FACTORY — construir 1 vez → vender N veces."""

from __future__ import annotations

import pytest

from cores.asset_factory.engine import AssetFactoryEngine
from cores.asset_factory.models import GATE_CRITERIA, AssetStatus, AssetType


@pytest.fixture
def tmp_engine(tmp_path):
    return AssetFactoryEngine(path=tmp_path / "assets.json")


def _gate_ok() -> dict[str, bool]:
    return {c: True for c in GATE_CRITERIA}


def test_create_and_gate(tmp_engine):
    a = tmp_engine.create(
        "API de facturación", AssetType.API, problem="Empresas pierden horas facturando", human_hours_est=12
    )
    assert a.status == AssetStatus.IDEA
    assert not a.gate_passed
    assert tmp_engine.score(a)["score"] == 0.0
    tmp_engine.set_gate(a.asset_id, _gate_ok())
    a2 = tmp_engine.get(a.asset_id)
    assert a2 is not None and a2.gate_passed is True
    sc = tmp_engine.score(a2)
    assert sc["score"] > 0 and sc["gate_passed"] is True


def test_gate_must_pass_before_building(tmp_engine):
    a = tmp_engine.create("Template Vue", AssetType.TEMPLATE)
    ok, msg = tmp_engine.advance(a.asset_id, AssetStatus.BUILDING)
    assert not ok and "gate_not_passed" in msg
    tmp_engine.set_gate(a.asset_id, _gate_ok())
    ok, _ = tmp_engine.advance(a.asset_id, AssetStatus.BUILDING)
    assert ok


def test_monetizing_requires_revenue(tmp_engine):
    a = tmp_engine.create("Dataset AR", AssetType.DATASET)
    tmp_engine.set_gate(a.asset_id, _gate_ok())
    tmp_engine.advance(a.asset_id, AssetStatus.BUILDING)
    tmp_engine.advance(a.asset_id, AssetStatus.PUBLISHED)
    ok, msg = tmp_engine.advance(a.asset_id, AssetStatus.MONETIZING)
    assert not ok and "no_revenue" in msg
    tmp_engine.update(a.asset_id, sales_count=1, revenue_total_usd=29.0)
    ok, _ = tmp_engine.advance(a.asset_id, AssetStatus.MONETIZING)
    assert ok


def test_score_boosts_repeatability_and_ownex(tmp_engine):
    a1 = tmp_engine.create("Tool A", AssetType.DEV_TOOL, human_hours_est=10)
    tmp_engine.set_gate(a1.asset_id, _gate_ok())
    s1 = tmp_engine.score(a1)["score"]
    tmp_engine.update(a1.asset_id, sales_count=15, mrr_usd=99.0)
    a1b = tmp_engine.get(a1.asset_id)
    s2 = tmp_engine.score(a1b)["score"]
    assert s2 > s1  # repeatability boost


def test_ranked_and_next_action(tmp_engine):
    a1 = tmp_engine.create("SaaS 1", AssetType.MICRO_SAAS, human_hours_est=20)
    a2 = tmp_engine.create("SaaS 2", AssetType.MICRO_SAAS, human_hours_est=5)
    tmp_engine.set_gate(a1.asset_id, _gate_ok())
    tmp_engine.set_gate(a2.asset_id, _gate_ok())
    ranked = tmp_engine.ranked()
    assert ranked[0][0].asset_id == a2.asset_id  # fewer hours → higher score
    nxt = tmp_engine.next_action()
    assert nxt is not None and nxt["action"] == "build"
    assert nxt["asset_id"] == a2.asset_id


def test_next_action_suggests_gate_completion(tmp_engine):
    a = tmp_engine.create("Idea sin gate", AssetType.PLUGIN)
    tmp_engine.set_gate(a.asset_id, {c: (c == "demanda_observable") for c in GATE_CRITERIA})
    nxt = tmp_engine.next_action()
    assert nxt is not None and nxt["action"] == "complete_gate"
    assert "costo_inicial_0" in nxt["missing"]


def test_pipeline_stats(tmp_engine):
    a = tmp_engine.create("Pack", AssetType.DIGITAL_PRODUCT, human_hours_est=4)
    tmp_engine.set_gate(a.asset_id, _gate_ok())
    stats = tmp_engine.pipeline_stats()
    assert stats["total"] == 1
    assert stats["gate_passed"] == 1
    assert stats["by_status"]["idea"] == 1


def test_persistence_roundtrip(tmp_path):
    p = tmp_path / "assets.json"
    e1 = AssetFactoryEngine(path=p)
    e1.create("Persist Me", AssetType.API, problem="test")
    e2 = AssetFactoryEngine(path=p)
    assert len(e2.list()) == 1
    assert e2.list()[0].title == "Persist Me"
