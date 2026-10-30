"""Tests for the HHD tracker — aware-UTC migration and persisted-state safety.

Regression guard: hhd_state.json files written by older versions store NAIVE
utcnow() timestamps. After the now(UTC) migration, loading one and comparing
against aware timestamps must not raise TypeError.
"""

from __future__ import annotations

import json

import pytest

from cores.system import hhd_tracker as hhd


@pytest.fixture(autouse=True)
def _reset_tracker() -> None:
    hhd._tracker_initialized = False
    hhd._persist_path = None
    hhd._idle_seconds_accumulator = 0.0
    yield
    hhd._tracker_initialized = False
    hhd._persist_path = None


def test_roundtrip_persists_aware_timestamps(tmp_path) -> None:
    hhd.init_hhd_tracker(str(tmp_path))
    hhd.record_human_activity()

    with open(tmp_path / "hhd_state.json") as f:
        data = json.load(f)
    assert data["last_human_activity"].endswith("+00:00")
    assert data["system_start_time"].endswith("+00:00")


def test_legacy_naive_state_loads_without_typeerror(tmp_path) -> None:
    # Simulate a state file written by the pre-migration (naive utcnow) version.
    naive = "2026-08-01T10:00:00.000000"
    (tmp_path / "hhd_state.json").write_text(
        json.dumps(
            {
                "last_human_activity": naive,
                "idle_seconds_accumulator": 42.0,
                "system_start_time": naive,
                "updated_at": naive,
            }
        )
    )

    hhd.init_hhd_tracker(str(tmp_path))
    # Comparing the naive-loaded timestamp against aware now(UTC) must not raise.
    assert hhd.get_idle_seconds() >= 42.0
    assert hhd.get_uptime_hours() >= 0.0
    assert hhd.get_last_activity().tzinfo is not None


def test_idle_and_uptime_math() -> None:
    hhd.init_hhd_tracker()
    hhd.reset_tracker()
    hhd.record_human_activity()
    assert hhd.get_idle_hours() >= 0.0
    assert hhd.get_uptime_hours() >= 0.0
    summary = hhd.get_hhd_summary()
    assert "autonomy_score" in summary
    assert summary["last_human_activity"].endswith("+00:00")
