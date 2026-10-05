"""Tests Bounty Tracker — estados persistentes + PAID con evidencia + puente learning."""

from __future__ import annotations

import pytest

from cores.opportunity.bounty_tracker import BountyTracker


def _tracker(tmp_path) -> BountyTracker:
    return BountyTracker(store_path=tmp_path / "bounties.json")


class TestLifecycle:
    def test_track_y_transiciones(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        assert b.status == "claimed"
        t.set_pr(b.id, "https://github.com/o/r/pull/2")
        assert t.get(b.id) is not None and t.get(b.id).status == "pr_open"
        t.set_merged(b.id, "abc123")
        assert t.get(b.id).status == "merged"
        t.set_paid(b.id, 150.0, "algora-payout-9")
        done = t.get(b.id)
        assert done is not None
        assert done.status == "paid" and done.amount_usd == 150.0

    def test_track_idempotente(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        a = t.track("algora", "https://github.com/o/r/issues/1")
        b = t.track("algora", "https://github.com/o/r/issues/1")
        assert a.id == b.id and len(t.list()) == 1

    def test_track_url_vacia_falla(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            _tracker(tmp_path).track("algora", "   ")

    def test_unknown_id_falla(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        with pytest.raises(KeyError):
            t.set_pr("nope", "https://x/y")
        with pytest.raises(KeyError):
            t.set_paid("nope", 10.0, "ref")

    def test_set_failed_y_expire(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("opire", "https://opire.dev/i/1")
        t.set_failed(b.id, "cerrado sin merge")
        got = t.get(b.id)
        assert got is not None and got.status == "failed"
        c = t.track("opire", "https://opire.dev/i/2")
        t.expire(c.id)
        got2 = t.get(c.id)
        assert got2 is not None and got2.status == "expired"


class TestPaidGate:
    def test_paid_sin_monto_falla(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        with pytest.raises(ValueError):
            t.set_paid(b.id, 0.0, "ref-1")
        got = t.get(b.id)
        assert got is not None and got.status == "claimed"

    def test_paid_sin_ref_falla(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        with pytest.raises(ValueError):
            t.set_paid(b.id, 100.0, "  ")
        got = t.get(b.id)
        assert got is not None and got.status == "claimed"


class TestPersistence:
    def test_roundtrip_sobrevive_restart(self, tmp_path) -> None:
        t1 = _tracker(tmp_path)
        b = t1.track("algora", "https://github.com/o/r/issues/1")
        t1.set_pr(b.id, "https://github.com/o/r/pull/2")
        t2 = BountyTracker(store_path=tmp_path / "bounties.json")
        assert t2.get(b.id).status == "pr_open"

    def test_store_corrupto_empieza_vacio(self, tmp_path) -> None:
        bad = tmp_path / "bounties.json"
        bad.write_text("{roto", encoding="utf-8")
        assert BountyTracker(store_path=bad).list() == []

    def test_pending_solo_en_vuelo(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        a = t.track("a", "https://x/1")
        b = t.track("b", "https://x/2")
        t.set_paid(b.id, 50.0, "ref-b")
        assert [i.id for i in t.pending()] == [a.id]


class TestLearningBridge:
    def test_paid_da_record_pagado(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        t.set_paid(b.id, 200.0, "payout-1")
        rec = t.to_learning_record(b.id)
        assert rec is not None
        assert rec.accepted is True and rec.paid is True and rec.net_amount == 200.0

    def test_merged_cuenta_sin_cash(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        t.set_merged(b.id, "sha1")
        rec = t.to_learning_record(b.id)
        assert rec is not None
        assert rec.accepted is True and rec.paid is False

    def test_abierto_no_es_outcome(self, tmp_path) -> None:
        t = _tracker(tmp_path)
        b = t.track("algora", "https://github.com/o/r/issues/1")
        assert t.to_learning_record(b.id) is None
