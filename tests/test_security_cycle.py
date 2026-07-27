from core.cycles.models import CycleStatus, Task
from core.cycles.security import SecurityCycle
from core.cycles.service import get_cycle_service
from core.database.manager import get_db_manager


class TestSecurityCycle:
    def test_get_security_cycle(self):
        cycle = SecurityCycle()
        assert cycle is not None

    def test_ensure_cycle(self):
        sc = SecurityCycle()
        cycle = sc.ensure_cycle()
        assert cycle.slug == "security"
        assert cycle.category == "security"

    def test_start_cycle(self):
        sc = SecurityCycle()
        svc = get_cycle_service()
        existing = svc.get_by_slug("security")
        if existing and existing.status == CycleStatus.RUNNING.value:
            svc.update(existing.id, {"status": CycleStatus.IDLE.value})

        cycle = sc.start_cycle()
        assert cycle.status == CycleStatus.RUNNING.value
        mgr = get_db_manager()
        db = mgr.get_session("cycles")
        tasks = db.query(Task).filter(Task.cycle_id == cycle.id).all()
        assert len(tasks) >= 7
        task_names = [t.name for t in tasks]
        assert "Recon" in task_names
        assert "Validation" in task_names
        assert "Report" in task_names

    def test_stage_estimates(self):
        sc = SecurityCycle()
        assert sc._estimate_hours("recon") == 1.0
        assert sc._estimate_hours("validation") == 4.0
        assert sc._estimate_hours("report") == 2.0
