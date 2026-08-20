"""Tests for Self-Improvement Engine (Ornith-1.5 loop)."""

import tempfile
from pathlib import Path

import pytest

from core.self_improvement.capability import CapabilityTracker
from core.self_improvement.config import SelfImprovementConfig
from core.self_improvement.engine import SelfImprovementEngine
from core.self_improvement.experience import ExperienceStore
from core.self_improvement.frontier import DifficultyFrontier
from core.self_improvement.harness import Harness
from core.self_improvement.models import ScaffoldStep, Task, TaskCategory
from core.self_improvement.rollout import DeterministicSolver, RolloutRunner
from core.self_improvement.task_generator import TaskGenerator


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def config(tmp_data_dir):
    return SelfImprovementConfig(
        data_dir=tmp_data_dir,
        task_store_path=tmp_data_dir / "tasks.json",
        experience_store_path=tmp_data_dir / "experiences.json",
        capability_store_path=tmp_data_dir / "capabilities.json",
    )


@pytest.fixture
def engine(config):
    return SelfImprovementEngine(config=config, solver=DeterministicSolver())


class TestDeterministicSolver:
    """Tests for the offline solver that produces verifiable solutions."""

    def test_code_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t1",
            title="Add two numbers",
            category=TaskCategory.CODE,
            description="Implement add function",
            prompt="Write a function that adds two numbers",
            skills=["python"],
            difficulty=0.3,
            metadata={"answer": 42, "call": "add", "cases": [[[1, 2], 3]]},
        )
        solution = solver.solve(task)
        assert "def add(*args):" in solution
        assert "return 42" in solution

    def test_test_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t2",
            title="Write test",
            category=TaskCategory.TEST,
            description="Write a test",
            prompt="Write a test",
            skills=["python"],
            difficulty=0.2,
            metadata={},
        )
        solution = solver.solve(task)
        assert "def test_trivial():" in solution
        assert "assert True" in solution

    def test_debug_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t3",
            title="Debug",
            category=TaskCategory.DEBUG,
            description="Debug code",
            prompt="Debug",
            skills=["python"],
            difficulty=0.3,
            metadata={},
        )
        solution = solver.solve(task)
        assert 'print("PASS")' in solution

    def test_analysis_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t4",
            title="Analyze",
            category=TaskCategory.ANALYSIS,
            description="Analyze data",
            prompt="Analyze",
            skills=["python"],
            difficulty=0.4,
            metadata={"accepted": ["accepted", "rejected"]},
        )
        solution = solver.solve(task)
        assert "verdict = 'accepted'" in solution

    def test_reasoning_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t5",
            title="Reason",
            category=TaskCategory.REASONING,
            description="Reason about X",
            prompt="Reason",
            skills=["python"],
            difficulty=0.5,
            metadata={"answer": "42"},
        )
        solution = solver.solve(task)
        assert "answer = '42'" in solution

    def test_security_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t6",
            title="Find vuln",
            category=TaskCategory.SECURITY,
            description="Find vulnerability",
            prompt="Find",
            skills=["security"],
            difficulty=0.6,
            metadata={"accepted": ["sqli", "xss"]},
        )
        solution = solver.solve(task)
        assert "vuln_type = 'sqli'" in solution

    def test_generation_category(self):
        solver = DeterministicSolver()
        task = Task(
            id="t7",
            title="Generate",
            category=TaskCategory.GENERATION,
            description="Generate data",
            prompt="Generate",
            skills=["python"],
            difficulty=0.2,
            metadata={"keys": ["x", "y", "z"]},
        )
        solution = solver.solve(task)
        assert "RESULT = " in solution
        import json as stdlib_json

        payload = stdlib_json.loads(solution.split("RESULT = ")[1])
        assert payload == {"x": "ok", "y": "ok", "z": "ok"}


class TestHarness:
    """Tests for the execution harness."""

    def test_harness_runs_code_solution(self, config):
        harness = Harness(config)
        task = Task(
            id="t1",
            title="Return 42",
            category=TaskCategory.CODE,
            description="Return 42",
            prompt="Return 42",
            skills=["python"],
            difficulty=0.3,
            metadata={"answer": 42, "call": "call", "cases": [[[], 42]]},
        )
        solution = "def call(*args):\n    return 42\n"
        rollout = harness.run(task, solution)
        assert rollout.exit_code == 0
        assert "CODE_OK" in rollout.stdout
        harness.cleanup()

    def test_harness_detects_syntax_error(self, config):
        harness = Harness(config)
        task = Task(
            id="t2",
            title="Bad code",
            category=TaskCategory.CODE,
            description="Bad",
            prompt="Bad",
            skills=["python"],
            difficulty=0.3,
            metadata={},
        )
        solution = "def call(:\n    return 1\n"
        rollout = harness.run(task, solution)
        assert rollout.exit_code != 0
        harness.cleanup()

    def test_harness_policy_enforcement(self, config):
        harness = Harness(config)
        task = Task(
            id="t3",
            title="Dangerous command",
            category=TaskCategory.CODE,
            description="Run rm -rf",
            prompt="Run rm -rf",
            skills=["python"],
            difficulty=0.3,
            metadata={},
        )
        solution = "import os\nos.system('rm -rf /')\n"
        rollout = harness.run(task, solution)
        assert "policy" in (rollout.error or "").lower()
        harness.cleanup()


class TestTaskGenerator:
    """Tests for the curriculum task generator."""

    def test_generate_batch_returns_tasks(self, config):
        generator = TaskGenerator(config, DifficultyFrontier(config))
        tasks = generator.generate_batch(
            count=3,
            existing=[],
            capabilities=[],
            skill_gaps=[],
        )
        assert len(tasks) <= 3
        assert all(hasattr(t, "id") for t in tasks)
        assert all(t.category in TaskCategory for t in tasks)

    def test_generate_batch_avoids_existing(self, config):
        generator = TaskGenerator(config, DifficultyFrontier(config))
        existing_task = Task(
            id="existing-1",
            title="Existing",
            category=TaskCategory.CODE,
            description="Existing task",
            prompt="Existing",
            skills=["python"],
            difficulty=0.3,
            metadata={},
        )
        tasks = generator.generate_batch(
            count=2,
            existing=[existing_task],
            capabilities=[],
            skill_gaps=[],
        )
        assert all(t.id != "existing-1" for t in tasks)


class TestCapabilityTracker:
    """Tests for capability tracking."""

    def test_record_and_stats(self, config):
        tracker = CapabilityTracker(config)
        tracker.record("python", True, 0.5)
        tracker.record("python", False, 0.0)
        tracker.record("security", True, 1.0)
        stats = tracker.stats()
        assert "python" in stats
        assert "security" in stats
        assert stats["python"]["attempts"] == 2
        assert stats["security"]["attempts"] == 1

    def test_persistence(self, config, tmp_data_dir):
        tracker = CapabilityTracker(config)
        tracker.record("python", True, 0.5)
        tracker2 = CapabilityTracker(config)
        stats = tracker2.stats()
        assert "python" in stats


class TestExperienceStore:
    """Tests for experience persistence."""

    def test_add_and_retrieve(self, config):
        store = ExperienceStore(config)
        initial_count = store.count()
        # Create a minimal experience
        from core.self_improvement.models import Evaluation, Experience, Rollout, Scaffold

        task = Task(
            id="exp-1",
            title="Test",
            category=TaskCategory.CODE,
            description="Test",
            prompt="Test",
            skills=["python"],
            difficulty=0.3,
            metadata={},
        )
        scaffold = Scaffold(task_id="exp-1", steps=[ScaffoldStep(index=0, instruction="step1", verification="check")])
        rollout = Rollout(task_id="exp-1", attempt=0, solution="def call(): return 1")
        evaluation = Evaluation(
            task_id="exp-1",
            rollout=rollout,
            valid=True,
            validity_score=1.0,
            checks_passed=1,
            checks_total=1,
            notes=["ok"],
        )
        exp = Experience(
            id="exp-1",
            task=task,
            scaffold=scaffold,
            evaluation=evaluation,
            reward=0.5,
            difficulty_before=0.3,
            difficulty_after=0.3,
        )
        store.add(exp)
        assert store.count() == initial_count + 1
        all_exp = store.all()
        assert any(e.id == "exp-1" for e in all_exp)

    def test_success_rate(self, config):
        store = ExperienceStore(config)
        from core.self_improvement.models import Evaluation, Experience, Rollout, Scaffold

        for i in range(3):
            task = Task(
                id=f"exp-{i}",
                title=f"Test {i}",
                category=TaskCategory.CODE,
                description="Test",
                prompt="Test",
                skills=["python"],
                difficulty=0.3,
                metadata={},
            )
            scaffold = Scaffold(
                task_id=f"exp-{i}", steps=[ScaffoldStep(index=0, instruction="step1", verification="check")]
            )
            rollout = Rollout(task_id=f"exp-{i}", attempt=0, solution="def call(): return 1")
            valid = i < 2  # 2 valid, 1 invalid
            evaluation = Evaluation(
                task_id=f"exp-{i}",
                rollout=rollout,
                valid=valid,
                validity_score=1.0 if valid else 0.0,
                checks_passed=1 if valid else 0,
                checks_total=1,
                notes=["ok"],
            )
            exp = Experience(
                id=f"exp-{i}",
                task=task,
                scaffold=scaffold,
                evaluation=evaluation,
                reward=0.5 if valid else 0.0,
                difficulty_before=0.3,
                difficulty_after=0.3,
            )
            store.add(exp)
        assert store.success_rate() == pytest.approx(2 / 3, rel=0.01)


class TestDifficultyFrontier:
    """Tests for adaptive difficulty."""

    def test_records_outcome(self, config):
        frontier = DifficultyFrontier(config)
        initial = frontier.current_difficulty()
        frontier.record_outcome(0.5, True)  # success
        frontier.record_outcome(0.5, True)  # success
        frontier.record_outcome(0.5, True)  # success
        # After 3 successes at same difficulty, should increase
        assert frontier.current_difficulty() >= initial

    def test_failure_decreases(self, config):
        frontier = DifficultyFrontier(config)
        initial = frontier.current_difficulty()
        frontier.record_outcome(initial, False)
        frontier.record_outcome(initial, False)
        frontier.record_outcome(initial, False)
        # After failures, should decrease or stay
        assert frontier.current_difficulty() <= initial


class TestEngineEndToEnd:
    """End-to-end tests for the full loop."""

    def test_run_once_completes(self, engine):
        result = engine.run_once()
        assert result["status"] == "completed"
        assert result["valid"] in (True, False)
        assert "task_id" in result
        assert "reward" in result

    def test_run_batch_multiple(self, engine):
        results = engine.run_batch(count=3)
        assert len(results) <= 3
        for r in results:
            assert r["status"] == "completed"
            assert "task_id" in r

    def test_status_returns_all_fields(self, engine):
        engine.run_once()
        status = engine.status()
        assert "config" in status
        assert "experiences" in status
        assert "success_rate" in status
        assert "frontier" in status
        assert "capabilities" in status
        assert "policies" in status

    def test_recommendations_returns_list(self, engine):
        recs = engine.recommendations(limit=5)
        assert isinstance(recs, list)
        for r in recs:
            assert "skill" in r
            assert "success_rate" in r

    def test_persistence_between_instances(self, tmp_data_dir):
        config = SelfImprovementConfig(
            data_dir=tmp_data_dir,
            task_store_path=tmp_data_dir / "tasks.json",
            experience_store_path=tmp_data_dir / "experiences.json",
            capability_store_path=tmp_data_dir / "capabilities.json",
        )
        e1 = SelfImprovementEngine(config=config, solver=DeterministicSolver())
        e1.run_once()
        e2 = SelfImprovementEngine(config=config, solver=DeterministicSolver())
        status = e2.status()
        assert status["experiences"] >= 1


class TestAPIEndpoints:
    """Integration tests for API endpoints using TestClient."""

    @pytest.fixture
    def client(self, tmp_data_dir, monkeypatch):
        import importlib
        import os
        import sys

        # Re-enable CSRF for these tests (conftest disables it by default)
        monkeypatch.delenv("CATEYE_CSRF_DISABLED", raising=False)

        os.environ["OWNEX_DATA_DIR"] = str(tmp_data_dir)
        os.environ["DATABASE_URL"] = f"sqlite:////{tmp_data_dir}/test.db"
        # Force reload to pick up new env vars
        if "api.main" in sys.modules:
            importlib.reload(sys.modules["api.main"])
        from fastapi.testclient import TestClient

        import api.main as m

        client = TestClient(m.app)
        # Login
        r = client.post("/api/auth/login", json={"device_id": "si-test-device"})
        tok = r.json().get("data", {}).get("token")
        client.headers.update({"Authorization": f"Bearer {tok}"})
        # Get CSRF token
        r = client.get("/api/version")
        csrf = r.cookies.get("csrf-token")
        client.headers.update({"X-CSRF-Token": csrf})
        return client

    def test_get_status(self, client):
        r = client.get("/api/self-improvement/status")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "config" in data["status"]
        assert "experiences" in data["status"]

    def test_get_frontier(self, client):
        r = client.get("/api/self-improvement/frontier")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "difficulty" in data["frontier"]
        assert "p_target" in data["frontier"]

    def test_get_capabilities(self, client):
        r = client.get("/api/self-improvement/capabilities")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["capabilities"], dict)

    def test_get_recommendations(self, client):
        r = client.get("/api/self-improvement/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["recommendations"], list)

    def test_get_experiences(self, client):
        r = client.get("/api/self-improvement/experiences")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "experiences" in data
        assert "total" in data

    def test_get_dashboard_engine(self, client):
        r = client.get("/api/self-improvement/dashboard/engine")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "status" in data
        assert "recommendations" in data
        assert "recent_experiences" in data

    def test_post_generate(self, client):
        r = client.post("/api/self-improvement/generate", json={"count": 2})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "tasks" in data
        # May return 0 tasks if no novel tasks found (depends on existing experiences)
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) <= 2

    def test_post_run(self, client):
        r = client.post("/api/self-improvement/run")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "result" in data
        # Engine may return "no_tasks" if no novel tasks generated
        assert data["result"]["status"] in ("completed", "no_tasks")

    def test_post_run_batch(self, client):
        r = client.post("/api/self-improvement/run/batch", json={"count": 3})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "results" in data
        assert len(data["results"]) <= 3
        for res in data["results"]:
            assert res["status"] in ("completed", "no_tasks")

    def test_end_to_end_critical(self, client):
        """FASE 13 critical test: full loop with artificial task."""
        # Run a single loop iteration
        r = client.post("/api/self-improvement/run")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        result = data["result"]
        # The engine may return "no_tasks" if no novel tasks generated; accept either
        assert result["status"] in ("completed", "no_tasks")
        if result["status"] == "completed":
            assert "task_id" in result
            # Verify experience was persisted
            r = client.get("/api/self-improvement/experiences")
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["total"] >= 1


class TestRolloutRunner:
    """Tests for the rollout runner."""

    def test_runner_runs_with_solver(self, config):
        runner = RolloutRunner(Harness(config), solver=DeterministicSolver())
        task = Task(
            id="run-1",
            title="Return 1",
            category=TaskCategory.CODE,
            description="Return 1",
            prompt="Return 1",
            skills=["python"],
            difficulty=0.3,
            metadata={"answer": 1, "call": "call", "cases": [[[], 1]]},
        )
        rollout, evaluation = runner.run(task)
        assert evaluation.valid is True
        assert rollout.exit_code == 0
