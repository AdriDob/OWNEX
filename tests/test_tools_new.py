"""Tests for GitleaksTool, GarakTool, and BrowserUseTool wrappers."""

from __future__ import annotations

import json

from cores.tools.base import UnifiedResult
from cores.tools.extra import (
    BrowserUseTool,
    GarakTool,
    GitleaksTool,
)

# ── Gitleaks ──────────────────────────────────────────────


def test_gitleaks_tool_init():
    tool = GitleaksTool()
    assert tool.name == "gitleaks"
    assert tool.min_version == "8.0.0"
    assert "gitleaks" in tool.install_hint


def test_gitleaks_parse_json_list():
    tool = GitleaksTool()
    sample = json.dumps(
        [
            {
                "Description": "AWS Access Key",
                "StartLine": 42,
                "EndLine": 42,
                "Match": "AKIA1234567890123456",
                "Secret": "AKIA1234567890123456",
                "File": "src/config.py",
                "Commit": "abc123",
                "RuleID": "aws-access-key",
                "Severity": "high",
                "Fingerprint": "abc123:src/config.py:aws-access-key:42",
            },
            {
                "Description": "GitHub Token",
                "StartLine": 10,
                "File": ".env",
                "Secret": "ghp_xxxxxxxxxxxxxxxxxxxx",
                "RuleID": "github-token",
                "Severity": "medium",
                "Fingerprint": "def456:.env:github-token:10",
            },
        ]
    )
    results = tool._parse_output(sample)
    assert len(results) == 2
    assert results[0].source == "gitleaks"
    assert results[0].target == "src/config.py"
    assert results[0].result_type == "secret"
    assert results[0].severity == "high"
    assert results[0].confidence == 0.75
    assert "[aws-access-key]" in results[0].name
    assert results[1].severity == "medium"


def test_gitleaks_parse_empty():
    tool = GitleaksTool()
    assert tool._parse_output("") == []


def test_gitleaks_parse_malformed():
    tool = GitleaksTool()
    assert tool._parse_output("not json") == []


def test_gitleaks_parse_dict_findings():
    tool = GitleaksTool()
    sample = json.dumps(
        {
            "Findings": [
                {"Description": "Test", "File": "test.py", "RuleID": "test-rule", "Severity": "critical"},
            ]
        }
    )
    results = tool._parse_output(sample)
    assert len(results) == 1
    assert results[0].severity == "high"


def test_gitleaks_parse_output_calls_parse():
    tool = GitleaksTool()
    sample = json.dumps([{"Description": "Test", "File": "x.py", "RuleID": "test"}])
    results = tool.parse_output(sample)
    assert len(results) == 1


# ── Garak ─────────────────────────────────────────────────


def test_garak_tool_init():
    tool = GarakTool()
    assert tool.name == "garak"
    assert tool.min_version == "0.15.0"
    assert "garak" in tool.install_hint


def test_garak_probe_types():
    tool = GarakTool()
    assert "prompt_injection" in tool.PROBE_TYPES
    assert "jailbreak" in tool.PROBE_TYPES
    assert "data_leakage" in tool.PROBE_TYPES


def test_garak_parse_json_line_detected():
    tool = GarakTool()
    sample = json.dumps(
        {
            "probe": "promptinject",
            "detected": True,
            "output": "Model responded with restricted content",
            "detail": "Prompt injection successful",
        }
    )
    results = tool._parse_output(sample)
    assert len(results) == 1
    assert results[0].source == "garak"
    assert results[0].target == "promptinject"
    assert results[0].severity == "high"
    assert results[0].confidence == 0.7
    assert "DETECTED" in results[0].name


def test_garak_parse_json_line_clean():
    tool = GarakTool()
    sample = json.dumps(
        {
            "probe": "jailbreak",
            "detected": False,
            "output": "Model refused to respond",
        }
    )
    results = tool._parse_output(sample)
    assert len(results) == 1
    assert results[0].severity == "low"
    assert results[0].confidence == 0.5
    assert "PASS" in results[0].name


def test_garak_parse_string_detection():
    tool = GarakTool()
    sample = json.dumps(
        {
            "probe": "encoding",
            "detected": "true",
        }
    )
    results = tool._parse_output(sample)
    assert len(results) == 1


def test_garak_parse_multiple_lines():
    tool = GarakTool()
    samples = "\n".join(
        [
            json.dumps({"probe": "p1", "detected": True, "output": "vuln"}),
            json.dumps({"probe": "p2", "detected": False, "output": "safe"}),
        ]
    )
    results = tool._parse_output(samples)
    assert len(results) == 2


def test_garak_parse_text_fallback():
    tool = GarakTool()
    results = tool._parse_output("FAIL: prompt injection detected\nPASS: encoding test")
    assert len(results) == 2


def test_garak_parse_empty():
    tool = GarakTool()
    assert tool._parse_output("") == []


def test_garak_parse_output_wrapper():
    tool = GarakTool()
    sample = json.dumps({"probe": "test", "detected": False})
    results = tool.parse_output(sample)
    assert len(results) == 1


# ── Browser Use ───────────────────────────────────────────


def test_browser_use_tool_init():
    tool = BrowserUseTool()
    assert tool.name == "browser_use"
    assert "browser-use" in tool.install_hint


def test_browser_use_is_available_returns_false_when_not_installed():
    tool = BrowserUseTool()
    # browser-use is not installed in test env
    assert tool.is_available() is False


def test_browser_use_run_returns_error_when_not_installed():
    tool = BrowserUseTool()
    result = tool.run_task("navigate to example.com")
    assert result.success is False
    assert "browser-use not installed" in result.error


def test_browser_use_run_uses_args_as_task():
    tool = BrowserUseTool()
    result = tool.run(["test", "task"], timeout=10)
    assert result.success is False


def test_browser_use_parse_output():
    tool = BrowserUseTool()
    assert tool.parse_output("") == []


# ── Pipeline integration ──────────────────────────────────


def test_tools_are_in_registry():
    from cores.tools.extra import TOOL_REGISTRY

    assert "gitleaks" in TOOL_REGISTRY
    assert "garak" in TOOL_REGISTRY
    assert "browser_use" in TOOL_REGISTRY
    assert TOOL_REGISTRY["gitleaks"] is GitleaksTool
    assert TOOL_REGISTRY["garak"] is GarakTool
    assert TOOL_REGISTRY["browser_use"] is BrowserUseTool


def test_tools_can_instantiate_from_registry():
    from cores.tools.extra import instantiate_tool

    for name in ("gitleaks", "garak", "browser_use"):
        tool = instantiate_tool(name)
        assert tool is not None
        assert tool.name.replace("_", "") == name.replace("_", "")


def test_unknown_tool_returns_none():
    from cores.tools.extra import instantiate_tool

    assert instantiate_tool("nonexistent_tool_xyz") is None


def test_unified_result_structure():
    r = UnifiedResult(
        source="gitleaks",
        target="test.py",
        result_type="secret",
        severity="high",
        confidence=0.75,
        name="Test finding",
        evidence={"key": "value"},
        tags=["test"],
    )
    assert r.source == "gitleaks"
    assert r.result_type == "secret"
    assert r.severity == "high"
    assert 0 <= r.confidence <= 1
    assert isinstance(r.evidence, dict)
    assert isinstance(r.tags, list)
