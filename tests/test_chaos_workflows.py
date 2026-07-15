"""Chaos tests for the Workflow Engine — edge cases, failure scenarios, resilience."""

from __future__ import annotations

from core.workflows.engine import WorkflowEngine, get_workflow_engine
from core.workflows.models import StepType, WorkflowStep


def test_engine_singleton():
    e1 = get_workflow_engine()
    e2 = get_workflow_engine()
    assert e1 is e2


def test_list_templates_empty_dir():
    engine = WorkflowEngine()
    templates = engine.list_templates()
    assert isinstance(templates, list)


def test_load_nonexistent_template():
    engine = WorkflowEngine()
    t = engine.load_template("does_not_exist.yaml")
    assert t is None


def test_create_run_bad_template():
    engine = WorkflowEngine()
    run = engine.create_run("bad_file.yaml")
    assert run is None


def test_create_run_success():
    engine = WorkflowEngine()
    run = engine.create_run("recon-full.yaml", target="example.com")
    assert run is not None
    assert run.target == "example.com"
    assert len(run.steps) > 0
    assert run.status.value == "pending"


def test_get_nonexistent_run():
    engine = WorkflowEngine()
    run = engine.get_run("NONEXISTENT")
    assert run is None


def test_execute_step_nonexistent_run():
    engine = WorkflowEngine()
    result = engine.execute_step("no_run", "step_1")
    assert result.status.value == "failed"
    assert "Run not found" in (result.error or "")


def test_execute_step_nonexistent_step():
    engine = WorkflowEngine()
    run = engine.create_run("recon-full.yaml")
    assert run is not None
    result = engine.execute_step(run.id, "no_such_step")
    assert result.status.value == "failed"
    assert "Step not found" in (result.error or "")


def test_execute_step_success():
    engine = WorkflowEngine()
    run = engine.create_run("scan-quick.yaml")
    assert run is not None
    first_step_id = run.steps[0].id
    result = engine.execute_step(run.id, first_step_id)
    assert result.status.value == "completed"
    assert result.output is not None


def test_list_runs_empty():
    engine = WorkflowEngine()
    runs = engine.list_runs()
    assert isinstance(runs, list)


def test_workflow_step_types():
    for st in StepType:
        assert st.value in ["discover", "recon", "scan", "hypothesis", "validate", "report", "notify"]


def test_workflow_step_creation():
    step = WorkflowStep(id="test", type=StepType.scan, params={"tool": "nuclei"})
    assert step.id == "test"
    assert step.type == StepType.scan
    assert step.params["tool"] == "nuclei"


def test_rapid_create_multiple_runs():
    engine = WorkflowEngine()
    count_before = len(engine.list_runs())
    for _ in range(10):
        engine.create_run("recon-full.yaml")
    assert len(engine.list_runs()) == count_before + 10


def test_create_run_with_empty_target():
    engine = WorkflowEngine()
    run = engine.create_run("report-auto.yaml", target="")
    assert run is not None
    assert run.target == ""
