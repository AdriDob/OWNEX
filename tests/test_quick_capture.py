"""Tests for Quick Capture (cores/intake/quick_capture.py)."""

from __future__ import annotations

import pytest

from cores.intake.quick_capture import QuickCaptureEngine, get_quick_capture_engine


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    e = QuickCaptureEngine(data_dir=tmp_path)
    monkeypatch.setattr("cores.intake.quick_capture._engine", e)
    return e


def test_capture_enrichment(engine):
    rec = engine.capture("https://hackerone.com/target?id=1", "test finding")
    assert rec.id.startswith("cap_")
    assert rec.enrichment["domain"] == "hackerone.com"
    assert rec.enrichment["platform"] == "hackerone"
    assert rec.enrichment["has_params"] is True


def test_capture_guess_platform_from_domain(engine):
    rec = engine.capture("https://bugcrowd.com/programs", "bc")
    assert rec.enrichment["platform"] == "bugcrowd"


def test_capture_unknown_platform(engine):
    rec = engine.capture("https://example.com/endpoint", "generic")
    assert rec.enrichment["platform"] is None


def test_requires_focus_flag(engine):
    no_params = engine.capture("https://example.com/path", "no params")
    assert no_params.enrichment["requires_focus"] is True
    with_params = engine.capture("https://example.com/path?id=1&user=2", "params")
    assert with_params.enrichment["requires_focus"] is False


def test_list_and_get(engine):
    engine.capture("https://a.com/x", "a")
    engine.capture("https://b.com/y", "b")
    recs = engine.list()
    assert len(recs) == 2
    assert engine.get(recs[0].id) is not None


def test_mark_status(engine):
    rec = engine.capture("https://a.com/x", "a")
    assert engine.mark(rec.id, "queued") is True
    assert engine.get(rec.id).status == "queued"
    assert engine.mark("nonexistent", "queued") is False


def test_queue_to_workbank_missing(engine):
    result = engine.queue_to_workbank("missing-cap")
    assert result["queued"] is False
    assert result["error"] == "capture_not_found"


def test_queue_to_workbank_best_effort(engine, monkeypatch):
    rec = engine.capture("https://opire.dev/task", "opire task")

    # Avoid touching the real workbank: replace with fake at the module it imports from.
    class FakeBank:
        def daily_cycle(self, opps, target=1):
            return {"total_in_bank": 1}

    monkeypatch.setattr("cores.direct_work_engine.workbank.get_workbank", lambda: FakeBank())
    result = engine.queue_to_workbank(rec.id)
    assert result["queued"] is True
    assert engine.get(rec.id).status == "queued"


def test_singleton():
    assert get_quick_capture_engine() is get_quick_capture_engine()
