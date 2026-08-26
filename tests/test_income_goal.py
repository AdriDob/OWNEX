"""Tests for income goal parsing and /api/copilot/income-goal endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cores.direct_work_engine.income_target import parse_income_goal


class TestParseIncomeGoal:
    def test_spanish_10k_monthly(self) -> None:
        assert parse_income_goal("quiero ganar 10k este mes") == (10000.0, "monthly")

    def test_dollar_sign_weekly(self) -> None:
        assert parse_income_goal("ganar $500 por semana") == (500.0, "weekly")

    def test_english_comma_thousands(self) -> None:
        assert parse_income_goal("income of 2,500/month") == (2500.0, "monthly")

    def test_spanish_dot_thousands(self) -> None:
        assert parse_income_goal("10.000 al mes") == (10000.0, "monthly")

    def test_decimal_k_suffix(self) -> None:
        assert parse_income_goal("quiero generar 1.5k mensual") == (1500.0, "monthly")

    def test_mil_keyword_thousands(self) -> None:
        assert parse_income_goal("objetivo de 5 mil pesos... quiero llegar a 5 mil dólares al mes") == (
            5000.0,
            "monthly",
        )

    def test_plain_number_defaults_monthly(self) -> None:
        assert parse_income_goal("quiero ingresos de 3000") == (3000.0, "monthly")

    def test_no_income_keyword_returns_none(self) -> None:
        assert parse_income_goal("hoy es lunes y hay 10 tareas") is None

    def test_no_amount_returns_none(self) -> None:
        assert parse_income_goal("quiero ganar mucho dinero") is None

    def test_empty_returns_none(self) -> None:
        assert parse_income_goal("") is None
        assert parse_income_goal("   ") is None

    def test_zero_rejected(self) -> None:
        assert parse_income_goal("ganar 0 dolares al mes") is None


class TestIncomeGoalEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        from fastapi import FastAPI

        from api.routers.copilot import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_natural_language_plan(self, client: TestClient) -> None:
        resp = client.post("/api/copilot/income-goal", json={"message": "quiero ganar 10k este mes"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["target"] == {"amount_usd": 10000.0, "period": "monthly"}
        for key in (
            "required_opportunities",
            "required_hours_per_week",
            "recommended_sources",
            "probability_of_success",
            "risk_factors",
            "weekly_plan",
            "progress",
        ):
            assert key in data

    def test_explicit_values(self, client: TestClient) -> None:
        resp = client.post("/api/copilot/income-goal", json={"target_usd": 2500, "period": "weekly"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["target"] == {"amount_usd": 2500.0, "period": "weekly"}

    def test_invalid_period_falls_back_to_monthly(self, client: TestClient) -> None:
        resp = client.post("/api/copilot/income-goal", json={"target_usd": 1000, "period": "daily"})
        assert resp.status_code == 200
        assert resp.json()["target"]["period"] == "monthly"

    def test_unparseable_message_400(self, client: TestClient) -> None:
        resp = client.post("/api/copilot/income-goal", json={"message": "hola que tal"})
        assert resp.status_code == 400
        assert "monto" in resp.json()["detail"]

    def test_progress_shape(self, client: TestClient) -> None:
        resp = client.post("/api/copilot/income-goal", json={"target_usd": 5000})
        progress = resp.json()["progress"]
        for key in (
            "earned_this_period",
            "pending_amount",
            "progress_pct",
            "days_remaining",
            "on_track",
            "required_daily_rate",
        ):
            assert key in progress
