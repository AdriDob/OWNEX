"""Tests Economic Trajectory — REAL/PIPELINE/SCENARIO nunca mezclados (spec §36)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cores.economic_trajectory.trajectory import (
    build_trajectory,
    calibrate_scenarios,
    calibration_level,
    channel_economics,
    channel_validation,
    compare_scenario_to_real,
    gap_to_target,
    scenarios_block,
)

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _row(state: str, amount: float, days_ago: int = 5, channel: str = "ownex") -> dict:
    ts = NOW - timedelta(days=days_ago)
    return {
        "revenue_state": state,
        "amount": amount,
        "channel": channel,
        "created_at": ts.isoformat(),
        "updated_at": ts.isoformat(),
    }


class TestStateSeparation:
    def test_paid_is_real_cash(self) -> None:
        t = build_trajectory([_row("paid", 500.0)], now=NOW)
        assert t.real_365d.realized_cash == 500.0
        assert t.real_365d.paid_outcomes == 1

    def test_accepted_is_not_paid(self) -> None:
        t = build_trajectory([_row("accepted", 900.0)], now=NOW)
        assert t.real_365d.realized_cash == 0.0
        assert t.real_365d.pipeline_value == 900.0

    def test_potential_excluded_from_cash(self) -> None:
        t = build_trajectory([_row("potential", 10000.0), _row("expected", 5000.0)], now=NOW)
        assert t.real_365d.realized_cash == 0.0
        assert t.speculative_value == 15000.0

    def test_net_state_counts_as_real(self) -> None:
        t = build_trajectory([_row("net", 300.0)], now=NOW)
        assert t.real_365d.realized_cash == 300.0

    def test_speculative_never_counted_as_cash_in_dict(self) -> None:
        d = build_trajectory([_row("potential", 1.0)], now=NOW).to_dict()
        assert d["speculative"]["counted_as_cash"] is False


class TestWindows:
    def test_90d_excludes_older(self) -> None:
        rows = [_row("paid", 100.0, days_ago=10), _row("paid", 200.0, days_ago=200)]
        t = build_trajectory(rows, now=NOW)
        assert t.real_90d.realized_cash == 100.0
        assert t.real_365d.realized_cash == 300.0

    def test_180d_window(self) -> None:
        rows = [_row("paid", 100.0, days_ago=10), _row("paid", 200.0, days_ago=150)]
        assert build_trajectory(rows, now=NOW).real_180d.realized_cash == 300.0

    def test_monthly_shape(self) -> None:
        d = build_trajectory([], now=NOW).to_dict()["real"]
        assert {"d90", "d180", "d365"} <= set(d)


class TestCashPerHour:
    def test_rate_requires_hours_and_paid(self) -> None:
        rows = [_row("paid", 1000.0)]
        assert build_trajectory(rows, hours_by_period={"d365": 10.0}, now=NOW).real_365d.net_cash_per_hour == 100.0

    def test_no_division_by_zero(self) -> None:
        assert (
            build_trajectory([_row("paid", 500.0)], hours_by_period={"d365": 0.0}, now=NOW).real_365d.net_cash_per_hour
            is None
        )

    def test_no_fake_rate_without_paid(self) -> None:
        t = build_trajectory([_row("expected", 500.0)], hours_by_period={"d365": 10.0}, now=NOW)
        assert t.real_365d.net_cash_per_hour is None

    def test_negative_hours_never_negative(self) -> None:
        t = build_trajectory([_row("paid", 100.0)], hours_by_period={"d365": -5.0}, now=NOW)
        assert t.real_365d.hours_used == 0.0

    def test_negative_amount_treated_zero(self) -> None:
        assert build_trajectory([_row("paid", -50.0)], now=NOW).real_365d.realized_cash == 0.0


class TestHoursConfigurable:
    def test_77_plus_supported(self) -> None:
        t = build_trajectory([], available_hours_per_week=77.0, now=NOW)
        assert t.to_dict()["available_hours_per_week"] == 77.0

    def test_custom_hours_not_hardcoded(self) -> None:
        t = build_trajectory([], available_hours_per_week=20.0, now=NOW)
        assert t.to_dict()["available_hours_per_week"] == 20.0


class TestCalibration:
    def test_zero_paid_is_unknown(self) -> None:
        c = calibration_level(0)
        assert c["level"] == 0 and c["net_cash_per_hour"] is None

    def test_ladder(self) -> None:
        assert calibration_level(1)["label"] == "FIRST_REAL_DATA"
        assert calibration_level(4)["label"] == "EARLY_PATTERN"
        assert calibration_level(15)["label"] == "MEASURABLE_CHANNEL"
        assert calibration_level(40)["label"] == "RELIABLE_MODEL"
        assert calibration_level(60)["label"] == "CALIBRATED_ECONOMY"

    def test_channel_validation_terms(self) -> None:
        assert channel_validation(0) == "NO_SIGNAL"
        assert channel_validation(1) == "PROOF_OF_POSSIBILITY"
        assert channel_validation(4) == "EARLY_SIGNAL"
        assert channel_validation(15) == "REPEATABILITY_SIGNAL"
        assert channel_validation(40) == "PLANIFIABLE_CHANNEL"

    def test_scenarios_not_calibrated_without_data(self) -> None:
        out = calibrate_scenarios(measured_monthly=5000.0, samples=1)
        assert out["calibrated"] is False
        out2 = calibrate_scenarios(measured_monthly=5000.0, samples=4)
        assert out2["calibrated"] is True


class TestScenariosAndGap:
    def test_scenarios_labeled_not_forecast(self) -> None:
        s = scenarios_block()
        assert s["is_forecast"] is False and s["label"] == "PLANNING_SCENARIO"

    def test_comparison_below_on_above(self) -> None:
        assert compare_scenario_to_real(0.0, "conservative", "m1_3")["status"] == "ON_TRACK"
        assert compare_scenario_to_real(99999.0, "conservative", "m1_3")["status"] == "ABOVE"

    def test_unknown_tier_falls_back_central(self) -> None:
        assert compare_scenario_to_real(0.0, "garantizado", "m1_3")["tier"] == "central"

    def test_gap_excludes_speculative(self) -> None:
        g = gap_to_target(10000.0, realized_cash=1840.0, verifiable_pending=920.0)
        assert g["gap"] == 7240.0 and g["speculative_excluded"] is True

    def test_gap_never_negative(self) -> None:
        assert gap_to_target(100.0, realized_cash=500.0)["gap"] == 0.0

    def test_gap_math_with_77h_week(self) -> None:
        g = gap_to_target(10000.0, realized_cash=0.0, available_hours_per_week=77.0)
        assert g["required_cash_per_hour"] is not None and g["is_math"] is True


class TestChannels:
    def test_cash_only_from_paid(self) -> None:
        rows = [_row("paid", 200.0, channel="oss"), _row("expected", 9999.0, channel="oss")]
        ch = {c["channel"]: c for c in channel_economics(rows)}
        assert ch["oss"]["cash"] == 200.0 and ch["oss"]["paid"] == 1

    def test_acceptance_rate_none_without_attempts(self) -> None:
        ch = {c["channel"]: c for c in channel_economics([])}
        assert ch["ownex"]["acceptance_rate"] is None

    def test_duplicate_rate_na_honest(self) -> None:
        rows = [_row("paid", 10.0, channel="security")]
        ch = {c["channel"]: c for c in channel_economics(rows)}
        assert "duplicate_rate" not in ch["security"] or ch["security"]["duplicate_rate"] in (None, 0.0)


class TestTimezones:
    def test_naive_treated_utc(self) -> None:
        row = _row("paid", 100.0)
        row["created_at"] = row["updated_at"] = "2026-09-27T12:00:00"  # naive
        assert build_trajectory([row], now=NOW).real_365d.realized_cash == 100.0

    def test_iso_string_parsed(self) -> None:
        row = {"revenue_state": "paid", "amount": 50.0, "updated_at": (NOW - timedelta(days=1)).isoformat()}
        assert build_trajectory([row], now=NOW).real_365d.paid_outcomes == 1


class TestApi:
    def test_endpoints_200_y_3_capas(self, monkeypatch, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from api.routers.economic_trajectory import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        traj = client.get("/api/economic-trajectory/trajectory?hours_d365=10")
        assert traj.status_code == 200
        body = traj.json()
        assert {"real", "pipeline", "speculative", "scenarios", "calibration"} <= set(body)
        assert body["speculative"]["counted_as_cash"] is False

        gap = client.get("/api/economic-trajectory/gap?target_monthly=10000")
        assert gap.status_code == 200 and gap.json()["is_math"] is True

        scen = client.get("/api/economic-trajectory/scenarios")
        assert scen.status_code == 200
        assert scen.json()["scenarios"]["is_forecast"] is False

    def test_horas_negativas_rechazadas(self, monkeypatch, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
        from api.routers.economic_trajectory import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/api/economic-trajectory/trajectory?hours_d365=-1").status_code == 422
