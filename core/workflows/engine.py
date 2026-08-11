from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import yaml

from core.workflows.models import RunStatus, StepType, WorkflowResult, WorkflowRun, WorkflowStep, WorkflowTemplate

logger = logging.getLogger("orion.core.workflows")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


class WorkflowEngine:
    """YAML-based workflow engine.

    Loads templates from core/workflows/templates/*.yaml,
    resolves variable references, executes steps sequentially.
    """

    def __init__(self) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._lock = Lock()

    def list_templates(self) -> list[dict[str, Any]]:
        """Return available workflow templates."""
        templates = []
        if not os.path.isdir(TEMPLATES_DIR):
            return templates
        for fname in sorted(os.listdir(TEMPLATES_DIR)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(TEMPLATES_DIR, fname)
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue
                templates.append(
                    {
                        "file": fname,
                        "name": data.get("name", fname),
                        "description": data.get("description", ""),
                        "steps": [{"id": s.get("id"), "type": s.get("type")} for s in (data.get("steps") or [])],
                    }
                )
            except Exception as e:
                logger.warning("Failed to load template %s: %s", fname, e)
        return templates

    def load_template(self, file: str) -> WorkflowTemplate | None:
        """Load a specific template by filename."""
        path = os.path.join(TEMPLATES_DIR, file)
        if not os.path.isfile(path):
            return None
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            if not data:
                return None
            steps = [
                WorkflowStep(id=s["id"], type=StepType(s["type"]), params=s.get("params", {}))
                for s in (data.get("steps") or [])
            ]
            return WorkflowTemplate(
                name=data.get("name", file),
                description=data.get("description", ""),
                steps=steps,
            )
        except Exception as e:
            logger.error("Error loading template %s: %s", file, e)
            return None

    def create_run(self, template_file: str, target: str = "") -> WorkflowRun | None:
        """Create a new workflow run from a template."""
        template = self.load_template(template_file)
        if not template:
            return None
        run = WorkflowRun(
            template_name=template.name,
            target=target,
            steps=template.steps,
            status=RunStatus.pending,
        )
        with self._lock:
            self._runs[run.id] = run
        logger.info("Workflow %s created: %s (target=%s)", run.id, template.name, target)
        return run

    def execute_step(self, run_id: str, step_id: str) -> WorkflowResult:
        """Execute a single workflow step by dispatching to the appropriate app engine."""
        run = self._runs.get(run_id)
        if not run:
            return WorkflowResult(step_id=step_id, status=RunStatus.failed, error="Run not found")
        step = next((s for s in run.steps if s.id == step_id), None)
        if not step:
            return WorkflowResult(step_id=step_id, status=RunStatus.failed, error="Step not found")

        logger.info("Executing step %s/%s (type=%s)", run_id, step_id, step.type.value)
        with self._lock:
            run.status = RunStatus.running

        try:
            output = self._dispatch_step(step)
            result = WorkflowResult(
                step_id=step_id,
                status=RunStatus.completed,
                output=output,
            )
        except Exception as exc:
            logger.warning("Step %s/%s failed: %s", run_id, step_id, exc)
            result = WorkflowResult(
                step_id=step_id,
                status=RunStatus.failed,
                error=str(exc),
            )

        with self._lock:
            run.results.append(result)
            run.status = result.status
            run.updated_at = datetime.now(UTC)
        return result

    def _dispatch_step(self, step: WorkflowStep) -> dict[str, Any]:
        """Dispatch a step to the appropriate executor based on type."""
        import importlib

        executors = {
            StepType.discover: ("apps.aegis.scheduler", "check_active_targets"),
            StepType.recon: ("apps.aegis.engines.recon", "run_recon"),
            StepType.scan: ("apps.aegis.engines.scanner", "run_scan"),
            StepType.report: ("api.scheduler", "generate_report"),
        }
        executor = executors.get(step.type)
        if not executor:
            return {"message": f"Step type '{step.type.value}' has no executor (reserved for future use)"}
        mod_path, func_name = executor
        try:
            mod = importlib.import_module(mod_path)
            fn = getattr(mod, func_name, None)
            if fn is None:
                return {"message": f"Executor {func_name} not found in {mod_path}"}
            target = step.params.get("target", "")
            if callable(fn):
                result = fn(target) if target else fn()
                return {"result": str(result)[:200], "executor": func_name}
            return {"message": f"Executor {func_name} is not callable"}
        except Exception as exc:
            logger.warning("Dispatch to %s.%s failed: %s", mod_path, func_name, exc)
            raise

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._runs.values()]


_engine: WorkflowEngine | None = None


def get_workflow_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
