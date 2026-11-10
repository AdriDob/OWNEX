"""Regression tests for verified financial inputs and capital projections."""

from __future__ import annotations


def test_monte_carlo_projection_uses_expected_returns() -> None:
    from cores.capital.maximizer_advanced import monte_carlo_projection

    result = monte_carlo_projection(
        current_portfolio={"cash": 1_000.0},
        expected_returns={"cash": 0.12},
        volatilities={"cash": 0.0},
        months=12,
        simulations=10,
    )

    assert result["projections"]["month_12"]["p50"] > result["current_value"]


def test_firefly_balances_do_not_inject_placeholder_values() -> None:
    from cores.financial.dashboard import _get_firefly_balances

    assert _get_firefly_balances() == {}


def test_revenue_ledger_availability_exports_are_defined() -> None:
    from cores.opportunity import revenue_ledger

    for name in ("compute_availability_score", "evaluate_availability", "is_available"):
        assert callable(getattr(revenue_ledger, name))
