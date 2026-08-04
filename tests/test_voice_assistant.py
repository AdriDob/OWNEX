"""Tests for the intelligent voice assistant (opportunity evaluator + real-time bridge)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.voice import router
from cores.voice.opportunity_evaluator import OpportunityEvaluator

app = FastAPI()
app.include_router(router)
client = TestClient(app)

evaluator = OpportunityEvaluator()


class TestOpportunityEvaluator:
    def test_opportunity_request_is_worth_it(self) -> None:
        result = evaluator.evaluate("Buscá oportunidades de trabajo remoto para ganar dinero")
        assert result.domain == "opportunity"
        assert result.worth_it is True
        assert result.worth_score >= 0.5
        assert result.suggested_action

    def test_investment_request_is_worth_it(self) -> None:
        result = evaluator.evaluate("Quiero invertir en cripto para multiplicar mi capital")
        assert result.domain == "investment"
        assert result.worth_it is True

    def test_learning_request_is_worth_it(self) -> None:
        result = evaluator.evaluate("Quiero aprender React para conseguir trabajo")
        assert result.domain in ("learning", "opportunity")
        assert result.worth_it is True

    def test_entertainment_is_low_value(self) -> None:
        result = evaluator.evaluate("Mostrame un video divertido")
        assert result.worth_it is False
        assert any("entretenimiento" in r or "generación de valor" in r for r in result.reasoning)

    def test_empty_request_not_worth_it(self) -> None:
        result = evaluator.evaluate("   ")
        assert result.worth_it is False
        assert result.worth_score == 0.0

    def test_productivity_request_scores_neutral(self) -> None:
        result = evaluator.evaluate("Organizá mi agenda de la semana")
        assert result.domain == "productivity"
        assert result.worth_it is True


class TestVoiceAssistantApi:
    def test_assistant_returns_reply(self) -> None:
        response = client.post(
            "/voice/assistant", json={"text": "Buscá bounties de desarrollo para cobrar esta semana"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] > 0
        assert body["domain"] == "opportunity"
        assert body["worth_it"] is True
        assert body["response"]
        assert body["suggested_action"]

    def test_replies_are_pollable(self) -> None:
        first = client.post("/voice/assistant", json={"text": "Buscá oportunidades"}).json()
        latest = client.get("/voice/assistant/replies", params={"since": first["id"]}).json()
        assert latest["replies"] == []
        older = client.get("/voice/assistant/replies", params={"since": 0}).json()
        assert any(r["id"] == first["id"] for r in older["replies"])

    def test_status_reports_open_source_providers(self) -> None:
        body = client.get("/voice/status").json()
        assert body["stt_provider"] == "browser_webspeech"
        assert body["tts_provider"] == "browser_webspeech"
