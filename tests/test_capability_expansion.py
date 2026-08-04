"""Tests for Capability Expansion Engine + its API surface.

Follows the project pattern: routers are mounted on an isolated FastAPI()
instance so the global CSRF middleware (present on api.main) doesn't block
POST routes in tests, matching tests/test_direct_work_api.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.capability_expansion import capabilities_router, router
from core.capabilities.expansion import (
    KNOWN_CANDIDATES,
    CapabilityExpansionEngine,
    reset_expansion_engine,
)
from core.capabilities.registry import CapabilityRegistry, reset_capability_registry


@pytest.fixture()
def registry(tmp_path: Path) -> CapabilityRegistry:
    return reset_capability_registry(store_path=tmp_path / "cap_registry.json")


@pytest.fixture()
def engine(registry: CapabilityRegistry, tmp_path: Path) -> CapabilityExpansionEngine:
    return reset_expansion_engine(registry=registry)
    # force a temp approvals store for test isolation


@pytest.fixture()
def client(registry: CapabilityRegistry, tmp_path: Path) -> TestClient:
    reset_expansion_engine(registry=registry)
    app = FastAPI()
    app.include_router(capabilities_router)
    app.include_router(router)
    return TestClient(app)


# ── Registry: persistence + metrics ───────────────────────────────


def test_registry_persists_across_instances(tmp_path: Path) -> None:
    store = tmp_path / "cap.json"
    r1 = CapabilityRegistry(store_path=store)
    r1.register("send_email", "outlook", {"category": "ai"})
    r1.record_usage("send_email", duration_ms=120.0)
    r1.set_health("send_email", 0.9)

    r2 = CapabilityRegistry(store_path=store)
    entry = r2.get_entry("send_email", "outlook")
    assert entry is not None
    assert entry.category == "ai"
    assert entry.usage_count == 1
    assert entry.health == 0.9


def test_record_usage_tracks_average_performance(registry: CapabilityRegistry) -> None:
    registry.register("web_scraping", "httpx")
    registry.record_usage("web_scraping", duration_ms=100.0)
    registry.record_usage("web_scraping", duration_ms=300.0)
    entry = registry.get_entry("web_scraping", "httpx")
    assert entry is not None
    assert entry.usage_count == 2
    assert entry.avg_performance_ms == 200.0


def test_set_status_and_stats(registry: CapabilityRegistry) -> None:
    registry.register("a", "m1", {"category": "ai"})
    registry.register("b", "m2", {"category": "data"})
    registry.set_status("b", "broken")
    stats = registry.stats()
    assert stats["total_entries"] == 2
    assert stats["active"] == 1
    assert stats["broken"] == 1
    assert "ai" in stats["categories"] and "data" in stats["categories"]


# ── Expansion Engine: detect gaps ─────────────────────────────────


def test_detect_gaps_returns_layers(engine: CapabilityExpansionEngine) -> None:
    gaps = engine.detect_gaps()
    assert isinstance(gaps, list)
    assert all("layer" in g and "capabilities" in g for g in gaps)
    # There are curated candidates missing from an empty registry
    total = sum(g["count"] for g in gaps)
    assert total >= 10


def test_registered_capability_not_a_gap(engine: CapabilityExpansionEngine, registry: CapabilityRegistry) -> None:
    # Register one canonical capability that exists among candidates
    target = KNOWN_CANDIDATES[0].capability
    registry.register(target, "test")
    gaps = engine.detect_gaps()
    gap_ids = {cap["capability"] for g in gaps for cap in g["capabilities"]}
    assert target not in gap_ids


# ── Expansion Engine: evaluate ────────────────────────────────────


def test_evaluate_safe_local_candidate_scores_high(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if not c.requires_approval)
    result = engine.evaluate_candidate(target)
    assert result["capability"] == target.capability
    assert 0.0 <= result["score"] <= 100.0
    assert result["decision"] in ("approve_auto", "needs_approval")


def test_evaluate_critical_candidate_needs_approval(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if c.requires_approval)
    result = engine.evaluate_candidate(target)
    assert result["decision"] == "needs_approval"


def test_evaluate_unknown_capability_rejects(engine: CapabilityExpansionEngine) -> None:
    result = engine.evaluate_candidate({"capability": "", "category": "ai"})
    assert result["decision"] == "reject"


# ── Expansion Engine: install + approval flow ─────────────────────


def test_safe_install_dry_run(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if not c.requires_approval)
    result = engine.install_candidate(target.capability, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert engine._registry.has_capability(target.capability) is False  # type: ignore[attr-defined]


def test_safe_install_registers_and_persists(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if not c.requires_approval)
    result = engine.install_candidate(target.capability, dry_run=False)
    assert result["ok"] is True
    assert result["dry_run"] is False
    entry = engine._registry.get_entry(target.capability, "expansion_engine")  # type: ignore[attr-defined]
    assert entry is not None
    assert entry.category == target.category


def test_critical_install_queues_for_approval(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if c.requires_approval)
    result = engine.install_candidate(target.capability, dry_run=False)
    assert result["ok"] is False
    assert result["needs_approval"] is True
    assert len(engine.pending_approvals()) == 1
    # not registered yet
    assert engine._registry.has_capability(target.capability) is False  # type: ignore[attr-defined]


def test_approve_registers_critical(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if c.requires_approval)
    res = engine.install_candidate(target.capability, dry_run=False)
    approval_id = res["approval_id"]
    decision = engine.approve(approval_id, granted=True)
    assert decision["approved"] is True
    assert engine._registry.has_capability(target.capability) is True  # type: ignore[attr-defined]
    assert len(engine.pending_approvals()) == 0


def test_deny_approval_does_not_register(engine: CapabilityExpansionEngine) -> None:
    target = next(c for c in KNOWN_CANDIDATES if c.requires_approval)
    res = engine.install_candidate(target.capability, dry_run=False)
    decision = engine.approve(res["approval_id"], granted=False)
    assert decision["ok"] is True
    assert decision["approved"] is False
    assert engine._registry.has_capability(target.capability) is False  # type: ignore[attr-defined]


# ── Self-improvement suggestions ──────────────────────────────────


def test_suggest_improvements_templates() -> None:
    engine = reset_expansion_engine(registry=None)
    suggestions = engine.suggest_improvements()
    assert len(suggestions) >= 10
    assert all("template" in s and "recommended_action" in s for s in suggestions)
    assert all(s["recommended_action"] in ("register", "install") for s in suggestions)


# ── API surface ───────────────────────────────────────────────────


def test_get_stats(client: TestClient) -> None:
    resp = client.get("/api/capabilities/stats")
    assert resp.status_code == 200
    assert "total_entries" in resp.json()


def test_get_gaps_api(client: TestClient) -> None:
    resp = client.get("/api/capability-expansion/gaps")
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body and "layers" in body


def test_get_suggestions_api(client: TestClient) -> None:
    resp = client.get("/api/capability-expansion/suggestions")
    assert resp.status_code == 200
    assert "suggestions" in resp.json()


def test_install_api_dry_run_default(client: TestClient) -> None:
    target = next(c for c in KNOWN_CANDIDATES if not c.requires_approval)
    resp = client.post("/api/capability-expansion/install", json={"capability": target.capability})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["dry_run"] is True


def test_record_usage_api(client: TestClient) -> None:
    # register via engine so there's an entry to record against
    from core.capabilities.registry import get_capability_registry

    get_capability_registry().register("test_cap_x", "test")
    resp = client.post("/api/capabilities/test_cap_x/usage", json={"duration_ms": 50.0})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ── Daily Evolution Report / Marketplace ──────────────────────────


def test_marketplace_coverage_has_bars(engine: CapabilityExpansionEngine) -> None:
    bars = engine.marketplace_coverage()
    assert len(bars) >= 1
    for bar in bars:
        assert "category" in bar and "coverage_pct" in bar
        assert 0 <= bar["coverage_pct"] <= 100


def test_daily_evolution_report_shape(engine: CapabilityExpansionEngine) -> None:
    report = engine.daily_evolution_report()
    assert "generated_at" in report
    assert "marketplace" in report and isinstance(report["marketplace"], list)
    assert "tools_integrated" in report
    assert "discovered_remaining" in report and isinstance(report["discovered_remaining"], list)
    assert "recommended_upgrades" in report and isinstance(report["recommended_upgrades"], list)
    assert "pending_approvals" in report
    assert "tools_tested" in report


def test_daily_report_api(client: TestClient) -> None:
    resp = client.get("/api/capability-expansion/daily-report")
    assert resp.status_code == 200
    body = resp.json()
    assert "marketplace" in body and "discovered_remaining" in body


def test_marketplace_api(client: TestClient) -> None:
    resp = client.get("/api/capability-expansion/marketplace")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body and isinstance(body["categories"], list)
