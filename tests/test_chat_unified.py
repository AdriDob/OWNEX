"""Tests for the unified chat API (POST /api/chat).

Single entry point dispatches by persona (merlin | copilot | assistant) to
the canonical handlers. No engine logic is duplicated: the dispatcher calls
the existing routers, so these tests pin delegation + normalization with
mocked engines (no network, no API keys).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    from cores.auth.auth import create_session_token

    return {"Authorization": f"Bearer {create_session_token('test-user')}"}


class _FakeRouter:
    def __init__(self, content: str = "Do X then Y.", error: str | None = None):
        self._content = content
        self._error = error

    async def route(self, **kwargs):
        return SimpleNamespace(
            content=self._content,
            error=self._error,
            provider="fake",
            model="fake-model",
            duration_ms=1,
        )


class _FakeMerlin:
    async def process_message(self, **kwargs):
        return "Merlin says hello. No estoy seguro del resto."


class _FakeAssistant:
    def chat(self, message: str):
        return {"answer": "Assistance answer here.", "source": "test"}


class _FakeBridge:
    async def ask(self, question: str, model: str = ""):
        return {"success": True, "answer": f"asked: {question}"}


def test_chat_defaults_to_copilot_persona():
    with patch("api.routers.copilot.get_provider_router", return_value=_FakeRouter("Unified hello.")):
        r = client.post("/api/chat", json={"message": "hello"}, headers=_auth_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona"] == "copilot"
    assert body["status"] == "ok"
    assert body["response"] == "Unified hello."
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}


def test_chat_merlin_persona():
    with patch("cores.merlin.system.get_merlin_system", return_value=_FakeMerlin()):
        r = client.post(
            "/api/chat",
            json={"persona": "merlin", "message": "hello", "context": {"detail_level": "normal"}},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona"] == "merlin"
    assert body["status"] == "ok"
    assert "Merlin says hello" in body["response"]
    assert body["tool_calls"] == []
    assert any("No estoy seguro" in u for u in body["semantics"]["UNKNOWN"])


def test_chat_assistant_persona():
    with patch("api.routers.assistant.get_assistant", return_value=_FakeAssistant()):
        r = client.post(
            "/api/chat",
            json={"persona": "assistant", "message": "hello", "history": []},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona"] == "assistant"
    assert body["status"] == "ok"
    assert body["response"] == "Assistance answer here."
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}


def test_chat_unknown_persona_is_400():
    r = client.post("/api/chat", json={"persona": "jarvis", "message": "hello"}, headers=_auth_headers())
    assert r.status_code == 400
    assert "persona" in r.json()["detail"].lower()


def test_chat_empty_message_is_400():
    r = client.post("/api/chat", json={"persona": "copilot", "message": "   "}, headers=_auth_headers())
    assert r.status_code == 400


def test_chat_execute_proxies_to_copilot():
    with patch(
        "api.routers.copilot.get_opencode_bridge",
        return_value=_FakeBridge(),
    ):
        r = client.post(
            "/api/chat/execute",
            json={"action": "opencode:ask", "params": {"question": "stats?"}},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["action"] == "opencode:ask"


def test_chat_approve_issues_token():
    r = client.post("/api/chat/approve", json={"target": "repo"}, headers=_auth_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["approval_token"]


def test_chat_runs_lists_runs():
    r = client.get("/api/chat/runs", headers=_auth_headers())
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("ok", "error")


def test_legacy_persona_routes_still_mounted():
    paths = set(app.openapi()["paths"])
    assert "/api/merlin/chat" in paths
    assert "/api/copilot/chat" in paths
    assert "/api/assistant/chat" in paths
    assert "/api/chat" in paths
