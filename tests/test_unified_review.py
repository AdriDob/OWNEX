"""Cola unificada: findings + workbank + assessments, ordenada por EV."""

from __future__ import annotations

from cores.direct_work_engine.workbank import WorkBank, WorkItem
from cores.review_queue import (
    ReviewItem,
    ReviewQueue,
    _assessment_review_items,
    _work_review_items,
    unified_ranked,
)


def _work(**over) -> WorkItem:
    base = {
        "id": "w1",
        "title": "Fix login bug",
        "platform": "algora",
        "category": "dev_bounty",
        "reward": 150.0,
        "barrier_score": 80.0,
        "employment_type": "bounty",
        "status": "ready_to_deliver",
    }
    base.update(over)
    return WorkItem(**base)


def _bank(tmp_path, *items) -> WorkBank:
    wb = WorkBank(store_path=tmp_path / "wb.json")
    for i in items:
        wb._items[i.id] = i
    return wb


def test_work_ready_lane_ev() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        wb = _bank(Path(tmp), _work())
        # inyectar vía store real: guardar y releer por path
        wb._save()
        out = _work_review_items(limit=10, store_path=Path(tmp) / "wb.json")
    assert len(out) == 1
    assert out[0].lane == "work" and out[0].ev_usd == 150.0
    assert out[0].tier == "HIGH_CONFIDENCE"


def test_work_needs_access_medium() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        wb = _bank(Path(tmp), _work(id="w2", status="needs_access", access_requirement="GitHub login", reward=0.0))
        wb._save()
        out = _work_review_items(limit=10, store_path=Path(tmp) / "wb.json")
    assert out[0].tier == "MEDIUM_CONFIDENCE"
    assert "GitHub login" in out[0].reason
    assert out[0].ev_usd is None


def test_work_empty_y_corrupto() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        assert _work_review_items(limit=10, store_path=Path(tmp) / "none.json") == []
        bad = Path(tmp) / "bad.json"
        bad.write_text("{no json", encoding="utf-8")
        assert _work_review_items(limit=10, store_path=bad) == []


def test_work_limit() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        wb = _bank(Path(tmp), *[_work(id=f"w{i}") for i in range(5)])
        wb._save()
        assert len(_work_review_items(limit=2, store_path=Path(tmp) / "wb.json")) == 2


def test_assessments_default_store() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        out = _assessment_review_items(limit=20, store_path=Path(tmp) / "apps.json")
    assert len(out) >= 1
    assert all(i.lane == "ai_work" and i.ev_usd is None for i in out)
    assert all(i.item_id.startswith("assess_") for i in out)


def test_assessment_accepted_skipped() -> None:
    import json
    import tempfile
    from pathlib import Path

    from cores.application_assistant import ApplicationAssistant

    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "apps.json"
        assistant = ApplicationAssistant(store)
        plan = assistant.get_plan()
        first_key = plan["platforms"][0]["key"]
        state = {first_key: {"status": "accepted", "completed_steps": [], "updated_at": None}}
        store.write_text(json.dumps(state), encoding="utf-8")
        out = _assessment_review_items(limit=50, store_path=store)
    ids = [i.item_id for i in out]
    assert f"assess_{first_key}" not in ids


def test_unified_ranked_por_ev() -> None:
    q = ReviewQueue()
    q.add(ReviewItem("a", "finding", "A", "HIGH_CONFIDENCE", 0.9, "r", lane="security"))
    q.add(ReviewItem("b", "work", "B", "HIGH_CONFIDENCE", 0.75, "r", lane="work", ev_usd=150.0))
    q.add(ReviewItem("c", "work", "C", "HIGH_CONFIDENCE", 0.8, "r", lane="work", ev_usd=50.0))
    ranked = unified_ranked(q)
    assert [i["item_id"] for i in ranked] == ["b", "c", "a"]


def test_unified_ranked_limit_y_vacio() -> None:
    assert unified_ranked(ReviewQueue()) == []
    q = ReviewQueue()
    for i in range(5):
        q.add(ReviewItem(f"x{i}", "work", "X", "MEDIUM_CONFIDENCE", 0.5, "r", lane="work", ev_usd=float(i)))
    assert len(unified_ranked(q, limit=2)) == 2
    assert unified_ranked(q, limit=2)[0]["item_id"] == "x4"


def test_build_queue_sigue_viva() -> None:
    from cores.review_queue import build_review_queue

    q = build_review_queue(limit=5)
    d = q.to_dict()
    assert {"high_confidence", "medium_confidence", "low_confidence", "total_items"} <= set(d)
