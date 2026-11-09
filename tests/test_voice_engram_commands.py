"""Tests for voice commands bound to the Engram memory system."""

from __future__ import annotations

import asyncio
from pathlib import Path

from cores.cycles.knowledge_capture import KnowledgeEntry, LearningType
from cores.voice.command_executor import (
    VULN_VOCABULARY,
    VoiceCommandExecutor,
    VoiceCommandType,
    detect_platform,
    detect_vuln_type,
)
from cores.voice.voice_engine import resolve_piper_voice


def _executor() -> VoiceCommandExecutor:
    """Executor with parsing state only (no executors / feedback loop needed)."""
    executor = VoiceCommandExecutor.__new__(VoiceCommandExecutor)
    executor._command_history = []
    executor._max_history = 100
    return executor


def _run(item):
    return asyncio.run(item)


class FakeCapture:
    """Minimal KnowledgeCapture stand-in for handler tests."""

    def __init__(self, entries: list[KnowledgeEntry] | None = None) -> None:
        self.entries = entries or []
        self.tag_calls: list[tuple[str, str]] = []

    def recall_engrams(self, platform=None, vuln_type=None, limit=20):
        selected = [e for e in self.entries if (platform is None or e.platform == platform) and (vuln_type is None or e.vuln_type == vuln_type)]
        return selected[:limit]

    def get_entries_by_vuln_type(self, vuln_type):
        return [e for e in self.entries if e.vuln_type == vuln_type]

    def get_entries_by_platform(self, platform):
        return [e for e in self.entries if e.platform == platform]

    def get_recent(self, limit=20):
        return self.entries[:limit]

    def tag_engram(self, engram_id, tag):
        self.tag_calls.append((engram_id, tag))
        return any(e.engram_id == engram_id for e in self.entries)


def _entry(engram_id="eng_1", vuln_type="xss", platform="hackerone") -> KnowledgeEntry:
    return KnowledgeEntry(
        id=engram_id,
        type=LearningType.ENGRAM,
        source_finding_id=None,
        source_target_id=None,
        platform=platform,
        vuln_type=vuln_type,
        lesson="Reflected XSS via unencoded search parameter on staging host.",
        confidence=0.8,
        engram_id=engram_id,
        tags=["critical"],
    )


class TestVulnVocabulary:
    def test_aliases_map_to_canonical_types(self) -> None:
        assert detect_vuln_type("I found sqli there") == "sql_injection"
        assert detect_vuln_type("stored cross site scripting") == "xss"
        assert detect_vuln_type("remote code execution") == "rce"
        assert detect_vuln_type("path traversal") == "lfi"
        assert detect_vuln_type("server side request forgery") == "ssrf"
        assert detect_vuln_type("insecure direct object reference") == "idor"
        assert detect_vuln_type("account takeover") == "account_takeover"

    def test_unknown_text_returns_none(self) -> None:
        assert detect_vuln_type("check my email") is None

    def test_every_canonical_key_is_reachable(self) -> None:
        for canonical, aliases in VULN_VOCABULARY.items():
            assert detect_vuln_type(aliases[0]) == canonical

    def test_platform_aliases(self) -> None:
        assert detect_platform("search hacker one reports") == "hackerone"
        assert detect_platform("bug crowd scope") == "bugcrowd"
        assert detect_platform("nothing here") is None


class TestEngramParsing:
    def test_recall_memory(self) -> None:
        parsed = _executor().parse_command("recall my memory")
        assert parsed.command_type == VoiceCommandType.ENGRAM_RECALL

    def test_recall_about_topic_enriches_vuln(self) -> None:
        parsed = _executor().parse_command("what do I know about sql injection")
        assert parsed.command_type == VoiceCommandType.ENGRAM_RECALL
        assert parsed.entities["topic"] == "sql"
        assert parsed.entities["vuln_type"] == "sql_injection"

    def test_vuln_lookup(self) -> None:
        parsed = _executor().parse_command("show me xss")
        assert parsed.command_type == VoiceCommandType.ENGRAM_LOOKUP
        assert parsed.entities["vuln_type"] == "xss"

    def test_platform_lookup(self) -> None:
        parsed = _executor().parse_command("hackerone entries")
        assert parsed.command_type == VoiceCommandType.ENGRAM_LOOKUP
        assert parsed.entities["platform"] == "hackerone"

    def test_capture_finding_with_id(self) -> None:
        parsed = _executor().parse_command("capture finding #42")
        assert parsed.command_type == VoiceCommandType.ENGRAM_CAPTURE
        assert parsed.entities["finding_id"] == "42"

    def test_tag_engram(self) -> None:
        parsed = _executor().parse_command("tag eng_1 as critical")
        assert parsed.command_type == VoiceCommandType.ENGRAM_TAG
        assert parsed.entities == {"engram_id": "eng_1", "tag": "critical"}

    def test_list_recent(self) -> None:
        assert _executor().parse_command("list recent engrams").command_type == VoiceCommandType.ENGRAM_LIST
        assert _executor().parse_command("últimos hallazgos").command_type == VoiceCommandType.ENGRAM_LIST

    def test_list_survives_whisper_phonetics(self) -> None:
        # Real transcripts land as "in grams" / "recenting grams" (see round-trip run).
        assert _executor().parse_command("List recent in grams.").command_type == VoiceCommandType.ENGRAM_LIST
        assert _executor().parse_command("List recenting grams.").command_type == VoiceCommandType.ENGRAM_LIST
        assert _executor().parse_command("show me my engrams").command_type == VoiceCommandType.ENGRAM_LIST

    def test_existing_commands_still_parse(self) -> None:
        executor = _executor()
        assert executor.parse_command("claim bounty abc").command_type == VoiceCommandType.CLAIM_BOUNTY
        assert executor.parse_command("submit pr for abc").command_type == VoiceCommandType.SUBMIT_PR
        assert executor.parse_command("status of abc").command_type == VoiceCommandType.GET_BOUNTY
        assert executor.parse_command("start bounty pipeline for abc").command_type == VoiceCommandType.START_PIPELINE
        assert executor.parse_command("hola que tal").command_type == VoiceCommandType.UNKNOWN

    def test_bounty_entities_unchanged(self) -> None:
        parsed = _executor().parse_command("claim bounty abc")
        assert parsed.entities["bounty_id"] == "abc"
        assert parsed.requires_confirmation is True

    def test_available_commands_include_engram(self) -> None:
        types = {c["command_type"] for c in _executor().get_available_commands()}
        assert "engram_recall" in types
        assert "engram_capture" in types


class TestEngramHandlers:
    def test_recall_returns_entries(self, monkeypatch) -> None:
        fake = FakeCapture([_entry()])
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: fake)
        executor = _executor()
        parsed = executor.parse_command("recall memory")
        result = _run(executor.execute_command(parsed, confirmed=True))
        assert result.success is True
        assert result.data["entries"][0]["engram_id"] == "eng_1"
        assert "memorias" in result.voice_feedback

    def test_recall_without_matches_reports_empty(self, monkeypatch) -> None:
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: FakeCapture([]))
        executor = _executor()
        parsed = executor.parse_command("recall memory")
        result = _run(executor.execute_command(parsed, confirmed=True))
        assert result.success is False
        assert result.error == "no matching engrams"

    def test_lookup_by_vuln_type(self, monkeypatch) -> None:
        fake = FakeCapture([_entry(), _entry(engram_id="eng_2", vuln_type="ssrf")])
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: fake)
        executor = _executor()
        parsed = executor.parse_command("show me ssrf")
        result = _run(executor.execute_command(parsed, confirmed=True))
        assert result.success is True
        assert result.data["label"] == "ssrf"
        assert len(result.data["entries"]) == 1

    def test_tag_handler_calls_store(self, monkeypatch) -> None:
        fake = FakeCapture([_entry()])
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: fake)
        executor = _executor()
        parsed = executor.parse_command("tag eng_1 as urgent")
        result = _run(executor.execute_command(parsed, confirmed=True))
        assert result.success is True
        assert fake.tag_calls == [("eng_1", "urgent")]

    def test_capture_without_id_asks_for_one(self, monkeypatch) -> None:
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: FakeCapture([]))
        executor = _executor()
        parsed = executor.parse_command("capture this finding")
        result = _run(executor.execute_command(parsed, confirmed=True))
        assert result.success is False
        assert "número del hallazgo" in result.voice_feedback

    def test_history_serialisation(self, monkeypatch) -> None:
        monkeypatch.setattr("cores.voice.command_executor._knowledge_capture", lambda: FakeCapture([_entry()]))
        executor = _executor()
        parsed = executor.parse_command("list recent engrams")
        _run(executor.execute_command(parsed, confirmed=True))
        history = executor.get_command_history()
        assert history[0]["command_type"] == VoiceCommandType.ENGRAM_LIST
        assert "voice_feedback" in history[0]


class TestPiperVoiceResolution:
    """piper >= 1.8 needs an .onnx path or a --data_dir, never a bare name."""

    def test_model_path_override_wins(self, tmp_path: Path, monkeypatch) -> None:
        model = tmp_path / "voice.onnx"
        model.write_bytes(b"")
        monkeypatch.setenv("OWNEX_PIPER_MODEL", str(model))
        path, dirs = resolve_piper_voice("es_MX-ald-medium")
        assert path.resolve() == model.resolve()
        assert dirs == [tmp_path]

    def test_data_dir_env_resolves_voice_name(self, tmp_path: Path, monkeypatch) -> None:
        model = tmp_path / "es_MX-ald-medium.onnx"
        model.write_bytes(b"")
        monkeypatch.delenv("OWNEX_PIPER_MODEL", raising=False)
        monkeypatch.setenv("OWNEX_PIPER_DATA_DIR", str(tmp_path))
        path, dirs = resolve_piper_voice("es_MX-ald-medium")
        assert path.resolve() == model.resolve()
        assert tmp_path in dirs

    def test_project_voices_dir_is_searched_by_default(self, tmp_path: Path, monkeypatch) -> None:
        # data/piper_voices is the persistent, gitignored home for piper models.
        voices = tmp_path / "data" / "piper_voices"
        voices.mkdir(parents=True)
        model = voices / "es_MX-ald-medium.onnx"
        model.write_bytes(b"")
        monkeypatch.delenv("OWNEX_PIPER_MODEL", raising=False)
        monkeypatch.delenv("OWNEX_PIPER_DATA_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        path, _dirs = resolve_piper_voice("es_MX-ald-medium")
        assert path.resolve() == model.resolve()

    def test_unresolved_voice_falls_back_to_name(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.delenv("OWNEX_PIPER_MODEL", raising=False)
        monkeypatch.delenv("OWNEX_PIPER_DATA_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        path, dirs = resolve_piper_voice("missing-voice")
        assert path == Path("missing-voice")
        assert Path.cwd() in dirs
