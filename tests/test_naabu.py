"""Tests for NaabuTool wrapper."""

from __future__ import annotations

from cores.tools.naabu import NaabuTool, UnifiedResult


def test_naabu_tool_init():
    tool = NaabuTool()
    assert tool.name == "naabu"
    assert tool.min_version == "2.0.0"
    assert "projectdiscovery" in tool.install_hint


def test_naabu_port_severity_map():
    tool = NaabuTool()
    assert tool.PORT_SEVERITY_MAP["21"] == "medium"
    assert tool.PORT_SEVERITY_MAP["443"] == "info"
    assert tool.PORT_SEVERITY_MAP["3306"] == "high"
    assert tool.PORT_SEVERITY_MAP["6379"] == "high"
    assert tool.PORT_SEVERITY_MAP.get("9999", "info") == "info"  # default


def test_naabu_parse_json_lines():
    tool = NaabuTool()
    sample = (
        '{"host":"10.0.0.1","port":80,"protocol":"tcp","service":"http","title":"Apache"}\n'
        '{"host":"10.0.0.1","port":443,"protocol":"tcp","service":"https","title":"nginx"}\n'
        '{"host":"10.0.0.1","port":3306,"protocol":"tcp","service":"mysql"}\n'
    )
    results = tool._parse_json_lines(sample)
    assert len(results) == 3
    assert results[0].target == "10.0.0.1"
    assert results[0].severity == "info"  # port 80
    assert results[1].severity == "info"  # port 443
    assert results[2].severity == "high"  # port 3306
    assert results[0].result_type == "open_port"
    assert all(r.source == "naabu" for r in results)
    assert results[0].evidence["port"] == "80"
    assert results[1].evidence["service"] == "https"


def test_naabu_parse_empty():
    tool = NaabuTool()
    results = tool._parse_json_lines("")
    assert results == []


def test_naabu_parse_malformed():
    tool = NaabuTool()
    results = tool._parse_json_lines('not json\n{"bad": json\n')
    assert results == []


def test_naabu_unified_result_structure():
    tool = NaabuTool()
    results = tool._parse_json_lines('{"host":"test.com","port":8080,"protocol":"tcp","service":"http-proxy"}')
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, UnifiedResult)
    assert r.source == "naabu"
    assert r.result_type == "open_port"
    assert r.confidence == 0.9
    assert "port" in r.evidence
    assert "8080" in r.name
