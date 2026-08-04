"""Tests for the OAR (AI Runtime) API router (status / chat / route).

Chat and route endpoints depend on real providers (network), so those are
tested with a mocked, already-initialized OAR instance. Status is exercised
both uninitialized and initialized.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import router and the helper to install a pre-initialized OAR.
from api.routers import oar as oar_router_module
from api.routers.oar import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestOarApi:
    def test_status_uninitialized(self) -> None:
        with patch.object(oar_router_module, "_oar", None):
            response = client.get("/oar/status")
            assert response.status_code == 200
            assert response.json()["initialized"] is False

    def test_status_initialized(self) -> None:
        fake = MagicMock()
        fake._initialized = True
        fake.status.return_value = {
            "initialized": True,
            "providers": ["ollama"],
            "health": {},
            "costs": {},
            "cache": {},
            "learning": {},
        }
        with patch.object(oar_router_module, "_oar", fake):
            with patch.object(oar_router_module, "_initialized", True):
                response = client.get("/oar/status")
                assert response.status_code == 200
                assert response.json()["initialized"] is True

    def test_doctor_unavailable_before_init(self) -> None:
        # Without a provider-backed OAR this should surface a clean 503,
        # not an unhandled crash. Mock initialize to fail.
        fake = MagicMock()
        fake.initialize = AsyncMock(side_effect=RuntimeError("no providers"))
        with patch.object(oar_router_module, "_oar", fake):
            with patch.object(oar_router_module, "_initialized", False):
                response = client.get("/oar/doctor")
                assert response.status_code == 503
                assert "initialization failed" in response.json()["detail"].lower()

    def test_route_returns_decision(self) -> None:
        decision = MagicMock()
        decision.provider_id = "ollama"
        decision.model_id = "qwen3-coder:8b"
        decision.confidence = 0.9
        decision.estimated_cost_usd = 0.0
        decision.estimated_latency_ms = 120
        decision.reasoning = "scored"
        decision.fallback_chain = ["opencode"]
        decision.capabilities_met = {"chat", "code"}
        decision.capabilities_missing = set()
        decision.privacy_ok = True

        fake_oar = MagicMock()
        fake_oar.initialize = AsyncMock()
        fake_oar._router = MagicMock()
        fake_oar._router.route = AsyncMock(return_value=decision)

        with patch.object(oar_router_module, "_oar", fake_oar):
            with patch.object(oar_router_module, "_initialized", False):
                response = client.post("/oar/route", json={"prompt": "h", "task_type": "code"})
                assert response.status_code == 200
                body = response.json()
                assert body["provider_id"] == "ollama"
                assert body["model_id"] == "qwen3-coder:8b"
                assert body["privacy_ok"] is True

    def test_chat_returns_content(self) -> None:
        import json

        from cores.ai.runtime.interfaces import AIResponse, TaskType

        resp = AIResponse(
            content="hello",
            provider_id="ollama",
            model_id="qwen3",
            task_type=TaskType.CHAT,
            metadata={"routing_decision": {"provider": "ollama", "model": "qwen3"}},
        )
        fake_oar = MagicMock()
        fake_oar.initialize = AsyncMock()
        fake_oar.chat = AsyncMock(return_value=resp)

        with patch.object(oar_router_module, "_oar", fake_oar):
            with patch.object(oar_router_module, "_initialized", False):
                response = client.post("/oar/chat", json={"prompt": "hi", "task_type": "chat"})
                assert response.status_code == 200
                body = response.json()
                assert body["content"] == "hello"
                assert body["provider_id"] == "ollama"
                assert json.dumps(body["routing_decision"])  # serializable

    def test_chat_error_surfaces_502(self) -> None:
        fake_oar = MagicMock()
        fake_oar.initialize = AsyncMock()
        fake_oar.chat = AsyncMock(side_effect=RuntimeError("all providers failed"))
        with patch.object(oar_router_module, "_oar", fake_oar):
            with patch.object(oar_router_module, "_initialized", False):
                response = client.post("/oar/chat", json={"prompt": "hi"})
                assert response.status_code == 502

    def test_invalid_task_type_422(self) -> None:
        fake_oar = MagicMock()
        fake_oar.initialize = AsyncMock()
        with patch.object(oar_router_module, "_oar", fake_oar):
            with patch.object(oar_router_module, "_initialized", False):
                response = client.post("/oar/route", json={"prompt": "h", "task_type": "bogus"})
                assert response.status_code == 422
