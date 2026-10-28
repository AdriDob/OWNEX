"""Tests Repro Harness — gate ≥50%, 100% offline con executors inyectados."""

from __future__ import annotations

import pytest

from cores.validation.repro_harness import DEFAULT_ATTEMPTS, OPENAI_THRESHOLD, run_repro


def test_all_pass() -> None:
    r = run_repro(lambda i: True, n=10)
    assert (r.successes, r.rate, r.passed) == (10, 1.0, True)
    assert r.to_dict()["verdict"] == "REPORTABLE"


def test_all_fail() -> None:
    r = run_repro(lambda i: False, n=10)
    assert (r.successes, r.rate, r.passed) == (0, 0.0, False)
    assert r.to_dict()["verdict"] == "NOT_REPORTABLE"


def test_exactly_fifty_percent_passes() -> None:
    r = run_repro(lambda i: i % 2 == 0, n=10)
    assert r.rate == 0.5 and r.passed is True


def test_forty_percent_fails() -> None:
    r = run_repro(lambda i: i < 4, n=10)
    assert r.rate == 0.4 and r.passed is False
    assert "40%" in r.to_dict()["recommendation"]


def test_custom_threshold() -> None:
    assert run_repro(lambda i: True, n=4, threshold=1.0).passed is True
    assert run_repro(lambda i: i < 3, n=4, threshold=1.0).passed is False


def test_executor_exception_counts_as_failure_with_note() -> None:
    def boom(i: int) -> bool:
        if i == 0:
            raise RuntimeError("lab exploded")
        return True

    r = run_repro(boom, n=5)
    assert r.successes == 4 and r.rate == 0.8 and r.passed is True
    assert any("attempt 0" in note for note in r.notes)


def test_single_attempt() -> None:
    assert run_repro(lambda i: True, n=1).passed is True
    assert run_repro(lambda i: False, n=1).passed is False


def test_invalid_n_fail_closed() -> None:
    with pytest.raises(ValueError):
        run_repro(lambda i: True, n=0)


def test_invalid_threshold_fail_closed() -> None:
    with pytest.raises(ValueError):
        run_repro(lambda i: True, n=10, threshold=1.5)


def test_defaults_match_openai_requirement() -> None:
    assert DEFAULT_ATTEMPTS == 10 and OPENAI_THRESHOLD == 0.5
