"""Revenue-truth tests for scripts/progress.py.

Proves that no queue state can inflate VERIFIED_REVENUE without payment
evidence, and that the pipeline-progress metric stays independent from
verified money.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_progress():
    spec = importlib.util.spec_from_file_location("ownex_progress", ROOT / "scripts" / "progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def progress():
    return _load_progress()


def _write_queue(tmp_path: Path, items: dict) -> Path:
    p = tmp_path / "execution_queue.json"
    p.write_text(json.dumps(items))
    return p


def _item(state: str, finance: dict | None = None) -> dict:
    payload: dict = {}
    if finance is not None:
        payload["finance"] = finance
    return {"state": state, "payload": payload, "history": [state]}


def _finance(entries: list[dict]) -> dict:
    latest: dict[str, dict] = {}
    for e in entries:
        latest[e["bucket"]] = e
    return {"entries": entries, "latest": latest}


def _paid(amount: float = 10.0, evidence: dict | None = None, currency: str = "USD") -> dict:
    return {
        "bucket": "paid",
        "amount": amount,
        "currency": currency,
        "fees": 0.0,
        "net": amount,
        "payout_method": None,
        "paid_at": "2026-11-23T00:00:00+00:00",
        "evidence": evidence,
        "recorded_at": "2026-11-23T00:00:00+00:00",
    }


class TestVerifiedRevenue:
    def test_empty_queue_is_zero(self, progress, tmp_path):
        out = progress.verified_revenue(_write_queue(tmp_path, {}))
        assert out["verified_revenue_usd"] == 0.0
        assert out["verified_paid_cycles"] == 0
        assert out["verified_revenue_by_currency"] == {}

    def test_paid_without_evidence_does_not_count(self, progress, tmp_path):
        items = {"a": _item("paid", _finance([_paid(evidence=None)]))}
        out = progress.verified_revenue(_write_queue(tmp_path, items))
        assert out["verified_revenue_usd"] == 0.0
        assert out["verified_paid_cycles"] == 0
        # exec state claims 'paid' but the paid entry has no evidence
        # -> flagged as unverifiable, still not counted
        assert out["paid_without_evidence"] == ["a"]

    def test_paid_state_without_any_finance_is_flagged(self, progress, tmp_path):
        items = {"a": _item("paid"), "b": _item("executing")}
        out = progress.verified_revenue(_write_queue(tmp_path, items))
        assert out["paid_without_evidence"] == ["a"]
        assert out["verified_revenue_usd"] == 0.0
        assert out["verified_paid_cycles"] == 0

    def test_paid_with_evidence_counts(self, progress, tmp_path):
        ev = {"tx": "0xabc", "platform": "taskmarket"}
        items = {
            "a": _item("paid", _finance([_paid(25.0, ev)])),
            "b": _item("executing", _finance([_paid(999.0, None)])),
        }
        out = progress.verified_revenue(_write_queue(tmp_path, items))
        assert out["verified_revenue_usd"] == 25.0
        assert out["verified_paid_cycles"] == 1
        assert out["paid_without_evidence"] == []

    def test_non_usd_currency_tracked_separately(self, progress, tmp_path):
        ev = {"receipt": "r-1"}
        items = {"a": _item("paid", _finance([_paid(100.0, ev, currency="USDC")]))}
        out = progress.verified_revenue(_write_queue(tmp_path, items))
        assert out["verified_revenue_usd"] == 0.0
        assert out["verified_revenue_by_currency"] == {"USDC": 100.0}
        assert out["verified_paid_cycles"] == 1

    def test_estimate_buckets_never_count_as_revenue(self, progress, tmp_path):
        est = {k: v for k, v in _paid(500.0).items()}
        for bucket in ("advertised", "expected", "approved", "pending"):
            est["bucket"] = bucket
            items = {"a": _item("executing", _finance([dict(est)]))}
            out = progress.verified_revenue(_write_queue(tmp_path, items))
            assert out["verified_revenue_usd"] == 0.0, bucket
            assert out["verified_paid_cycles"] == 0, bucket

    def test_missing_or_corrupt_file_is_zero(self, progress, tmp_path):
        assert progress.verified_revenue(tmp_path / "nope.json")["verified_revenue_usd"] == 0.0
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        assert progress.verified_revenue(bad)["verified_paid_cycles"] == 0

    def test_realization_rate_denominator_is_committed_only(self, progress, tmp_path):
        ev = {"tx": "0x1"}
        approved = dict(_paid(100.0), bucket="approved")
        pending = dict(_paid(50.0), bucket="pending")
        advertised = dict(_paid(10000.0), bucket="advertised")
        items = {
            "a": _item("paid", _finance([_paid(30.0, ev), approved, pending, advertised])),
        }
        out = progress.verified_revenue(_write_queue(tmp_path, items))
        # committed = approved 100 + pending 50 + paid 30 = 180
        assert out["reward_realization_rate"] == pytest.approx(30.0 / 180.0, abs=1e-4)

    def test_realization_rate_none_when_nothing_committed(self, progress, tmp_path):
        out = progress.verified_revenue(_write_queue(tmp_path, {}))
        assert out["reward_realization_rate"] is None
        assert out["time_to_first_payout"] is None
