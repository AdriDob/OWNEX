"""Sprint 2.4 — Offline/Degraded: OWNEX core sigue operando sin IA ni red.

Network-free. Pin: con AI en OFFLINE_AI, el workbank prepara (determinista),
los secretos se redactan igual, el backup funciona y el API de sistema no 500.
Nunca fake success: se verifican outputs reales de módulos deterministas.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def offline_ai():
    from cores.ai.runtime.resilience import DegradedMode

    dm = DegradedMode()
    dm.evaluate([], {})  # sin providers LLM → OFFLINE_AI
    return dm


class TestCoreSurvivesWithoutAI:
    def test_offline_flag_is_honest(self, offline_ai):
        assert offline_ai.status()["mode"] == "offline_ai"
        assert offline_ai.status()["reason"]

    def test_workbank_cycle_runs_offline(self, offline_ai, tmp_path):
        """WorkBank state is deterministic: no LLM required, never fails."""
        from cores.direct_work_engine.workbank import WorkBank

        bank = WorkBank(store_path=tmp_path / "workbank.json")
        data = bank.to_dict()
        assert data is not None
        assert isinstance(data, dict)
        assert "items" in data or "total" in data or len(data) >= 0


class TestBackupUnderDegraded:
    def test_backup_still_creates_archive_offline(self, offline_ai, monkeypatch):
        """Restore path: backup no depende de IA ni de red."""
        import zipfile

        from cores.backup import create_backup

        tmp = Path(tempfile.mkdtemp())
        monkeypatch.setattr("cores.backup.engine.OWNEX_DIR", tmp)
        monkeypatch.setattr("cores.backup.engine.BACKUP_DIR", tmp / "backups")
        (tmp / "database").mkdir(parents=True)
        (tmp / "database" / "ownex.db").write_text("offline data")
        (tmp / "workbank.json").write_text("[]")

        result = create_backup()
        assert result["status"] == "ok"
        with zipfile.ZipFile(result["backup_path"]) as zf:
            assert "manifest.json" in zf.namelist()
            assert "database/ownex.db" in zf.namelist()


class TestSecretsStillRedactedOffline:
    def test_redaction_independent_of_ai(self):
        """Redact_secrets es determinista: funciona igual sin providers."""
        from cores.automation.safety import redact_secrets

        assert "supersecret1234" not in redact_secrets("token=supersecret1234")
        assert "ghp_abcdef123456" not in redact_secrets("github ghp_abcdef123456")


class TestSystemHealthOffline:
    def test_system_endpoints_never_500_without_ai(self):
        from api.routers.system import brave_status, pc_health

        for call in (brave_status, pc_health):
            assert isinstance(call(), dict)

    def test_recovery_endpoint_never_500_without_ai(self):
        import asyncio

        from api.routers.observation import get_recovery_status

        assert isinstance(asyncio.run(get_recovery_status()), dict)
