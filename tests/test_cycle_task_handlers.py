"""Tests for scheduler task handlers in cores/cycles/tasks.py.

Regression cover for dead scheduler jobs: every handler string registered in
cores/scheduler/jobs.py must resolve to a callable (lifespan._resolve_handler
silently no-ops otherwise, killing the autonomous loop without a trace).

The auto-submit sweep is tested against the isolated test DB (conftest redirects
DATABASE_URL to a per-PID temp sqlite): confirmed findings flow through the
AutoSubmitPipeline elite gate; already-submitted findings are skipped.
"""

from __future__ import annotations

import importlib
import json
from typing import Any
from unittest.mock import MagicMock, patch

from cores.scheduler.jobs import get_all_jobs


def _resolve(handler: str) -> Any | None:
    """Faithful mirror of api/lifespan._resolve_handler (both module:attr
    and bare dotted-path formats)."""
    if ":" in handler:
        module_path, attr_path = handler.split(":", 1)
    else:
        module_path, attr_path = handler, ""
    try:
        if not attr_path:
            parts = module_path.split(".")
            for cut in range(len(parts) - 1, 0, -1):
                try:
                    obj = importlib.import_module(".".join(parts[:cut]))
                except Exception:
                    continue
                for part in parts[cut:]:
                    obj = getattr(obj, part)
                if callable(obj):
                    return obj
            return None
        obj = importlib.import_module(module_path)
        for part in attr_path.split("."):
            obj = getattr(obj, part)
        return obj if callable(obj) else None
    except Exception:
        return None


class TestAllJobHandlersResolve:
    def test_every_registered_handler_resolves_to_callable(self):
        dead = []
        total = 0
        for _cycle, jobs in get_all_jobs().items():
            for job in jobs:
                total += 1
                handler = job.handler
                if callable(handler):
                    continue  # lifespan accepts callables directly
                if _resolve(handler) is None:
                    dead.append(f"{job.job_id} -> {handler}")
        assert total > 0
        assert dead == [], f"{len(dead)} dead scheduler jobs (silent no-ops):\n" + "\n".join(dead)

    def test_security_auto_submit_handler_exists(self):
        from cores.cycles import tasks

        assert callable(tasks.auto_submit_pending_findings)

    def test_security_cycle_start_handler_exists(self):
        from cores.cycles import tasks

        assert callable(tasks.auto_start_security_cycle)


def _make_finding(session, models, **kw) -> Any:
    target = models.Target(name="hackerone_test-target", domain="test-target.example.com")
    session.add(target)
    session.commit()
    args = {"title": "t", "severity": "high", "status": "confirmed", "target_id": target.id, **kw}
    f = models.Finding(**args)
    session.add(f)
    session.commit()
    return f


class TestAutoSubmitSweep:
    def test_sweep_empty_db(self):
        from cores.cycles.tasks import auto_submit_pending_findings

        result = auto_submit_pending_findings()
        assert result["status"] == "ok"
        assert result["scanned"] == 0
        assert result["actions"] == []

    def test_sweep_submits_unsubmitted_confirmed(self):
        from cores.cycles.tasks import auto_submit_pending_findings
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(session, models, title="SQLi in login")
            fid = f.id
        finally:
            session.close()

        fake_pipeline = MagicMock()
        fake_pipeline.on_finding_confirmed.return_value = {
            "action": "queued_for_review",
            "score": 70.0,
            "platform": "hackerone",
            "finding_id": fid,
        }
        with patch(
            "cores.auto_submit.pipeline.get_auto_submit_pipeline",
            return_value=fake_pipeline,
        ):
            result = auto_submit_pending_findings()

        assert result["status"] == "ok"
        assert result["scanned"] >= 1
        called_ids = [c.args[0] for c in fake_pipeline.on_finding_confirmed.call_args_list]
        assert fid in called_ids

    def test_sweep_skips_already_submitted(self):
        from cores.cycles.tasks import auto_submit_pending_findings
        from database import db, models

        session = db.SessionLocal()
        try:
            f = _make_finding(session, models, title="Already out")
            fid = f.id
            rep = models.Report(
                finding_ids=json.dumps([fid]),
                status="submitted",
                format="markdown",
            )
            session.add(rep)
            session.commit()
        finally:
            session.close()

        fake_pipeline = MagicMock()
        with patch(
            "cores.auto_submit.pipeline.get_auto_submit_pipeline",
            return_value=fake_pipeline,
        ):
            result = auto_submit_pending_findings()

        assert result["status"] == "ok"
        called_ids = [c.args[0] for c in fake_pipeline.on_finding_confirmed.call_args_list]
        assert fid not in called_ids

    def test_sweep_never_raises(self):
        from cores.cycles.tasks import auto_submit_pending_findings
        from database import db, models

        session = db.SessionLocal()
        try:
            _make_finding(session, models, title="Will explode")
        finally:
            session.close()

        with patch(
            "cores.auto_submit.pipeline.get_auto_submit_pipeline",
            side_effect=RuntimeError("boom"),
        ):
            result = auto_submit_pending_findings()
        assert result["status"] == "error"
        assert "message" in result


class TestOtherPortedHandlers:
    def test_auto_start_skips_running_cycle(self):
        from cores.cycles.tasks import auto_start_security_cycle

        fake_cycle = MagicMock()
        fake_cycle.ensure_cycle.return_value = MagicMock(status="running")
        with patch("cores.cycles.tasks.get_security_cycle", return_value=fake_cycle):
            result = auto_start_security_cycle()
        assert result["status"] == "skipped"

    def test_qa_cycle_skips_when_running(self):
        from cores.cycles.tasks import run_qa_cycle

        fake_qa = MagicMock()
        fake_qa.ensure_cycle.return_value = MagicMock(status="running")
        with patch("cores.cycles.qa.get_qa_cycle", return_value=fake_qa):
            result = run_qa_cycle()
        assert result["status"] == "skipped"

    def test_market_evolution_smoke(self):
        from cores.cycles.tasks import run_daily_market_evolution

        fake_engine = MagicMock()
        fake_engine.analyze.return_value = {
            "platforms_analyzed": 3,
            "new_ecosystems_discovered": 0,
            "rejected_platforms": 0,
            "best_recommendation": None,
            "friction_summary": {},
        }
        with patch(
            "cores.direct_work_engine.market_evolution.get_market_evolution_engine",
            return_value=fake_engine,
        ):
            result = run_daily_market_evolution()
        assert result["status"] == "ok"
        assert result["platforms_analyzed"] == 3
