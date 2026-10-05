"""Notify-everything: events fire at real outcomes, map covers them, UI can poll.

Cubre el gap "las tuberías existen pero el agua no corre": cada test pinnea
que un resultado real del sistema (submit, claim, PR, merge, kill-switch,
finding, reporte, job muerto, payout, config pendiente) llega al EventBus
o a un endpoint consumible por el frontend.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.notifications import router as notif_router

app = FastAPI()
app.include_router(notif_router)
client = TestClient(app)


def _recorder(monkeypatch):
    """Parchea emit() y graba (event, payload)."""
    calls: list = []

    def fake_emit(event_type: str, **payload):
        calls.append((event_type, payload))
        return True

    monkeypatch.setattr("cores.notifications.emit.emit", fake_emit)
    return calls


def _clear_table(model) -> None:
    """Empty a table from the shared test DB (best effort)."""
    try:
        from database.db import engine

        model.__table__.create(bind=engine, checkfirst=True)
        with engine.begin() as conn:
            conn.execute(model.__table__.delete())
    except Exception:  # noqa: BLE001 — isolation is best-effort
        pass


class TestEmitHelper:
    def test_emit_publishes(self, monkeypatch) -> None:
        from cores.notifications import emit as emit_mod

        seen = {}
        fake_bus = SimpleNamespace(publish=lambda et, **kw: seen.update({"et": et, **kw}))
        monkeypatch.setattr("cores.events.event_bus.get_event_bus", lambda: fake_bus)
        assert emit_mod.emit("finding:confirmed", message="x", id="1") is True
        assert seen["et"] == "finding:confirmed"
        assert seen["message"] == "x"

    def test_emit_never_raises(self, monkeypatch) -> None:
        from cores.notifications import emit as emit_mod

        def boom():
            raise RuntimeError("bus down")

        monkeypatch.setattr("cores.events.event_bus.get_event_bus", boom)
        assert emit_mod.emit("finding:confirmed", message="x") is False


class TestPushMapCoverage:
    EXPECTED = [
        "submission:submitted",
        "submission:confirmed",
        "submission:dead_letter",
        "devbounty:claimed",
        "devbounty:claim_failed",
        "devbounty:pr_created",
        "devbounty:merged_paid",
        "devbounty:merge_pending",
        "trading:killswitch_on",
        "trading:killswitch_off",
        "scheduler:job_failed",
        "revenue:payout_recorded",
    ]

    def test_all_new_events_mapped(self) -> None:
        from cores.notifications.push import EVENT_PUSH_MAP

        for key in self.EXPECTED:
            assert key in EVENT_PUSH_MAP, f"sin mapa: {key}"
            assert EVENT_PUSH_MAP[key].get("title")
            assert EVENT_PUSH_MAP[key].get("priority")

    def test_money_events_are_critical(self) -> None:
        from cores.notifications.push import EVENT_PUSH_MAP

        assert EVENT_PUSH_MAP["devbounty:merged_paid"]["priority"] == "critical"
        assert EVENT_PUSH_MAP["revenue:payout_recorded"]["priority"] == "critical"
        assert EVENT_PUSH_MAP["trading:killswitch_on"]["priority"] == "critical"


class TestAutoSubmitEmits:
    def _engine(self, monkeypatch, tmp_path, token="tok"):
        from cores.opportunity.executors.auto_submit import AutoSubmitEngine

        class FakeVault:
            def get_credentials(self, provider: str) -> dict:
                return {"token": token} if token else {}

        e = AutoSubmitEngine(vault=FakeVault(), dlq_path=str(tmp_path / "dlq"), queue_path=str(tmp_path / "queue.json"))
        e.base_retry_delay = 0
        e.max_retry_delay = 0
        return e

    def _prep(self, monkeypatch) -> None:
        import cores.opportunity.executors.assisted_mode as assisted_mod

        class _P:
            platform = "algora"
            title = "t"
            files = {"work.md": "# ok"}
            metadata = {"opportunity": {"title": "t"}}
            submission_url = None

        async def _prepare(self, opportunity):
            return _P()

        async def _save(self, prepared):
            from pathlib import Path

            return Path("/tmp/pkg")

        monkeypatch.setattr(assisted_mod.AssistedExecutor, "prepare_work", _prepare)
        monkeypatch.setattr(assisted_mod.AssistedExecutor, "save_work_to_disk", _save)

    def test_confirmed_emits(self, monkeypatch, tmp_path) -> None:
        from cores.opportunity.executors.algora_executor import AlgoraDweAdapter
        from cores.opportunity.executors.auto_submit import SubmissionStatus

        calls = _recorder(monkeypatch)
        e = self._engine(monkeypatch, tmp_path)
        self._prep(monkeypatch)
        monkeypatch.setattr(e, "_get_adapter", lambda key: AlgoraDweAdapter(github_token="t"))
        monkeypatch.setattr(
            AlgoraDweAdapter, "submit_work", AsyncMock(return_value={"success": True, "external_id": "pr-1"})
        )
        monkeypatch.setattr(e, "_poll_confirmation", AsyncMock(return_value=True))
        import asyncio

        rec = asyncio.run(e.submit_workbank_item("wb-1", "algora", {"id": "wb-1", "title": "t"}))
        assert rec.status == SubmissionStatus.CONFIRMED
        assert any(et == "submission:confirmed" for et, _ in calls)

    def test_submitted_emits_when_unconfirmed(self, monkeypatch, tmp_path) -> None:
        from cores.opportunity.executors.algora_executor import AlgoraDweAdapter
        from cores.opportunity.executors.auto_submit import SubmissionStatus

        calls = _recorder(monkeypatch)
        e = self._engine(monkeypatch, tmp_path)
        self._prep(monkeypatch)
        monkeypatch.setattr(e, "_get_adapter", lambda key: AlgoraDweAdapter(github_token="t"))
        monkeypatch.setattr(
            AlgoraDweAdapter, "submit_work", AsyncMock(return_value={"success": True, "external_id": "pr-1"})
        )
        monkeypatch.setattr(e, "_poll_confirmation", AsyncMock(return_value=False))
        import asyncio

        rec = asyncio.run(e.submit_workbank_item("wb-1", "algora", {"id": "wb-1", "title": "t"}))
        assert rec.status == SubmissionStatus.SUBMITTED
        assert any(et == "submission:submitted" for et, _ in calls)

    def test_dlq_emits(self, monkeypatch, tmp_path) -> None:
        from cores.opportunity.executors.auto_submit import SubmissionStatus

        calls = _recorder(monkeypatch)
        e = self._engine(monkeypatch, tmp_path, token="")
        self._prep(monkeypatch)
        e.max_attempts = 1
        import asyncio

        rec = asyncio.run(e.submit_workbank_item("wb-9", "algora", {"id": "wb-9", "title": "t"}))
        assert rec.status == SubmissionStatus.DLQ
        assert any(et == "submission:dead_letter" for et, _ in calls)


class TestAlgoraEmits:
    def _executor(self):
        from cores.opportunity.executors.algora_executor import AlgoraConfig, AlgoraExecutor

        return AlgoraExecutor(AlgoraConfig(github_token="gh_test"))

    def test_claim_failed_emits(self, monkeypatch) -> None:
        calls = _recorder(monkeypatch)
        fake = SimpleNamespace(status_code=409, text="taken")
        import asyncio

        async def run():
            from cores.opportunity.executors import algora_executor as mod

            with patch.object(
                mod.AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(fake))
            ):
                with patch.object(
                    mod.AlgoraExecutor, "clone_repo", new=AsyncMock(side_effect=AssertionError("no-clone"))
                ):
                    return await mod.AlgoraExecutor(mod.AlgoraConfig(github_token="t")).execute_bounty(
                        "https://algora.io/issues/o/r/1", {}, "fix"
                    )

        out = asyncio.run(run())
        assert out["success"] is False and out["stage"] == "claim"
        assert any(et == "devbounty:claim_failed" for et, _ in calls)

    def test_claim_pr_merge_emits(self, monkeypatch, tmp_path) -> None:
        calls = _recorder(monkeypatch)
        import asyncio

        async def run():
            from cores.opportunity.executors import algora_executor as mod

            ok_claim = SimpleNamespace(status_code=200, json=lambda: {"claim_id": "c1"})
            ex = mod.AlgoraExecutor(mod.AlgoraConfig(github_token="t", work_dir=tmp_path))
            with patch.object(
                mod.AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(ok_claim))
            ):
                with (
                    patch.object(mod.AlgoraExecutor, "clone_repo", new=AsyncMock(return_value=tmp_path)),
                    patch("cores.opportunity.executors.algora_executor.subprocess.run") as run_cmd,
                    patch.object(
                        mod.AlgoraExecutor,
                        "create_pr",
                        new=AsyncMock(return_value=SimpleNamespace(success=True, pr_url="https://x/pr/1", pr_number=1)),
                    ),
                    patch.object(mod.AlgoraExecutor, "_poll_for_merge", new=AsyncMock(return_value=True)),
                ):
                    run_cmd.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
                    return await ex.execute_bounty("https://algora.io/issues/o/r/1", {"a.md": "#"}, "fix")

        out = asyncio.run(run())
        assert out["success"] is True
        kinds = [et for et, _ in calls]
        assert "devbounty:claimed" in kinds
        assert "devbounty:pr_created" in kinds
        assert "devbounty:merged_paid" in kinds


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp

    async def post(self, url, **kwargs):
        return self._resp

    async def get(self, url, **kwargs):
        return self._resp


class TestTradingKillswitchEmits:
    def test_activate_deactivate_emit(self, monkeypatch) -> None:
        from cores.trading.risk import KillSwitchLevel, KillSwitchManager

        calls = _recorder(monkeypatch)
        mgr = KillSwitchManager()
        mgr.activate(KillSwitchLevel.STRATEGY, reason="test", affected=["s1"])
        mgr.deactivate(KillSwitchLevel.STRATEGY, affected=["s1"], triggered_by="human")
        kinds = [et for et, _ in calls]
        assert "trading:killswitch_on" in kinds
        assert "trading:killswitch_off" in kinds


class TestFindingReportEmits:
    def test_persist_confirmed_emits(self, monkeypatch) -> None:
        from cores.cycles.stages.validation_executor import ValidationExecutor

        # Other suites drop tables from the shared test DB; this one must not
        # depend on `targets` already existing (it failed with
        # "no such table: targets" in a full-suite run). The rows are removed
        # afterwards so a suite that asserts an EMPTY db (e.g.
        # test_command_center) still sees it empty.
        from database.db import Base, engine
        from database.models import Finding, Target

        Base.metadata.create_all(bind=engine, tables=[Target.__table__, Finding.__table__])

        calls = _recorder(monkeypatch)
        ex = ValidationExecutor()
        try:
            ex._persist_findings(
                "example.com", [{"status": "confirmed", "vulnerability_type": "idor", "confidence": 0.8}]
            )
            assert any(et == "finding:confirmed" for et, _ in calls)
        finally:
            _clear_table(Finding)
            _clear_table(Target)

    def test_report_save_emits(self, monkeypatch, tmp_path) -> None:
        from cores.reporting import generate_and_save_report

        calls = _recorder(monkeypatch)
        out = generate_and_save_report(
            finding_id=1,
            finding_title="IDOR t",
            severity="high",
            target_name="t",
            endpoint_path="/x",
            method="GET",
            vulnerability_type="idor",
            description="d",
            confidence=0.9,
            poc_curl="curl",
            poc_python="py",
            output_path=str(tmp_path / "r.md"),
        )
        assert out
        assert any(et == "report:generated" for et, _ in calls)


class TestSchedulerAndPayoutEmits:
    def test_job_failed_helper_emits(self, monkeypatch) -> None:
        from api import lifespan as ls

        calls = _recorder(monkeypatch)
        ls._emit_job_failed("job_x", RuntimeError("boom"))
        assert calls and calls[0][0] == "scheduler:job_failed"
        assert "job_x" in calls[0][1].get("message", "")

    def test_record_payout_emits(self, monkeypatch) -> None:
        from cores.revenue.ledger import RevenueLedger, RevenueLedgerEntry
        from database.db import Base, engine

        Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])
        Base.metadata.create_all(bind=engine, tables=[RevenueLedgerEntry.__table__])
        try:
            ledger = RevenueLedger()
            ledger.create(
                entry_id="pay-1",
                mission_id="m",
                opportunity_id="o",
                platform="algora",
                gross_usd=200.0,
                payment_method="crypto",
                external_id="x",
            )
            for state in (
                "committed",
                "in_progress",
                "delivered",
                "submitted",
                "accepted",
                "awarded",
                "pending_payout",
            ):
                ledger.transition("pay-1", state)
            calls = _recorder(monkeypatch)
            entry = ledger.record_payout("pay-1", 200.0, "crypto", "x")
            assert entry is not None
            assert any(et == "revenue:payout_recorded" for et, _ in calls)
        finally:
            Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])


class TestPendingConfigAndForwarder:
    def test_pending_config_shape(self) -> None:
        r = client.get("/api/notifications/pending-config")
        assert r.status_code == 200
        body = r.json()["data"]
        assert {"complete_pct", "pending_count", "pending"} <= set(body)
        assert isinstance(body["pending"], list)
        by_id = {i["id"]: i for i in body["pending"]}
        assert "github_token" in by_id  # sin token en este env: pendiente
        gh = by_id["github_token"]
        assert "opportunity.env" in gh["how_to"]  # doc fix pineado
        assert {"id", "title", "why", "est_minutes", "how_to", "url", "phase"} <= set(gh)

    def test_ws_forwarder_registers(self) -> None:
        from cores.notifications.bridges import register_ws_forwarder
        from cores.notifications.hub import get_hub

        before = len(get_hub()._listeners)
        register_ws_forwarder()
        assert len(get_hub()._listeners) == before + 1
