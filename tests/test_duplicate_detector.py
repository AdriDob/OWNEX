"""Tests confirming DuplicateDetector shares state with the unified DedupTracker (SELF-7).

The detector must delegate de-duplication to cores.dedup.get_session_tracker (the
shared, session-scoped tracker) — not maintain its own separate seen-set.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cores.analysis.duplicate_detector import DuplicateDetector
from cores.dedup import reset_session_tracker


@pytest.fixture(autouse=True)
def _reset_tracker():
    reset_session_tracker()
    yield
    reset_session_tracker()


class TestLoadHistoryDedup:
    def test_filters_duplicates_via_shared_tracker(self) -> None:
        detector = DuplicateDetector()

        finding = {"id": 1, "url": "https://api.example.com/users/123", "method": "GET"}
        dup = {"id": 2, "url": "https://api.example.com/users/999", "method": "GET"}  # normalized to same path

        detector.load_history([finding, dup])
        # Path fingerprint is normalized (IDs stripped), so the two collapse.
        assert len(detector._history) == 1

    def test_populates_session_tracker(self) -> None:
        from cores.dedup import get_session_tracker

        tracker = get_session_tracker()
        detector = DuplicateDetector()
        assert tracker.size() == 0

        detector.load_history([{"id": 1, "url": "https://api.example.com/users/123"}])
        assert tracker.size() >= 1

    def test_seen_finding_replayed_keeps_accumulated_history(self) -> None:
        detector = DuplicateDetector()
        finding = {"id": 1, "url": "https://api.example.com/users/123"}
        detector.load_history([finding])
        assert len(detector._history) == 1

        # Reload the SAME finding: tracker marks it, so no new append, but the
        # prior history must be preserved (not wiped to []).
        detector.load_history([finding])
        assert len(detector._history) == 1

    def test_empty_history_returns_unknown_assessment(self) -> None:
        detector = DuplicateDetector()
        assessment = detector.assess({"id": 1, "url": "https://x.test/a"})
        assert assessment.verdict == "unknown"
        assert assessment.risk == 0.0

    def test_tracker_injected_not_global(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = MagicMock()
        fake.seen.return_value = False
        # load_history imports get_session_tracker lazily from cores.dedup, so
        # patch the source to control injection.
        monkeypatch.setattr("cores.dedup.get_session_tracker", lambda: fake)
        detector = DuplicateDetector()
        detector.load_history([{"id": 1, "url": "https://x.test/a"}])
        assert fake.seen.called


class TestAssessSharedState:
    def test_assess_marks_fingerprint_in_shared_tracker(self) -> None:
        from cores.dedup import get_session_tracker

        tracker = get_session_tracker()
        detector = DuplicateDetector()
        detector.load_history([{"id": 1, "url": "https://api.example.com/users/123"}])

        detector.assess({"id": 2, "url": "https://api.example.com/users/999"})
        # Same normalized path -> the assessed candidate is now known session-wide.
        assert tracker.seen(detector.fingerprint({"id": 2, "url": "https://api.example.com/users/999"})) is True

    def test_assess_marks_even_without_history(self) -> None:
        from cores.dedup import get_session_tracker

        tracker = get_session_tracker()
        detector = DuplicateDetector()
        assessment = detector.assess({"id": 1, "url": "https://x.test/a"})
        assert assessment.verdict == "unknown"
        assert tracker.size() == 1

    def test_fingerprint_normalizes_ids_across_urls(self) -> None:
        detector = DuplicateDetector()
        a = detector.fingerprint({"url": "https://api.example.com/users/123", "method": "GET"})
        b = detector.fingerprint({"url": "https://api.example.com/users/999", "method": "GET"})
        assert a == b
        assert len(a) == 16

    def test_assessed_finding_skipped_by_other_consumer(self) -> None:
        from cores.dedup import get_session_tracker

        detector = DuplicateDetector()
        finding = {"id": 2, "url": "https://api.example.com/users/999"}
        detector.load_history([{"id": 1, "url": "https://api.example.com/users/123"}])
        detector.assess(finding)

        # A second consumer using the unified tracker sees the finding as done.
        assert get_session_tracker().seen(detector.fingerprint(finding)) is True
