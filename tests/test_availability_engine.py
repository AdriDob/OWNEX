"""Availability Intelligence (P0-4) — señal real de task_available.

Estados spec §7: AVAILABLE/LIMITED/UNKNOWN/UNAVAILABLE/STALE.
Regla de oro: jamás inventa — known SOLO con observación fresca de un
productor real; UNKNOWN/STALE delegan al warning del SSOT económico.
"""

from __future__ import annotations

import pytest

from cores.revenue.availability import (
    AvailabilityMonitor,
    AvailabilityState,
    Observation,
    get_availability_monitor,
    reset_availability_monitor,
    state_from_observation,
)


@pytest.fixture(autouse=True)
def _isolated_monitor(tmp_path, monkeypatch):
    """Cada test usa su propio store aislado + singleton fresco."""
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path / "ownex"))
    reset_availability_monitor()
    yield
    reset_availability_monitor()


NOW = 1_800_000_000.0


def test_no_observation_is_unknown_never_assumed() -> None:
    monitor = AvailabilityMonitor(store_path="/tmp/opencode/nonexistent_avail.json")
    verdict = monitor.assess("plataforma-nueva")
    assert verdict.state is AvailabilityState.UNKNOWN
    ta, v = monitor.task_availability_for("plataforma-nueva")
    assert not ta.known  # UNKNOWN ≠ 100%: el factor se EXCLUYE del EV


def test_fresh_observation_with_many_items_is_available() -> None:
    monitor = AvailabilityMonitor(store_path="/tmp/opencode/nonexistent_avail.json")
    monitor.record("gitcoin.co", items_seen=12)
    ta, verdict = monitor.task_availability_for("GITCOIN.CO")  # case-insensitive
    assert verdict.state is AvailabilityState.AVAILABLE
    assert ta.known and ta.value == pytest.approx(1.0)


def test_zero_items_after_successful_fetch_is_unavailable() -> None:
    obs = Observation(items_seen=0, observed_at=NOW - 3600)
    state, reason = state_from_observation(obs, now=NOW)
    assert state is AvailabilityState.UNAVAILABLE
    assert "0 items" in reason


def test_stale_observation_downgrades_to_unknown_factor() -> None:
    monitor = AvailabilityMonitor(store_path="/tmp/opencode/nonexistent_avail.json")
    old = NOW - 8 * 86400  # > FRESHNESS_DAYS (7)
    monitor._observations["old.io"] = Observation(items_seen=10, observed_at=old).to_dict()
    ta, verdict = monitor.task_availability_for("old.io", now=NOW)
    assert verdict.state is AvailabilityState.STALE
    assert not ta.known  # stale no puede multiplicar el EV como si existiera


def test_limited_items_use_policy_multiplier() -> None:
    monitor = AvailabilityMonitor(store_path="/tmp/opencode/nonexistent_avail.json")
    monitor.record("few.io", items_seen=2)
    ta, verdict = monitor.task_availability_for("few.io")
    assert verdict.state is AvailabilityState.LIMITED
    assert ta.known and ta.value == pytest.approx(0.5)


def test_persistence_roundtrip(tmp_path) -> None:
    store = tmp_path / "ownex" / "availability.json"
    m1 = AvailabilityMonitor(store_path=store)
    m1.record("persist.io", items_seen=9)
    m2 = AvailabilityMonitor(store_path=store)
    assert m2.assess("persist.io").state is AvailabilityState.AVAILABLE


def test_singleton_respects_ownex_data_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path / "ownex"))
    get_availability_monitor().record("single.io", items_seen=5)
    store = tmp_path / "ownex" / "availability.json"
    assert store.exists()


def test_evscorer_consumes_real_signal(monkeypatch, tmp_path):
    """El scorer delega la disponibilidad observada al EV (spec §7:
    $40/h sin tareas NO supera $15/h disponibles)."""
    from cores.direct_work_engine.autonomous_discovery import EVScorer
    from cores.direct_work_engine.models import (
        Opportunity,
        OpportunityCategory,
        WorkPlatform,
    )

    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path / "ownex"))
    reset_availability_monitor()

    scorer = EVScorer()

    def make_opp(opp_id: str, payment: float) -> Opportunity:
        return Opportunity(
            id=opp_id,
            title="t",
            platform=WorkPlatform.ALGORA,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=payment,
            estimated_time_hours=4.0,
        )

    rich_unavailable = make_opp("rich", 160.0)  # $40/h pero SIN tareas observadas
    poor_available = make_opp("poor", 60.0)  # $15/h con tareas observadas

    mon = get_availability_monitor()
    mon.record(WorkPlatform.ALGORA.value, items_seen=0)
    score_rich = scorer.score(rich_unavailable)
    mon.record(WorkPlatform.ALGORA.value, items_seen=15)
    score_poor = scorer.score(poor_available)

    # La disponible gana aunque pague 2.6x menos por hora nominal.
    assert score_rich.total_ev_usd == pytest.approx(0.0)
    assert score_poor.total_ev_usd > 0.0
