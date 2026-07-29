"""Tests for AI Bounty Auto-Hunter module."""

from __future__ import annotations

from core.ai_bounty.engine import AIBountyEngine
from core.ai_bounty.monitor import AIBountyChallenge, AIBountyMonitor
from core.ai_bounty.publisher import AIBountyEventPublisher
from cores.events.types import Events
from cores.platforms.ai_bounty import (
    AI_BOUNTY_REGISTRY,
    AnthropicBounty,
    GoogleAIBounty,
    ImbueBounty,
    OpenAIBounty,
)

# ── Monitor tests ────────────────────────────────────────────────


def test_monitor_init():
    monitor = AIBountyMonitor()
    stats = monitor.get_stats()
    assert stats["total_challenges"] == 0
    assert stats["programs_tracked"] == 4


def test_monitor_get_programs():
    monitor = AIBountyMonitor()
    programs = monitor.get_programs()
    assert len(programs) == 4
    pids = [p["platform_id"] for p in programs]
    assert "imbue" in pids
    assert "anthropic" in pids
    assert "openai" in pids
    assert "google_ai" in pids


def test_monitor_register_challenge():
    monitor = AIBountyMonitor()
    c = monitor.register_challenge(
        platform="openai",
        challenge_id="gpt5_audit",
        title="GPT-5 Security Audit",
        url="https://openai.com/bounty/gpt5",
        description="Test GPT-5 for vulnerabilities",
        targets=["api.openai.com"],
        severity="high",
    )
    assert c.platform == "openai"
    assert c.challenge_id == "gpt5_audit"
    assert c.status == "new"
    assert len(c.focus_areas) > 0
    assert c.targets == ["api.openai.com"]


def test_monitor_register_duplicate():
    monitor = AIBountyMonitor()
    c1 = monitor.register_challenge(platform="anthropic", challenge_id="claude_audit", title="Test")
    c2 = monitor.register_challenge(platform="anthropic", challenge_id="claude_audit", title="Test")
    assert c1 is c2
    assert c2.status == "new"


def test_monitor_get_challenges():
    monitor = AIBountyMonitor()
    monitor.register_challenge(platform="imbue", challenge_id="c1", title="Challenge 1")
    monitor.register_challenge(platform="openai", challenge_id="c2", title="Challenge 2")
    all_c = monitor.get_challenges()
    assert len(all_c) == 2
    openai_c = monitor.get_challenges(platform="openai")
    assert len(openai_c) == 1
    assert openai_c[0].challenge_id == "c2"


def test_monitor_status_lifecycle():
    monitor = AIBountyMonitor()
    c = monitor.register_challenge(platform="imbue", challenge_id="lifecycle", title="Lifecycle Test")
    assert c.status == "new"
    monitor.mark_scanned("imbue", "lifecycle")
    assert c.status == "scanned"
    got = monitor.get_challenge("imbue", "lifecycle")
    assert got is not None
    assert got.status == "scanned"


def test_engine_discover_all():
    engine = AIBountyEngine()
    challenges = engine.discover_all()
    assert len(challenges) == 4
    stats = engine.get_stats()
    assert stats["total_scans"] == 0


def test_engine_assess_opportunity():
    engine = AIBountyEngine()
    engine.discover_all()
    result = engine.assess_opportunity("openai", "openai_program")
    assert "error" not in result
    assert result["platform"] == "openai"
    assert result["expected_value_per_hour"] > 0
    assert result["recommended_action"] in ("high_priority", "worth_pursuing", "low_priority", "skip")


def test_engine_assess_unknown():
    engine = AIBountyEngine()
    result = engine.assess_opportunity("unknown", "nonexistent")
    assert "error" in result


def test_engine_discover_sets_default_targets():
    engine = AIBountyEngine()
    engine.discover_all()
    c = engine._monitor.get_challenge("openai", "openai_program")
    assert c is not None
    assert len(c.targets) > 0
    assert "https://openai.com" in c.targets


def test_engine_scan_with_explicit_empty_targets():
    engine = AIBountyEngine()
    engine._monitor.register_challenge(
        platform="imbue",
        challenge_id="empty_test",
        title="No targets",
        targets=[],
    )
    result = engine.scan_challenge("imbue", "empty_test")
    assert "No targets to scan" in result.get("error", "")


def test_engine_scan_unknown():
    engine = AIBountyEngine()
    result = engine.scan_challenge("imbue", "no_such_challenge")
    assert "error" in result


def test_engine_pending_reports():
    engine = AIBountyEngine()
    assert engine.get_pending_reports() == []


def test_engine_scan_history():
    engine = AIBountyEngine()
    assert engine.get_scan_history() == []
    assert engine.get_scan_history(platform="openai") == []


def test_engine_estimate_payout():
    engine = AIBountyEngine()
    findings = [
        {"severity": "critical", "name": "RCE"},
        {"severity": "high", "name": "IDOR"},
        {"severity": "medium", "name": "XSS"},
        {"severity": "low", "name": "Info"},
    ]
    total = engine._estimate_payout(findings)
    assert total == 5000 + 1500 + 500 + 100


def test_engine_get_stats_empty():
    engine = AIBountyEngine()
    stats = engine.get_stats()
    assert stats["total_scans"] == 0
    assert stats["total_findings"] == 0


# ── Platform connector tests ──────────────────────────────────────


def test_platform_registry_has_ai_bounty():
    assert "imbue" in AI_BOUNTY_REGISTRY
    assert "anthropic" in AI_BOUNTY_REGISTRY
    assert "openai" in AI_BOUNTY_REGISTRY
    assert "google_ai" in AI_BOUNTY_REGISTRY


def test_imbue_platform():
    p = ImbueBounty()
    assert p.platform_id == "imbue"
    assert p.display_name == "Imbue AI Bounty"
    result = p.submit({}, "")
    assert result.success is False
    assert "manual" in result.error.lower()


def test_anthropic_platform():
    p = AnthropicBounty()
    assert p.platform_id == "anthropic"
    assert not p._supports_api_submission()
    result = p.submit({}, "")
    assert result.success is False


def test_openai_platform():
    p = OpenAIBounty()
    assert p.platform_id == "openai"
    formatted = p._format_report(
        {
            "vulnerability": "SSRF",
            "severity": "high",
            "content": {"description": "SSRF in API endpoint", "category": "security"},
        }
    )
    assert formatted["title"] == "SSRF"
    assert formatted["severity"] == "high"


def test_google_ai_platform():
    p = GoogleAIBounty()
    assert p.platform_id == "google_ai"
    result = p.submit({}, "")
    assert result.success is False


# ── Event types ───────────────────────────────────────────────────


def test_ai_bounty_event_types_exist():
    assert hasattr(Events, "AI_BOUNTY_CHALLENGE_DETECTED")
    assert hasattr(Events, "AI_BOUNTY_CHALLENGE_SCANNED")
    assert hasattr(Events, "AI_BOUNTY_REPORT_READY")
    assert hasattr(Events, "AI_BOUNTY_OPPORTUNITY_ASSESSED")


def test_ai_bounty_events_in_all():
    assert Events.AI_BOUNTY_CHALLENGE_DETECTED in Events.ALL
    assert Events.AI_BOUNTY_CHALLENGE_SCANNED in Events.ALL
    assert Events.AI_BOUNTY_REPORT_READY in Events.ALL
    assert Events.AI_BOUNTY_OPPORTUNITY_ASSESSED in Events.ALL


# ── Challenge model tests ─────────────────────────────────────────


def test_challenge_to_dict():
    c = AIBountyChallenge(
        platform="openai",
        challenge_id="test_001",
        title="Test Challenge",
        url="https://example.com",
        targets=["api.example.com"],
    )
    d = c.to_dict()
    assert d["platform"] == "openai"
    assert d["challenge_id"] == "test_001"
    assert d["targets"] == ["api.example.com"]
    assert d["status"] == "new"


def test_challenge_defaults():
    c = AIBountyChallenge(platform="imbue", challenge_id="c1", title="T", url="")
    assert c.focus_areas == []
    assert c.targets == []
    assert c.status == "new"
    assert c.detected_at == ""


# ── Publisher tests (noop safety) ─────────────────────────────────


def test_publisher_noop_without_bus():
    p = AIBountyEventPublisher()
    p.challenge_detected("openai", "c1", "Test", "https://example.com")
    p.challenge_scanned("openai", "c1", 5, 100.0)
    p.report_ready("openai", "c1", 1, 5, 1500.0)
    p.opportunity_assessed("openai", "c1", 50.0, 4.0, "high_priority")


# ── Platform registry ─────────────────────────────────────────────


def test_platform_registry_integration():
    from cores.platforms import PLATFORM_REGISTRY, get_platform

    for pid in ("imbue", "anthropic", "openai", "google_ai"):
        assert pid in PLATFORM_REGISTRY
        p = get_platform(pid)
        assert p is not None
        assert p.platform_id == pid


def test_platform_supports_action():
    p = ImbueBounty()
    assert p.supports_action("prepare_only")
    assert p.supports_action("prepare_and_open")
    assert not p.supports_action("auto_submit")


def test_platform_format_report_string_content():
    p = OpenAIBounty()
    formatted = p._format_report(
        {
            "vulnerability": "XSS",
            "content": "Simple string summary of the vulnerability",
        }
    )
    assert formatted["title"] == "XSS"
    assert "Simple string" in formatted["description"]


def test_platform_prepare_report():
    p = AnthropicBounty()
    prepared = p.prepare_report(
        {
            "vulnerability": "Jailbreak",
            "content": {"prompt": "malicious input", "response": "harmful output"},
            "severity": "critical",
        }
    )
    assert prepared["platform"] == "anthropic"
    assert "content" in prepared
    assert prepared["content"]["title"] == "Jailbreak"
