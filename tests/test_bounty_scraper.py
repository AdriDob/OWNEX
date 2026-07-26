"""Tests for BountyScraper, ProgramChangeTracker, and Discovery API."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from cores.bounty_scraper.changes import DiscoveryDiff, ProgramChangeTracker, ProgramSnapshot
from cores.bounty_scraper.scraper import BountyScraper, ScrapedProgram

# ── ProgramSnapshot ──────────────────────────────────────────────


def test_snapshot_from_scraped():
    prog = ScrapedProgram(
        name="Test Program",
        platform="hackerone",
        estimated_payout=5000,
        raw_payout_range="$1k - $5k",
        technologies=["python", "aws"],
        program_url="https://hackerone.com/test",
    )
    snap = ProgramSnapshot.from_scraped(prog)
    assert snap.name == "Test Program"
    assert snap.platform == "hackerone"
    assert snap.estimated_payout == 5000
    assert snap.key() == "hackerone:test_program"


def test_snapshot_key_normalization():
    p1 = ScrapedProgram(name="Test Program", platform="hackerone")
    p2 = ScrapedProgram(name="test   Program", platform="HACKERONE")
    s1 = ProgramSnapshot.from_scraped(p1)
    s2 = ProgramSnapshot.from_scraped(p2)
    assert s1.key() == s2.key()


# ── DiscoveryDiff ────────────────────────────────────────────────


def test_diff_empty():
    diff = DiscoveryDiff()
    assert not diff.has_changes


def test_diff_has_changes_new():
    snap = ProgramSnapshot(
        platform="hackerone",
        name="test",
        program_url="",
        estimated_payout=0,
        raw_payout_range="",
    )
    diff = DiscoveryDiff(new_programs=[snap])
    assert diff.has_changes


def test_diff_has_changes_removed():
    snap = ProgramSnapshot(
        platform="hackerone",
        name="test",
        program_url="",
        estimated_payout=0,
        raw_payout_range="",
    )
    diff = DiscoveryDiff(removed_programs=[snap])
    assert diff.has_changes


def test_diff_has_changes_updated():
    diff = DiscoveryDiff(updated_programs=[{"program": "hackerone:test", "changes": ["payout"]}])
    assert diff.has_changes


# ── ProgramChangeTracker ─────────────────────────────────────────


def test_change_tracker_empty():
    tracker = ProgramChangeTracker(path="/tmp/nonexistent_test.json")
    assert tracker.get_known_count() == 0


def test_change_tracker_first_run():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        programs = [
            ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=1000),
            ScrapedProgram(name="Prog B", platform="bugcrowd", estimated_payout=2000),
        ]
        diff = tracker.compute_diff(programs)
        assert len(diff.new_programs) == 2
        assert len(diff.removed_programs) == 0
        assert tracker.get_known_count() == 2
        assert os.path.exists(path)
    finally:
        os.unlink(path)


def test_change_tracker_no_changes():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        programs = [
            ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=1000),
            ScrapedProgram(name="Prog B", platform="bugcrowd", estimated_payout=2000),
        ]
        tracker.compute_diff(programs)

        diff2 = tracker.compute_diff(programs)
        assert len(diff2.new_programs) == 0
        assert len(diff2.removed_programs) == 0
        assert len(diff2.updated_programs) == 0
        assert tracker.get_known_count() == 2
    finally:
        os.unlink(path)


def test_change_tracker_new_program_detected():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
            ]
        )

        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
                ScrapedProgram(name="Prog B", platform="bugcrowd", estimated_payout=3000),
            ]
        )
        assert len(diff.new_programs) == 1
        assert diff.new_programs[0].name == "Prog B"
    finally:
        os.unlink(path)


def test_change_tracker_removed_program_detected():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
                ScrapedProgram(name="Prog B", platform="bugcrowd"),
            ]
        )

        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
            ]
        )
        assert len(diff.removed_programs) == 1
        assert diff.removed_programs[0].name == "Prog B"
    finally:
        os.unlink(path)


def test_change_tracker_payout_updated():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=1000),
            ]
        )

        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=5000),
            ]
        )
        assert len(diff.updated_programs) == 1
        assert "payout" in diff.updated_programs[0]["changes"]
    finally:
        os.unlink(path)


def test_change_tracker_scope_updated():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", domains=["old.com"]),
            ]
        )

        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", domains=["new.com", "old.com"]),
            ]
        )
        assert len(diff.updated_programs) == 1
        assert "scope" in diff.updated_programs[0]["changes"]
    finally:
        os.unlink(path)


def test_change_tracker_tech_updated():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", technologies=["python"]),
            ]
        )

        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", technologies=["python", "aws", "react"]),
            ]
        )
        assert len(diff.updated_programs) == 1
        assert "technologies" in diff.updated_programs[0]["changes"]
    finally:
        os.unlink(path)


def test_change_tracker_persists_state():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker1 = ProgramChangeTracker(path=path)
        tracker1.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=1000),
            ]
        )

        tracker2 = ProgramChangeTracker(path=path)
        assert tracker2.get_known_count() == 1

        diff = tracker2.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone", estimated_payout=1000),
                ScrapedProgram(name="Prog B", platform="bugcrowd"),
            ]
        )
        assert len(diff.new_programs) == 1
        assert diff.new_programs[0].name == "Prog B"
    finally:
        os.unlink(path)


def test_change_tracker_reset():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
            ]
        )
        assert tracker.get_known_count() == 1
        tracker.reset()
        assert tracker.get_known_count() == 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_change_tracker_total_counts():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        diff = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
                ScrapedProgram(name="Prog B", platform="bugcrowd"),
            ]
        )
        assert diff.total_before == 0
        assert diff.total_after == 2

        diff2 = tracker.compute_diff(
            [
                ScrapedProgram(name="Prog A", platform="hackerone"),
                ScrapedProgram(name="Prog B", platform="bugcrowd"),
                ScrapedProgram(name="Prog C", platform="intigriti"),
            ]
        )
        assert diff2.total_before == 2
        assert diff2.total_after == 3
    finally:
        os.unlink(path)


# ── BountyScraper ranking ────────────────────────────────────────


def test_prioritize_payout_desc():
    scraper = BountyScraper()
    programs = [
        ScrapedProgram(name="Low", platform="hackerone", estimated_payout=500),
        ScrapedProgram(name="High", platform="bugcrowd", estimated_payout=10000),
        ScrapedProgram(name="Mid", platform="intigriti", estimated_payout=3000),
    ]
    ranked = scraper.prioritize(programs)
    assert ranked[0].name == "High"
    assert ranked[1].name == "Mid"
    assert ranked[2].name == "Low"


def test_prioritize_new_bonus():
    scraper = BountyScraper()
    programs = [
        ScrapedProgram(name="Old High", platform="hackerone", estimated_payout=5000, is_new=False),
        ScrapedProgram(name="New Mid", platform="bugcrowd", estimated_payout=3000, is_new=True),
    ]
    ranked = scraper.prioritize(programs)
    assert ranked[0].name == "Old High"


def test_prioritize_platform_bonus():
    scraper = BountyScraper()
    programs = [
        ScrapedProgram(name="Regular", platform="yeswehack", estimated_payout=5000),
        ScrapedProgram(name="Immunefi", platform="immunefi", estimated_payout=5000),
    ]
    ranked = scraper.prioritize(programs)
    assert ranked[0].name == "Immunefi"


def test_prioritize_empty():
    scraper = BountyScraper()
    ranked = scraper.prioritize([])
    assert ranked == []


def test_prioritize_tech_bonus():
    scraper = BountyScraper()
    programs = [
        ScrapedProgram(
            name="Rich",
            platform="hackerone",
            estimated_payout=5000,
            technologies=["python", "aws", "react", "postgres", "docker"],
        ),
        ScrapedProgram(name="Poor", platform="hackerone", estimated_payout=5000, technologies=[]),
    ]
    ranked = scraper.prioritize(programs)
    assert ranked[0].name == "Rich"


# ── scrape_with_changes ─────────────────────────────────────────


def test_scrape_with_changes():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        scraper = BountyScraper()
        with patch.object(
            scraper,
            "scrape_all",
            return_value=[
                ScrapedProgram(name="Prog A", platform="hackerone"),
            ],
        ):
            programs, diff = scraper.scrape_with_changes(
                max_pages=1,
                web_search=False,
                github_search=False,
                tracker=tracker,
            )
            assert isinstance(programs, list)
            assert isinstance(diff, DiscoveryDiff)
            assert len(diff.new_programs) == 1
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_scrape_with_changes_twice():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        tracker = ProgramChangeTracker(path=path)
        scraper = BountyScraper()
        with patch.object(
            scraper,
            "scrape_all",
            return_value=[
                ScrapedProgram(name="Prog A", platform="hackerone"),
            ],
        ):
            scraper.scrape_with_changes(
                max_pages=1,
                web_search=False,
                github_search=False,
                tracker=tracker,
            )
            programs2, diff2 = scraper.scrape_with_changes(
                max_pages=1,
                web_search=False,
                github_search=False,
                tracker=tracker,
            )
            assert diff2.total_before == 1
            assert len(diff2.new_programs) == 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ── Discovery API ranking endpoint ───────────────────────────────


def test_discovery_api_ranked_endpoint():
    from api.routers.discovery import _scraper

    programs = getattr(_scraper, "_programs", [])
    ranked = _scraper.prioritize(programs) if programs else []
    assert isinstance(ranked, list)
