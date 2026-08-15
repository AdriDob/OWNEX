"""Tests for scheduler job definitions — all 5 cycles (Security, Forge, Pulse, Vault, Atlas)."""

from __future__ import annotations

from core.interfaces.scheduler import JobDefinition
from core.scheduler.jobs import (
    get_all_jobs,
    get_atlas_jobs,
    get_forge_jobs,
    get_pulse_jobs,
    get_security_jobs,
    get_trading_jobs,
    get_vault_jobs,
)


def _check_job_structure(job: JobDefinition) -> None:
    """Verify a job has all required fields."""
    assert isinstance(job.job_id, str)
    assert len(job.job_id) > 0
    assert isinstance(job.app_id, str)
    assert len(job.app_id) > 0
    assert isinstance(job.handler, str)
    assert len(job.handler) > 0
    assert job.trigger in ("interval", "cron")
    if job.trigger == "interval":
        assert isinstance(job.seconds, int)
        assert job.seconds > 0


class TestForgeJobs:
    def test_returns_list(self):
        jobs = get_forge_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_forge_jobs():
            _check_job_structure(job)

    def test_all_have_forge_app_id(self):
        for job in get_forge_jobs():
            assert job.app_id == "forge"

    def test_has_opencollective_discovery(self):
        ids = [j.job_id for j in get_forge_jobs()]
        assert "forge_opencollective_discover" in ids

    def test_has_sync_scores_job(self):
        ids = [j.job_id for j in get_forge_jobs()]
        assert "forge_sync_scores" in ids

    def test_has_cycle_metadata(self):
        for job in get_forge_jobs():
            assert job.metadata.get("cycle") == "forge"

    def test_cron_jobs_have_cron_kwarg(self):
        for job in get_forge_jobs():
            if job.trigger == "cron":
                assert "cron" in job.kwargs.get("kwargs", job.kwargs)


class TestPulseJobs:
    def test_returns_list(self):
        jobs = get_pulse_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_pulse_jobs():
            _check_job_structure(job)

    def test_all_have_pulse_app_id(self):
        for job in get_pulse_jobs():
            assert job.app_id == "pulse"

    def test_has_mindrift_fast_job(self):
        ids = [j.job_id for j in get_pulse_jobs()]
        assert "pulse_mindrift_fast" in ids

    def test_has_sync_scores_job(self):
        ids = [j.job_id for j in get_pulse_jobs()]
        assert "pulse_sync_scores" in ids

    def test_has_orchestrator(self):
        ids = [j.job_id for j in get_pulse_jobs()]
        assert "pulse_execute_orchestrator" in ids

    def test_staggered_platforms_have_different_cron(self):
        jobs = get_pulse_jobs()
        crons = []
        for job in jobs:
            if "discover" in job.job_id:
                kws = job.kwargs.get("kwargs", job.kwargs)
                crons.append(kws.get("cron"))
        crons = [c for c in crons if c is not None]
        assert len(set(crons)) > 1


class TestVaultJobs:
    def test_returns_list(self):
        jobs = get_vault_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_vault_jobs():
            _check_job_structure(job)

    def test_all_have_vault_app_id(self):
        for job in get_vault_jobs():
            assert job.app_id == "vault"

    def test_has_backup_job(self):
        ids = [j.job_id for j in get_vault_jobs()]
        assert "vault_backup_2h" in ids

    def test_has_health_job(self):
        ids = [j.job_id for j in get_vault_jobs()]
        assert "vault_health_4h" in ids

    def test_backup_handler(self):
        for job in get_vault_jobs():
            if job.job_id == "vault_backup_2h":
                handler_str = str(job.handler)
                assert "backup_vault" in handler_str

    def test_health_handler(self):
        for job in get_vault_jobs():
            if job.job_id == "vault_health_4h":
                handler_str = str(job.handler)
                assert "check_secrets_health" in handler_str


class TestAtlasJobs:
    def test_returns_list(self):
        jobs = get_atlas_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_atlas_jobs():
            _check_job_structure(job)

    def test_all_have_atlas_app_id(self):
        for job in get_atlas_jobs():
            assert job.app_id == "atlas"

    def test_has_health_job(self):
        ids = [j.job_id for j in get_atlas_jobs()]
        assert "atlas_health_5min" in ids

    def test_has_intel_job(self):
        ids = [j.job_id for j in get_atlas_jobs()]
        assert "atlas_intel_30min" in ids


class TestSecurityJobs:
    def test_returns_list(self):
        jobs = get_security_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_security_jobs():
            _check_job_structure(job)

    def test_all_have_security_app_id(self):
        for job in get_security_jobs():
            assert job.app_id == "security"

    def test_has_cycle_start_job(self):
        ids = [j.job_id for j in get_security_jobs()]
        assert "security_cycle_start" in ids

    def test_has_advance_job(self):
        ids = [j.job_id for j in get_security_jobs()]
        assert "security_cycle_advance" in ids

    def test_has_sync_job(self):
        ids = [j.job_id for j in get_security_jobs()]
        assert "security_cycle_sync" in ids


class TestTradingJobs:
    def test_returns_list(self):
        jobs = get_trading_jobs()
        assert isinstance(jobs, list)

    def test_all_have_valid_structure(self):
        for job in get_trading_jobs():
            _check_job_structure(job)

    def test_all_have_trading_app_id(self):
        for job in get_trading_jobs():
            assert job.app_id == "trading"

    def test_has_risk_check_job(self):
        ids = [j.job_id for j in get_trading_jobs()]
        assert "trading_risk_check" in ids

    def test_has_dna_update_job(self):
        ids = [j.job_id for j in get_trading_jobs()]
        assert "trading_dna_update" in ids

    def test_has_discovery_job(self):
        ids = [j.job_id for j in get_trading_jobs()]
        assert "trading_discovery" in ids

    def test_has_cycle_metadata(self):
        for job in get_trading_jobs():
            assert job.metadata.get("cycle") == "trading"

    def test_risk_check_handler_resolves(self):
        for job in get_trading_jobs():
            if job.job_id == "trading_risk_check":
                assert job.handler == "core.trading.copy_trading:run_trading_risk_check"


class TestGetAllJobs:
    def test_returns_dict_with_twelve_cycles(self):
        all_jobs = get_all_jobs()
        assert set(all_jobs.keys()) == {
            "security",
            "forge",
            "pulse",
            "vault",
            "atlas",
            "direct_work",
            "investment",
            "qa",
            "evolution",
            "knowledge",
            "trading",
            "integrations",
        }

    def test_all_cycles_have_lists(self):
        for _cycle, jobs in get_all_jobs().items():
            assert isinstance(jobs, list)
            assert len(jobs) > 0

    def test_total_jobs_count(self):
        total = sum(len(jobs) for jobs in get_all_jobs().values())
        assert (
            total == 48
        )  # 12 cycles: security(10) + forge(9) + pulse(10) + vault(2) + atlas(2) + direct_work(5) + investment(3) + qa(1) + evolution(1) + knowledge(1) + trading(3) + integrations(1)

    def test_all_jobs_have_unique_ids(self):
        all_ids = []
        for jobs in get_all_jobs().values():
            for job in jobs:
                all_ids.append(job.job_id)
        assert len(all_ids) == len(set(all_ids))

    def test_all_jobs_have_valid_structure(self):
        for jobs in get_all_jobs().values():
            for job in jobs:
                _check_job_structure(job)


class TestDeliveryPreparationJob:
    def test_delivery_preparation_job_registered(self):
        from core.scheduler.jobs import get_all_jobs

        all_jobs = get_all_jobs()
        direct_work_jobs = all_jobs.get("direct_work", [])
        job_ids = [j.job_id for j in direct_work_jobs]
        assert "daily_delivery_preparation" in job_ids

    def test_delivery_preparation_handler_callable(self):
        from core.cycles.tasks import run_daily_delivery_preparation
        from core.scheduler.jobs import get_all_jobs

        all_jobs = get_all_jobs()
        direct_work_jobs = all_jobs.get("direct_work", [])
        job = next(j for j in direct_work_jobs if j.job_id == "daily_delivery_preparation")
        assert job.handler == "core.cycles.tasks:run_daily_delivery_preparation"
        assert callable(run_daily_delivery_preparation)

    def test_run_daily_delivery_preparation(self, monkeypatch):
        from core.cycles.tasks import run_daily_delivery_preparation

        monkeypatch.setattr(
            "cores.direct_work_engine.workbank.get_workbank",
            lambda: _FakeWorkBank(),
            raising=True,
        )
        result = run_daily_delivery_preparation()
        assert result["status"] == "ok"
        assert "prepared_count" in result


class _FakeWorkBank:
    def best_ready(self, limit: int = 200):
        return []


class TestIntegrationJobs:
    def test_outlook_sync_job_registered(self):
        from core.scheduler.jobs import get_integration_jobs

        ids = [j.job_id for j in get_integration_jobs()]
        assert "outlook_calendar_sync" in ids

    def test_outlook_sync_job_config(self):
        from core.scheduler.jobs import get_integration_jobs

        job = next(j for j in get_integration_jobs() if j.job_id == "outlook_calendar_sync")
        kws = job.kwargs.get("kwargs", job.kwargs)
        assert job.handler == "cores.integrations.outlook.sync:run_calendar_sync"
        assert kws.get("cron") == "*/15 * * * *"

    def test_outlook_sync_handler_callable(self):
        import inspect

        from cores.integrations.outlook.sync import run_calendar_sync

        assert callable(run_calendar_sync)
        assert inspect.iscoroutinefunction(run_calendar_sync)
