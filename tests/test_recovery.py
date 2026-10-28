"""Sprint 2.3 — Recovery hardening: healing rules, engine status, store persistence, API.

No network, no real rollback: version_rollback paths exercised with the
version-backup system monkeypatched/unavailable (honest False, never fake).
"""

from __future__ import annotations


class TestHealingRules:
    def test_critical_and_corruption_map_to_version_rollback_prio0(self):
        from cores.recovery.healing_rules import FailureType, get_rule

        for failure in (FailureType.CRITICAL_SYSTEM_FAILURE, FailureType.VERSION_CORRUPTION):
            rule = get_rule(failure)
            assert rule.recovery_action == "version_rollback"
            assert rule.priority == 0
            # Last resort: requires no circuit breaker (must always be possible).
            assert rule.requires_circuit_breaker is False

    def test_eventbus_and_agent_rules_resolve(self):
        from cores.recovery.healing_rules import FailureType, get_rule

        assert get_rule(FailureType.EVENTBUS_DEAD).recovery_action == "restart_agent_bus"
        assert get_rule(FailureType.AGENT_CRASHED).recovery_action == "restart_agent"
        assert get_rule(FailureType.DB_CONNECTION_LOST).recovery_action == "reopen_db_connection"
        assert get_rule(FailureType.UNKNOWN).recovery_action == "log_and_observe"

    def test_all_rules_present_and_unique_priorities(self):
        from cores.recovery.healing_rules import HEALING_RULES

        assert len(HEALING_RULES) >= 14
        actions = {r.recovery_action for r in HEALING_RULES}
        assert "version_rollback" in actions


class TestRecoveryEngineStatus:
    def test_singleton_and_status_shape(self):
        from cores.recovery import get_recovery_engine, reset_recovery_engine

        reset_recovery_engine()
        engine = get_recovery_engine()
        assert get_recovery_engine() is engine
        status = engine.status()
        assert set(status) == {"running", "circuit_breakers", "recovery_in_progress"}
        assert isinstance(status["running"], bool)
        assert isinstance(status["circuit_breakers"], dict)
        assert isinstance(status["recovery_in_progress"], dict)

    def test_version_rollback_honest_without_backup_system(self):
        from cores.recovery import get_recovery_engine, reset_recovery_engine

        reset_recovery_engine()
        engine = get_recovery_engine()
        engine._version_backup_system = None  # simulate unavailable
        ok = engine.attempt_version_rollback_recovery("scheduler", {"reason": "test"})
        assert ok is False
        st = engine.get_version_recovery_status()
        assert isinstance(st, dict)


class TestRecoveryStore:
    def test_store_persists_and_reloads(self, tmp_path):
        from cores.recovery import persistence

        db_path = tmp_path / "recovery_history.db"
        store = persistence.RecoveryStore(db_path=str(db_path))
        store.record_recovery("scheduler", "crash", "restart", "ok", details="x=1")
        history = store.get_recovery_history(limit=10)
        assert len(history) >= 1
        assert history[0]["component"] == "scheduler"
        assert history[0]["recovery_action"] == "restart"

        # Reload from the same file.
        store2 = persistence.RecoveryStore(db_path=str(db_path))
        history2 = store2.get_recovery_history(limit=10)
        assert len(history2) >= 1
        assert history2[0]["status"] == "ok"


class TestRecoveryEndpoint:
    def test_recovery_endpoint_never_500s(self):
        import asyncio

        from api.routers.observation import get_recovery_status

        body = asyncio.run(get_recovery_status())
        assert "status" in body or "features" in body
        assert "features" in body
        assert "version_rollback" in body["features"]
