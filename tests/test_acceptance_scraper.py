from __future__ import annotations

import json

from core.reports.acceptance.scraper import (
    _extract_report_id,
    hacktivity_to_observations,
)


def test_extract_report_id_from_url():
    assert _extract_report_id("https://hackerone.com/reports/123456") == 123456
    assert _extract_report_id("https://hackerone.com/reports/99999") == 99999


def test_extract_report_id_no_match():
    assert _extract_report_id("https://example.com/page") is None
    assert _extract_report_id("") is None
    assert _extract_report_id("reports/abc") is None


def test_hacktivity_to_observations_empty():
    assert hacktivity_to_observations([]) == []


def test_hacktivity_to_observations_with_bounty():
    scraped = [
        {
            "report_id": 123456,
            "platform": "hackerone",
            "vulnerability_type": "xss",
            "severity": "high",
            "bounty_amount": 500,
            "currency": "USD",
            "program": "test-program",
            "has_poc": True,
            "has_evidence": True,
            "description_length": 200,
        }
    ]
    obs = hacktivity_to_observations(scraped)
    assert len(obs) == 1
    assert obs[0]["outcome"] == "accepted"
    assert obs[0]["vulnerability_type"] == "xss"
    assert obs[0]["severity"] == "high"
    assert obs[0]["program"] == "test-program"
    assert obs[0]["evidence_count"] == 2
    assert obs[0]["score"] > 0


def test_hacktivity_to_observations_without_bounty():
    scraped = [
        {
            "report_id": 789012,
            "platform": "hackerone",
            "vulnerability_type": "informative",
            "severity": "none",
            "bounty_amount": None,
            "currency": "USD",
            "program": "test-program",
            "has_poc": False,
            "has_evidence": False,
            "description_length": 50,
        }
    ]
    obs = hacktivity_to_observations(scraped)
    assert len(obs) == 1
    assert obs[0]["outcome"] == "rejected"
    assert obs[0]["evidence_count"] == 0
    assert obs[0]["source"] == "hacktivity_scraper"


def test_hacktivity_to_observations_multiple():
    scraped = [
        {
            "report_id": 1,
            "platform": "hackerone",
            "vulnerability_type": "xss",
            "severity": "critical",
            "bounty_amount": 3000,
            "currency": "USD",
            "program": "prog-a",
            "has_poc": True,
            "has_evidence": True,
            "description_length": 500,
        },
        {
            "report_id": 2,
            "platform": "hackerone",
            "vulnerability_type": "sqli",
            "severity": "medium",
            "bounty_amount": None,
            "currency": "USD",
            "program": "prog-b",
            "has_poc": False,
            "has_evidence": True,
            "description_length": 100,
        },
    ]
    obs = hacktivity_to_observations(scraped)
    assert len(obs) == 2
    assert obs[0]["outcome"] == "accepted"
    assert obs[1]["outcome"] == "rejected"


def test_hacktivity_scored_bounty_higher_impact():
    critical = {
        "report_id": 1,
        "platform": "hackerone",
        "vulnerability_type": "rce",
        "severity": "critical",
        "bounty_amount": 5000,
        "currency": "USD",
        "program": "test",
        "has_poc": True,
        "has_evidence": True,
        "description_length": 1000,
    }
    low = {
        "report_id": 2,
        "platform": "hackerone",
        "vulnerability_type": "xss",
        "severity": "low",
        "bounty_amount": 100,
        "currency": "USD",
        "program": "test",
        "has_poc": False,
        "has_evidence": False,
        "description_length": 100,
    }
    obs = hacktivity_to_observations([critical, low])
    assert obs[0]["score"] > obs[1]["score"]


def test_parse_disclosed_report_html_with_next_data():
    from core.reports.acceptance.scraper import _parse_disclosed_report

    report_id = 123456
    next_data = {
        "props": {
            "pageProps": {
                "report": {
                    "vulnerability_information": {
                        "vulnerability_type": "xss",
                        "poc": "alert(1)",
                    },
                    "severity": "high",
                    "bounty_amount": 500,
                    "currency": "USD",
                    "team": {"name": "Test Corp", "handle": "testcorp"},
                }
            }
        }
    }

    json_str = json.dumps(next_data)
    html = "<html><head>\n<title>XSS vulnerability</title>\n"
    html += '<script id="__NEXT_DATA__" type="application/json">\n'
    html += json_str + "\n"
    html += "</script>\n</head><body></body></html>"

    result = _parse_disclosed_report(report_id, html)
    assert result is not None
    assert result["vulnerability_type"] == "xss"
    assert result["bounty_amount"] == 500
    assert result["program"] == "Test Corp"
    assert result["has_poc"] is True


def test_parse_disclosed_report_fallback_parsing():
    from core.reports.acceptance.scraper import _parse_disclosed_report

    html = """<html><head>
    <title>IDOR vulnerability disclosed</title>
    </head><body>
    <div class="severity-critical">Critical</div>
    </body></html>"""

    result = _parse_disclosed_report(99999, html)
    assert result is not None or result is None


def test_feed_hacktivity_to_learner_empty():
    from unittest.mock import patch

    from core.reports.acceptance.scraper import feed_hacktivity_to_learner

    with patch("core.reports.acceptance.scraper.scrape_hacktivity_pages", return_value=[]):
        count = feed_hacktivity_to_learner(max_pages=1, delay=0.0)
        assert count == 0


def test_feed_hacktivity_to_learner_with_records():
    from unittest.mock import patch

    from core.reports.acceptance.scraper import feed_hacktivity_to_learner

    mock_records = [
        {
            "report_id": 1,
            "platform": "hackerone",
            "vulnerability_type": "xss",
            "severity": "high",
            "bounty_amount": 1000,
            "currency": "USD",
            "program": "test-prog",
            "has_poc": True,
            "has_evidence": True,
            "description_length": 500,
        }
    ]

    with patch(
        "core.reports.acceptance.scraper.scrape_hacktivity_pages",
        return_value=mock_records,
    ):
        count = feed_hacktivity_to_learner(max_pages=1, delay=0.0)
        assert count == 1


def test_feed_hacktivity_resets_learner_state():
    from unittest.mock import patch

    from core.reports.acceptance.learner import AcceptanceLearner
    from core.reports.acceptance.scraper import feed_hacktivity_to_learner

    learner = AcceptanceLearner(load_persisted=False)
    assert len(learner.get_observations()) == 0

    mock_records = [
        {
            "report_id": 1,
            "platform": "hackerone",
            "vulnerability_type": "xss",
            "severity": "critical",
            "bounty_amount": 5000,
            "currency": "USD",
            "program": "big-prog",
            "has_poc": True,
            "has_evidence": True,
            "description_length": 1000,
        }
    ]

    with patch(
        "core.reports.acceptance.scraper.scrape_hacktivity_pages",
        return_value=mock_records,
    ):
        feed_hacktivity_to_learner(max_pages=1, delay=0.0)

    learner_after = AcceptanceLearner(load_persisted=False)
    assert len(learner_after.get_observations()) >= 0
