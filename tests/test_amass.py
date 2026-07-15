"""Tests for AmassTool wrapper."""

from __future__ import annotations

from cores.tools.amass import AmassTool, UnifiedResult


def test_amass_tool_init():
    tool = AmassTool()
    assert tool.name == "amass"
    assert tool.min_version == "4.0.0"
    assert "owasp-amass" in tool.install_hint


def test_amass_parse_json_lines():
    tool = AmassTool()
    sample = (
        '{"name":"sub.example.com","domain":"example.com","addresses":[{"ip":"1.2.3.4"}],"event_type":"subdomain"}\n'
        '{"name":"mail.example.com","domain":"example.com","addresses":[],"event_type":"cert"}\n'
        '{"domain":"example.com","addresses":[],"event_type":"synced"}\n'
    )
    results = tool._parse_json_lines(sample)
    assert len(results) == 2  # synced filtered out
    assert results[0].target == "sub.example.com"
    assert results[0].result_type == "resolved_subdomain"  # has addresses
    assert results[0].severity == "info"
    assert results[0].source == "amass"
    assert "1.2.3.4" in results[0].description
    # cert type
    assert results[1].result_type == "certificate"
    assert results[1].target == "mail.example.com"


def test_amass_parse_empty():
    tool = AmassTool()
    results = tool._parse_json_lines("")
    assert results == []


def test_amass_parse_malformed():
    tool = AmassTool()
    results = tool._parse_json_lines('not json\n{"bad": json\n')
    assert results == []


def test_amass_unified_result_structure():
    tool = AmassTool()
    results = tool._parse_json_lines(
        '{"name":"api.example.com","domain":"example.com","addresses":[{"ip":"10.0.0.1"}],"event_type":"subdomain","tag":"dns"}'
    )
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, UnifiedResult)
    assert r.source == "amass"
    assert r.result_type == "resolved_subdomain"  # has addresses
    assert r.confidence == 0.8
    assert r.tags == ["subdomain", "resolved_subdomain", "example.com"]
