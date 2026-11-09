"""API tests for the audio-in voice command endpoint (dashboard round-trip)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import voice_commands
from cores.voice.command_executor import (
    CommandExecutionResult,
    ParsedCommand,
    VoiceCommandType,
)


class _StubExecutor:
    """Executor stub: parses/executes without wiring the real executor graph."""

    def __init__(self) -> None:
        self.seen: list[str] = []
        self.executors: dict[str, object] = {}
        self.bounty_pipeline = None
        self._command_history: list[object] = []

    def get_command_history(self, limit: int = 50) -> list[dict]:
        return []

    def parse_command(self, text: str) -> ParsedCommand:
        self.seen.append(text)
        return ParsedCommand(
            command_type=VoiceCommandType.ENGRAM_LIST,
            raw_text=text,
            entities={},
            confidence=0.95,
            requires_confirmation=False,
        )

    async def execute_command(self, parsed: ParsedCommand, confirmed: bool = False) -> CommandExecutionResult:
        return CommandExecutionResult(
            success=True,
            command_type=parsed.command_type,
            raw_text=parsed.raw_text,
            message="2 memorias recientes",
            voice_feedback="Tengo dos memorias.",
            data={"entries": []},
        )


@pytest.fixture()
def api(monkeypatch) -> tuple[TestClient, _StubExecutor, list[dict]]:
    """App with only the voice-commands router plus a stubbed STT/executor."""
    calls: list[dict] = []
    executor = _StubExecutor()

    def fake_transcribe(path, model_size="base", language=None):
        # The uploaded bytes must be on disk while STT runs.
        assert Path(path).exists(), "audio file must exist during transcription"
        calls.append({"path": Path(path), "model_size": model_size, "language": language})
        return "List recent in grams."

    monkeypatch.setattr("cores.cycles.voice_commands.transcribe_audio", fake_transcribe)
    monkeypatch.setattr(voice_commands, "_get_executor", lambda: executor)

    app = FastAPI()
    app.include_router(voice_commands.router)
    return TestClient(app), executor, calls


def test_audio_round_trip_executes_transcribed_command(api) -> None:
    client, executor, calls = api
    payload = b"RIFF....fake-audio-bytes"

    response = client.post(
        "/api/voice/commands/audio",
        files={"audio": ("command.wav", payload, "audio/wav")},
        data={"language": "es"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "List recent in grams."
    assert body["command_type"] == VoiceCommandType.ENGRAM_LIST.value
    assert body["message"] == "2 memorias recientes"
    assert body["audio_bytes"] == len(payload)
    assert body["language"] == "es"
    assert body["success"] is True
    # The transcript is what actually drove the command.
    assert executor.seen == ["List recent in grams."]
    assert calls[0]["language"] == "es"


def test_audio_uses_stt_defaults_when_not_given(api) -> None:
    client, _executor, calls = api

    response = client.post(
        "/api/voice/commands/audio",
        files={"audio": ("command.webm", b"webm-bytes", "audio/webm")},
    )

    assert response.status_code == 200, response.text
    assert calls[0]["language"] is None
    # Model size is resolved from the STT layer, never duplicated here.
    assert calls[0]["model_size"]
    assert response.json()["model_size"] == calls[0]["model_size"]


def test_audio_rejects_empty_body(api) -> None:
    client, executor, _calls = api

    response = client.post(
        "/api/voice/commands/audio",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 422
    assert "empty audio" in response.json()["detail"]
    assert executor.seen == []


def test_audio_without_transcript_fails_honestly(api, monkeypatch) -> None:
    client, executor, _calls = api
    monkeypatch.setattr("cores.cycles.voice_commands.transcribe_audio", lambda *a, **k: None)

    response = client.post(
        "/api/voice/commands/audio",
        files={"audio": ("x.wav", b"some-bytes", "audio/wav")},
    )

    assert response.status_code == 422
    assert "transcribe" in response.json()["detail"]
    assert executor.seen == []


def test_audio_temp_file_is_removed(api) -> None:
    client, _executor, calls = api

    client.post(
        "/api/voice/commands/audio",
        files={"audio": ("cmd.wav", b"some-bytes", "audio/wav")},
    )

    assert calls, "transcription should have been attempted"
    assert not calls[0]["path"].exists()


def test_text_command_contract_unchanged(api) -> None:
    client, executor, _calls = api

    response = client.post("/api/voice/commands/command", json={"text": "list recent engrams"})

    assert response.status_code == 200, response.text
    assert response.json()["command_type"] == VoiceCommandType.ENGRAM_LIST.value
    assert executor.seen == ["list recent engrams"]


def _health_client() -> TestClient:
    app = FastAPI()
    app.include_router(voice_commands.router)
    return TestClient(app)


def test_health_reports_stt_tts_and_player() -> None:
    response = _health_client().get("/api/voice/commands/health")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] in {"ok", "degraded", "unavailable"}
    assert body["checked_at"]
    for component in ("stt", "tts", "audio_player"):
        section = body["components"][component]
        assert isinstance(section["available"], bool)
        assert section["fallback"]
        assert section["fallback_detail"]
    assert isinstance(body["fallbacks"], list)


def test_health_marks_missing_player_with_browser_fallback(monkeypatch) -> None:
    from cores.cycles import voice_commands as stt_layer

    monkeypatch.setattr(stt_layer, "_find_player", lambda: None)
    health = stt_layer.voice_stack_health()

    player = health["components"]["audio_player"]
    assert player["available"] is False
    assert player["fallback"] == "browser_audio_element"
    assert health["status"] != "ok"


def test_health_marks_missing_stt_as_unavailable(monkeypatch) -> None:
    from cores.cycles import voice_commands as stt_layer

    monkeypatch.setattr(stt_layer, "_has_module", lambda name: False)
    health = stt_layer.voice_stack_health()

    stt = health["components"]["stt"]
    assert stt["available"] is False
    assert stt["fallback"] == "browser_speech_recognition"
    assert health["status"] == "unavailable"


def test_health_marks_missing_tts_voice_as_degraded(monkeypatch, tmp_path) -> None:
    from cores.cycles import voice_commands as stt_layer
    from cores.voice import voice_engine

    # STT available, player available: only TTS is broken → degraded, not unavailable.
    monkeypatch.setattr(stt_layer, "_has_module", lambda name: True)
    monkeypatch.setattr(stt_layer, "_find_player", lambda: "/usr/bin/aplay")
    monkeypatch.setattr(voice_engine, "PIPER_BIN", None)
    monkeypatch.setattr(
        voice_engine,
        "resolve_piper_voice",
        lambda model=None: (tmp_path / "missing.onnx", []),
    )
    health = stt_layer.voice_stack_health()

    tts = health["components"]["tts"]
    assert tts["available"] is False
    assert tts["fallback"] == "system_tts"
    assert health["status"] == "degraded"


def test_health_is_registered_on_the_real_router() -> None:
    paths = {getattr(route, "path", "") for route in voice_commands.router.routes}
    assert "/api/voice/commands/health" in paths


def test_status_includes_voice_stack_components(monkeypatch) -> None:
    executor = _StubExecutor()
    monkeypatch.setattr(voice_commands, "_get_executor", lambda: executor)

    response = _health_client().get("/api/voice/commands/status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["initialized"] is True
    stack = body["voice_stack"]
    assert stack["status"] in {"ok", "degraded", "unavailable"}
    for component in ("stt", "tts", "audio_player"):
        assert "available" in stack["components"][component]
        assert stack["components"][component]["fallback"]
