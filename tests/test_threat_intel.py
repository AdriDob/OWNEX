"""Tests for cores/engine/hypothesis/threat_intel — capa extra de OWNEX.

Cubren: cache degradation, correlación tech-stack, likelihood, source tagging,
empty tech / unavailable feed, y que el engine incorpora el source en by_source.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cores.engine.hypothesis.engine import HypothesisEngine
from cores.engine.hypothesis.models import HypothesisSource
from cores.engine.hypothesis.threat_intel import (
    ThreatIntelFeed,
    _KevEntry,
    generate_from_threat_intel,
)


@pytest.fixture
def kev_entries() -> list[_KevEntry]:
    return [
        _KevEntry(
            cve_id="CVE-2023-34362",
            vendor_project="progress software",
            product="moveit transfer",
            short_description="MoveIt Transfer exploitation in the wild",
            technical_alert=True,
            severity="critical",
            date_added="2023-06-29",
            required_action="Apply vendor patches immediately",
            days_since_added=10,
        ),
        _KevEntry(
            cve_id="CVE-2022-30190",
            vendor_project="microsoft",
            product="windows",
            short_description="Follina remote code execution",
            technical_alert=False,
            severity="high",
            date_added="2022-06-01",
            required_action="Disable RDP",
            days_since_added=800,
        ),
    ]


@pytest.fixture
def mock_feed(kev_entries: list[_KevEntry]) -> MagicMock:
    feed = MagicMock(spec=ThreatIntelFeed)
    feed.load.return_value = kev_entries
    return feed


class TestThreatIntelCorrelation:
    def test_correlates_matching_tech(self, mock_feed: MagicMock) -> None:
        tech = [{"name": "MoveIt Transfer", "vendor": "Progress Software"}]
        hyps = generate_from_threat_intel(1, "target", technologies=tech, feed=mock_feed)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type.value == "known_vulnerability"
        assert hyps[0].source == HypothesisSource.THREAT_INTEL
        assert "CVE-2023-34362" in hyps[0].reasoning

    def test_no_match_returns_empty(self, mock_feed: MagicMock) -> None:
        hyps = generate_from_threat_intel(1, "t", technologies=[{"name": "totally-foreign-product"}], feed=mock_feed)
        assert hyps == []

    def test_empty_tech_returns_empty(self, mock_feed: MagicMock) -> None:
        assert generate_from_threat_intel(1, "t", technologies=None, feed=mock_feed) == []
        assert generate_from_threat_intel(1, "t", technologies=[], feed=mock_feed) == []

    def test_likelihood_boosted_by_recency(self, mock_feed: MagicMock) -> None:
        tech = [{"name": "moveit transfer"}]
        hyps = generate_from_threat_intel(1, "t", technologies=tech, feed=mock_feed)
        # CVE-2023-34362: critical + technical_alert + days=10 → likelihood > 0.75
        assert hyps[0].likelihood > 0.75

    def test_likelihood_lower_for_old_no_ra(self, mock_feed: MagicMock) -> None:
        tech = [{"name": "windows"}]
        hyps = generate_from_threat_intel(1, "t", technologies=tech, feed=mock_feed)
        # CVE-2022-30190: no technical_alert, days=800 → likelihood < fresh match
        assert hyps[0].likelihood < 0.75

    def test_sources_unique_per_cve(self, mock_feed: MagicMock) -> None:
        tech = [{"name": "moveit"}]
        hyps = generate_from_threat_intel(1, "t", technologies=tech, endpoint={"path": "/api"}, feed=mock_feed)
        assert len({h.id for h in hyps}) == len(hyps)


class TestThreatIntelFeedCache:
    def test_degrades_to_cache_on_network_failure(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("cores.engine.hypothesis.threat_intel._CACHE_DIR", str(tmp_path))
        cache_file = tmp_path / "kev_cache.json"
        cache_file.write_text(json.dumps({"vulnerabilities": [], "_fetched_at": "2020-01-01T00:00:00+00:00"}))
        feed = ThreatIntelFeed(cache_dir=str(tmp_path))
        with patch(
            "cores.engine.hypothesis.threat_intel.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")
        ):
            entries = feed.load()
        assert entries == []

    def test_returns_empty_when_no_cache_and_no_network(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("cores.engine.hypothesis.threat_intel._CACHE_DIR", str(tmp_path))
        feed = ThreatIntelFeed(cache_dir=str(tmp_path))
        with patch(
            "cores.engine.hypothesis.threat_intel.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")
        ):
            assert feed.load() == []


class TestEngineIntegration:
    def test_by_source_includes_threat_intel(self, mock_feed: MagicMock) -> None:
        engine = HypothesisEngine()
        engine._kev_feed = mock_feed  # inject mock feed
        tech = [{"name": "MoveIt Transfer", "vendor": "Progress Software"}]
        out = engine.run(
            target_id=1,
            target_name="demo",
            endpoints=[{"id": 1, "path": "/api/upload", "method": "POST", "risk_score": 0.5}],
            attack_surface_map={"technologies": tech},
        )
        assert out.by_source.get("threat_intel", 0) >= 1
        assert any(h.source == HypothesisSource.THREAT_INTEL for h in out.attack_queue.hypotheses)
