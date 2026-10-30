"""Tests for free-chat semantic labeling (P3/P5).

The canonical free-chat path (POST /copilot/chat) must label model output
as INFERENCE (never FACT) and always carry the standing UNKNOWN. Additive
`semantics` key; existing contract keys untouched.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from cores.copilot.semantics import label_free_text

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


def test_label_free_text_marks_model_output_as_inference():
    resp = label_free_text("Do X then Y. It will work.")
    d = resp.to_dict()
    assert d["FACT"] == []
    assert len(d["INFERENCE"]) == 2
    assert any("Unverified model output" in u for u in d["UNKNOWN"])


def test_label_free_text_extracts_uncertainty_markers():
    resp = label_free_text("I don't know the payout date. Submit the report today.")
    d = resp.to_dict()
    assert any("don't know" in u for u in d["UNKNOWN"])
    assert any("Submit the report today" in i for i in d["INFERENCE"])


def test_label_free_text_spanish_markers():
    resp = label_free_text("No estoy seguro del scope. Revisá el programa.")
    d = resp.to_dict()
    assert any("No estoy seguro" in u for u in d["UNKNOWN"])


def test_label_free_text_empty_is_honest():
    d = label_free_text("").to_dict()
    assert d["FACT"] == [] and d["INFERENCE"] == []
    assert len(d["UNKNOWN"]) == 1  # standing unknown only


def test_copilot_chat_includes_semantics():
    with patch("api.routers.copilot.get_provider_router", return_value=_FakeRouter("Do X then Y.")):
        r = client.post(
            "/api/copilot/chat",
            json={"message": "hello", "history": [], "task_type": "chat"},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["response"] == "Do X then Y."
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}
    assert body["semantics"]["FACT"] == []
    assert len(body["semantics"]["INFERENCE"]) == 1


def test_copilot_chat_error_path_unaffected():
    with patch(
        "api.routers.copilot.get_provider_router",
        return_value=_FakeRouter("", error="boom"),
    ):
        r = client.post(
            "/api/copilot/chat",
            json={"message": "hello", "history": [], "task_type": "chat"},
            headers=_auth_headers(),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert "semantics" in body


class _FakeMerlin:
    async def process_message(self, **kwargs):
        return "Merlin says hello. No estoy seguro del resto."


class _FakeAssistant:
    def chat(self, message: str):
        return {"answer": "Assistance answer here.", "source": "test", "suggestions": []}


class _FakeOrionAgent:
    async def chat(self, message: str, history=None):
        return {"response": "Orion says hi.", "engine": "test"}


def test_merlin_chat_includes_semantics():
    with patch("cores.merlin.system.get_merlin_system", return_value=_FakeMerlin()):
        r = client.post(
            "/api/merlin/chat",
            json={"message": "hello"},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}
    assert any("No estoy seguro" in u for u in body["semantics"]["UNKNOWN"])


def test_assistant_chat_includes_semantics():
    with patch("api.routers.assistant.get_assistant", return_value=_FakeAssistant()):
        r = client.post(
            "/api/assistant/chat",
            json={"message": "hello", "history": [], "task_type": "chat"},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"] == "Assistance answer here."
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}


def test_orion_chat_includes_semantics():
    with patch("cores.ai.orion_agent.OrionAgent", return_value=_FakeOrionAgent()):
        r = client.post(
            "/api/assistant/orion-chat",
            json={"message": "hello", "history": []},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "test"
    assert set(body["semantics"]) == {"FACT", "INFERENCE", "RECOMMENDATION", "UNKNOWN"}


class _CapturingRouter(_FakeRouter):
    def __init__(self, content: str = "Do X then Y."):
        super().__init__(content)
        self.received_messages: list[dict[str, str]] | None = None

    async def route(self, **kwargs):
        self.received_messages = kwargs.get("messages")
        return await super().route(**kwargs)


def test_copilot_chat_roundtrip_like_frontend():
    """The frontend path (ownexAi -> sendChatMessage) must round-trip the
    grounded prompt with a real history and receive authoritative semantics:
    model output is INFERENCE, never FACT. Regression: the UI used to relabel
    locally with a FACT-default heuristic."""
    router = _CapturingRouter("[OWNEX canonical state] Submit the report today.")
    with patch("api.routers.copilot.get_provider_router", return_value=router):
        r = client.post(
            "/api/copilot/chat",
            json={
                "message": "[OWNEX canonical state — ground every claim]\n\nUSER QUESTION: what now?",
                "history": [
                    {"role": "user", "content": "primer pregunta"},
                    {"role": "assistant", "content": "Primera respuesta del modelo."},
                ],
                "task_type": "chat",
            },
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    # provider received history first, then the user message
    assert router.received_messages is not None
    assert router.received_messages[:2] == [
        {"role": "user", "content": "primer pregunta"},
        {"role": "assistant", "content": "Primera respuesta del modelo."},
    ]
    assert router.received_messages[-1]["role"] == "user"
    # authoritative semantics: FACT empty by contract, model output labeled INFERENCE
    assert body["semantics"]["FACT"] == []
    assert len(body["semantics"]["INFERENCE"]) >= 1


def test_copilot_chat_contract_drift_handled_by_frontend_fallback():
    """If a future backend omits semantics, the FE fallback must not label
    model output as FACT (tagFor defaults to INFERENCE)."""
    router = _FakeRouter("Estimación: probably $500. Submit today.")
    with patch("api.routers.copilot.get_provider_router", return_value=router):
        r = client.post(
            "/api/copilot/chat",
            json={"message": "hello", "history": [], "task_type": "chat"},
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    assert r.json()["semantics"]["FACT"] == []


def test_copilot_chat_empty_message_returns_400():
    """Frontend pre-trims input; backend stays fail-closed."""
    r = client.post(
        "/api/copilot/chat",
        json={"message": "", "history": [], "task_type": "chat"},
        headers=_auth_headers(),
    )
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()
    r2 = client.post(
        "/api/copilot/chat",
        json={"message": "   ", "history": [], "task_type": "chat"},
        headers=_auth_headers(),
    )
    assert r2.status_code == 400
