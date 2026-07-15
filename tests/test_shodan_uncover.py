"""Tests for ShodanTool and UncoverTool wrappers."""

from __future__ import annotations

from cores.tools.shodan import ShodanTool, UnifiedResult
from cores.tools.uncover import UncoverTool

# ── ShodanTool ─────────────────────────────────────────────────────


def test_shodan_init():
    tool = ShodanTool()
    assert tool.name == "shodan"
    assert "SHODAN_API_KEY" in tool.install_hint


def test_shodan_no_key():
    tool = ShodanTool(api_key="")
    assert not tool.is_available()
    results = tool.search("test.com")
    assert results == []


def test_shodan_port_severity():
    assert ShodanTool._port_severity(22) == "medium"
    assert ShodanTool._port_severity(3389) == "medium"
    assert ShodanTool._port_severity(80) == "info"
    assert ShodanTool._port_severity(443) == "info"
    assert ShodanTool._port_severity(9999) == "info"


def test_shodan_parse_search():
    tool = ShodanTool(api_key="test")
    data = {
        "total": 5,
        "matches": [
            {
                "ip_str": "1.2.3.4",
                "port": 443,
                "hostnames": ["example.com"],
                "data": [{"product": "nginx"}],
                "org": "Cloudflare",
                "os": "",
                "location": {"country_name": "US"},
                "tags": ["cloud"],
            },
            {
                "ip_str": "5.6.7.8",
                "port": 22,
                "hostnames": [],
                "data": [],
                "org": "",
                "os": "Linux",
                "location": {},
                "tags": [],
            },
        ],
    }
    results = tool._parse_search(data, "test.com")
    assert len(results) == 3  # 2 matches + 1 search_meta
    # First result should be search meta
    assert results[0].result_type == "search_meta"
    assert results[0].evidence["total"] == 5
    assert results[0].target == "test.com"
    # Port 443 match
    assert results[1].target == "1.2.3.4"
    assert results[1].severity == "info"
    assert "nginx" in str(results[1].evidence.get("services", []))
    # Port 22 match
    assert results[2].evidence["port"] == 22
    assert results[2].severity == "medium"
    assert results[2].target == "5.6.7.8"


def test_shodan_parse_search_empty():
    tool = ShodanTool(api_key="test")
    results = tool._parse_search({}, "test.com")
    assert results == []


def test_shodan_parse_host():
    tool = ShodanTool(api_key="test")
    data = {
        "ip_str": "1.2.3.4",
        "ports": [80, 443, 22, 3306],
        "hostnames": ["example.com"],
        "os": "Linux",
    }
    results = tool._parse_host(data)
    assert len(results) == 4
    assert results[0].target == "1.2.3.4"
    assert results[0].evidence["port"] == 80
    assert results[1].evidence["port"] == 443
    # Port 22 should be medium severity
    port_22 = [r for r in results if r.evidence.get("port") == 22]
    assert len(port_22) == 1
    assert port_22[0].severity == "medium"


# ── UncoverTool ────────────────────────────────────────────────────


def test_uncover_init():
    tool = UncoverTool()
    assert tool.name == "uncover"
    assert "projectdiscovery" in tool.install_hint


def test_uncover_parse_json_lines():
    tool = UncoverTool()
    sample = (
        '{"ip":"1.2.3.4","port":80,"host":"example.com","source":"shodan"}\n'
        '{"ip":"5.6.7.8","port":443,"host":"test.org","source":"censys"}\n'
        '{"ip":"1.2.3.4","port":8080,"host":"api.example.com","source":"fofa"}\n'
    )
    results = tool._parse_output(sample, "test.com")
    assert len(results) == 3
    assert results[0].target == "1.2.3.4"
    assert results[0].source == "shodan"
    assert results[0].severity == "info"
    assert results[0].evidence["port"] == 80
    assert results[0].result_type == "exposed_service"

    assert results[1].source == "censys"
    assert results[2].source == "fofa"


def test_uncover_parse_empty():
    tool = UncoverTool()
    results = tool._parse_output("", "test.com")
    assert results == []


def test_uncover_parse_malformed():
    tool = UncoverTool()
    results = tool._parse_output("not json\nbad data\n", "test.com")
    assert results == []


def test_uncover_dedup():
    """Same engine+ip+port should not appear twice."""
    tool = UncoverTool()
    sample = (
        '{"ip":"1.2.3.4","port":80,"host":"a.com","source":"shodan"}\n'
        '{"ip":"1.2.3.4","port":80,"host":"a.com","source":"shodan"}\n'
        '{"ip":"1.2.3.4","port":443,"host":"a.com","source":"shodan"}\n'
    )
    results = tool._parse_output(sample, "test.com")
    assert len(results) == 2  # 80 deduped, 443 unique


def test_uncover_result_structure():
    tool = UncoverTool()
    results = tool._parse_output(
        '{"ip":"10.0.0.1","port":22,"host":"ssh.example.com","source":"censys"}',
        "example.com",
    )
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, UnifiedResult)
    assert r.source == "censys"
    assert r.result_type == "exposed_service"
    assert r.confidence == 0.75
    assert r.evidence["port"] == 22


def test_uncover_tagging():
    tool = UncoverTool()
    results = tool._parse_output(
        '{"ip":"10.0.0.1","port":8080,"host":"proxy.example.com","source":"fofa"}',
        "example.com",
    )
    r = results[0]
    assert "fofa" in r.tags
    assert "exposed" in r.tags
    assert "port:8080" in r.tags
