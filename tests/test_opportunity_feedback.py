"""Tests for opportunity feedback loop."""

import pytest

from cores.opportunity.feedback import FeedbackLoop, FeedbackOutcome, get_feedback_loop


@pytest.fixture
def feedback_loop():
    """Create a fresh feedback loop instance for testing."""
    return FeedbackLoop()


def test_record_feedback(feedback_loop):
    """Test recording feedback for an opportunity."""
    feedback_loop.record_feedback(
        opportunity_id="test-opp-1",
        outcome=FeedbackOutcome.ACCEPTED,
        category="web3",
        platform="immunefi",
        technology_tags=["solidity", "defi"],
        estimated_payout=5000.0,
        actual_payout=4800.0,
        reasoning="Good fit for skills",
    )

    history = feedback_loop.get_feedback_history(opportunity_id="test-opp-1")
    assert len(history) == 1
    # MemoryStore.get() returns the details dict directly
    assert history[0]["outcome"] == "accepted"
    assert history[0]["category"] == "web3"
    assert history[0]["platform"] == "immunefi"


def test_record_multiple_feedback(feedback_loop):
    """Test recording multiple feedback entries."""
    feedback_loop.record_feedback(
        opportunity_id="test-opp-2",
        outcome=FeedbackOutcome.ACCEPTED,
        category="platform",
        platform="hackerone",
        technology_tags=["api"],
    )

    feedback_loop.record_feedback(
        opportunity_id="test-opp-3",
        outcome=FeedbackOutcome.REJECTED,
        category="platform",
        platform="hackerone",
        technology_tags=["web"],
    )

    history = feedback_loop.get_feedback_history(category="platform")
    assert len(history) >= 2


def test_category_multiplier_computation():
    """Test category multiplier computation logic directly."""
    # Test with empty history
    loop = FeedbackLoop()
    assert loop.compute_category_multiplier("web3") == 1.0

    # Mock high acceptance scenario
    loop._cache = {"web3_feedback": {"accepted": 7, "rejected": 3}}
    # This would need the actual implementation to use cache


def test_platform_multiplier_computation():
    """Test platform multiplier computation logic directly."""
    loop = FeedbackLoop()
    assert loop.compute_platform_multiplier("bugcrowd") == 1.0


def test_technology_multiplier_computation():
    """Test technology multiplier computation logic directly."""
    loop = FeedbackLoop()
    assert loop.compute_technology_multiplier("api") == 1.0


def test_personalized_multipliers(feedback_loop):
    """Test combined personalized multipliers."""
    feedback_loop.record_feedback(
        opportunity_id="test-opp-1",
        outcome=FeedbackOutcome.ACCEPTED,
        category="web3",
        platform="immunefi",
        technology_tags=["solidity", "defi"],
    )

    multipliers = feedback_loop.get_personalized_multipliers(
        category="web3",
        platform="immunefi",
        technology_tags=["solidity", "defi"],
    )

    assert "category_multiplier" in multipliers
    assert "platform_multiplier" in multipliers
    assert "technology_multiplier" in multipliers
    assert "combined_multiplier" in multipliers


def test_feedback_summary(feedback_loop):
    """El resumen EXCLUYE los fixtures de test.

    Este test escribía 8 registros `test-opp-*` y después exigía
    `total_feedback >= 8`. Como los tests escriben en el mismo
    MemoryStore que producción, el resumen de Learn from Outcomes estaba
    compuesto por datos de prueba: una `acceptance_rate` que mide tests,
    no submits. Lo que se verifica ahora es el contrato correcto: los
    fixtures se excluyen y se cuentan aparte.
    """
    for i in range(5):
        feedback_loop.record_feedback(
            opportunity_id=f"test-opp-accepted-{i}",
            outcome=FeedbackOutcome.ACCEPTED,
            category="platform",
            platform="hackerone",
            technology_tags=["api"],
        )

    for i in range(3):
        feedback_loop.record_feedback(
            opportunity_id=f"test-opp-rejected-{i}",
            outcome=FeedbackOutcome.REJECTED,
            category="platform",
            platform="bugcrowd",
            technology_tags=["web"],
        )

    summary = feedback_loop.get_feedback_summary()
    assert summary["excluded_fixtures"] >= 8, "los 8 fixtures de este test deben quedar fuera"
    for key in summary["by_category"]:
        assert "test-opp" not in key, f"categoría de fixture filtrada: {key}"
    for key, counts in summary["by_platform"].items():
        assert key not in ("hackerone", "bugcrowd") or sum(counts.values()) == 0, (
            f"fixture filtrado pero summarised en platform={key}: {counts}"
        )
    assert "by_category" in summary
    assert "by_platform" in summary


def test_feedback_summary_cuenta_un_registro_real_y_limpia(feedback_loop):
    """Un registro con clave real SÍ se cuenta, y el outcome se lee bien.

    Cubre el segundo bug del mismo bloque: `get_feedback_history()` ya
    devuelve el `details` interno, así que leer `h["details"]["outcome"]`
    sobre eso daba `{}` siempre ⇒ los 960 registros se contaban como
    "unknown" y `accepted / total` rendía 0.0 — "rechazaste el 100%"
    cuando la verdad era "no hay outcomes clasificados".

    Se usa una clave sin prefijo de fixture y se borra al final: si se
    dejara, volvería a contaminar el learning real.
    """
    from cores.memory.memory_store import MemoryStore
    from cores.opportunity.feedback import _FEEDBACK_CATEGORY

    real_id = "realtest-opp-outcome-probe"
    store = MemoryStore()
    try:
        feedback_loop.record_feedback(
            opportunity_id=real_id,
            outcome=FeedbackOutcome.ACCEPTED,
            category="probe_category",
            platform="probe_platform",
            technology_tags=["probe"],
        )
        feedback_loop.record_feedback(
            opportunity_id=f"{real_id}-rej",
            outcome=FeedbackOutcome.REJECTED,
            category="probe_category",
            platform="probe_platform",
            technology_tags=["probe"],
        )

        summary = feedback_loop.get_feedback_summary()
        assert summary["accepted"] >= 1, "el outcome no se está leyendo"
        assert summary["rejected"] >= 1
        assert summary["classified"] >= 2
        assert summary["acceptance_rate"] is not None, "con outcomes clasificados ya no es UNKNOWN"
        assert 0.0 <= summary["acceptance_rate"] <= 1.0
        assert "1/" in summary["acceptance_rate_basis"] or summary["accepted"] >= 1
    finally:
        store.delete(_FEEDBACK_CATEGORY, real_id)
        store.delete(_FEEDBACK_CATEGORY, f"{real_id}-rej")


def test_feedback_outcome_enum():
    """Test FeedbackOutcome enum values."""
    assert FeedbackOutcome.ACCEPTED.value == "accepted"
    assert FeedbackOutcome.REJECTED.value == "rejected"
    assert FeedbackOutcome.SKIPPED.value == "skipped"


def test_get_feedback_loop_singleton():
    """Test that get_feedback_loop returns the same instance."""
    loop1 = get_feedback_loop()
    loop2 = get_feedback_loop()
    assert loop1 is loop2


def test_empty_history(feedback_loop):
    """Test behavior with empty history."""
    # Note: This may not be truly empty if DB has accumulated data
    multiplier = feedback_loop.compute_category_multiplier("web3")
    # Default multiplier when no data
    assert multiplier == 1.0 or 0.6 <= multiplier <= 1.2

    summary = feedback_loop.get_feedback_summary()
    # May have accumulated data from other tests
    assert "total_feedback" in summary
    assert "acceptance_rate" in summary
