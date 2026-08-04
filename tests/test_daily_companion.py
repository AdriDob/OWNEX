"""Tests for the Daily Companion System."""

from __future__ import annotations

from cores.direct_work_engine.daily_companion import daily_companion


def test_daily_companion_returns_all_blocks() -> None:
    result = daily_companion()
    assert set(result) >= {
        "generated_at",
        "system",
        "personal",
        "market",
        "focus",
        "briefing",
        "projection",
    }


def test_daily_companion_briefing_shape() -> None:
    result = daily_companion()
    briefing = result["briefing"]
    assert "greeting" in briefing
    assert "system_health" in briefing
    assert "important_tasks" in briefing
    assert "income_opportunities_analyzed" in briefing
    assert "recommended_actions" in briefing
    assert "focus_summary" in briefing
    assert "estimated_time_saved" in briefing


def test_daily_companion_focus_has_categories() -> None:
    result = daily_companion()
    focus = result["focus"]
    assert "stop" in focus
    assert "automate" in focus
    assert "delegate" in focus
    assert "improve" in focus
    assert "summary" in focus


def test_daily_companion_projection_requires_inputs() -> None:
    result = daily_companion()
    projection = result["projection"]
    # Without income/savings inputs, projection gives a note
    assert "note" in projection or projection.get("crossing_months") is not None


def test_daily_companion_with_income_inputs() -> None:
    result = daily_companion(
        work_income_usd_per_month=3000,
        savings_usd_per_month=1000,
        start_capital_usd=50_000,
        annual_return_rate=0.10,
        target_monthly_usd=100_000,
    )
    projection = result["projection"]
    assert "crossing_months" in projection
    assert "months_to_target" in projection


def test_daily_companion_greeting_is_valid() -> None:
    result = daily_companion()
    greeting = result["briefing"]["greeting"]
    assert greeting in ("Good morning", "Good afternoon", "Good evening")


def test_daily_companion_estimated_time_saved_format() -> None:
    result = daily_companion()
    saved = result["briefing"]["estimated_time_saved"]
    assert isinstance(saved, str)
    assert "minutes" in saved or saved == "0 minutes"
