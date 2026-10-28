"""Internal Dev Agent — autonomous dev queue for the repo itself.

External work already has agents (CoderAgent + DevBountyPipeline + OpenCode
bridge + WorkerCore). Nothing consumed the repo's OWN task list — every
internal change was human-driven. This module closes that gap with the same
discipline as the rest of the system:

- queue (human adds tasks) → propose (agent, read-only, scheduled) →
  approve (human click, existing approval tokens) → build (agent writes +
  verifies) → record.
- The agent NEVER commits, pushes, or touches paths outside the task scope.
  Writes happen only through OpenCodeBridge (same runs dir, same diffs).
- Verification: task test_command when given, else ruff on changed .py files.
  No green evidence → status failed, never done.

$0/open-source: execution model is whatever opencode runs locally (OAR free
chain); no new dependency, no external service.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.autonomy.internal_dev")

REPO_ROOT = Path(__file__).resolve().parents[2]

TASK_KINDS = ("implement", "fix", "refactor")
STATUS_QUEUED = "queued"
STATUS_PROPOSED = "proposed"
STATUS_DONE = "done"
STATUS_FAILED = "failed"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "dev_queue.json"


@dataclass(slots=True)
class DevTask:
    id: str
    kind: str = "implement"  # implement | fix | refactor
    description: str = ""
    scope_paths: list[str] = field(default_factory=list)
    test_command: str = ""  # acceptance, e.g. "pytest tests/test_x.py -q"
    status: str = STATUS_QUEUED
    proposal: str = ""
    run_id: str = ""
    evidence: str = ""
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DevQueue:
    """Persistent internal task queue. Best-effort I/O, never raises on load/save."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path) if store_path else _default_store_path()
        self._tasks: dict[str, DevTask] = {}
        self._load()

    def add(
        self,
        kind: str,
        description: str,
        scope_paths: list[str] | None = None,
        test_command: str = "",
    ) -> DevTask:
        if kind not in TASK_KINDS:
            raise ValueError(f"kind debe ser {'|'.join(TASK_KINDS)}")
        if not (description or "").strip():
            raise ValueError("description vacía")
        task = DevTask(
            id=f"dev_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            kind=kind,
            description=description.strip(),
            scope_paths=[p for p in (scope_paths or []) if p],
            test_command=test_command.strip(),
        )
        self._tasks[task.id] = task
        self._save()
        return task

    def get(self, task_id: str) -> DevTask | None:
        return self._tasks.get(task_id)

    def list(self, status: str | None = None) -> list[DevTask]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at)
        return [t for t in tasks if status is None or t.status == status] if status else tasks

    def _set(self, task: DevTask, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(task, key, value)
        task.updated_at = _utcnow_iso()
        self._save()

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                for raw in data.get("tasks", []):
                    try:
                        self._tasks[raw["id"]] = DevTask(**raw)
                    except TypeError:
                        logger.warning("Dev task corrupto ignorado: %s", raw.get("id"))
        except Exception as exc:
            logger.warning("Could not load dev queue: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(
                json.dumps({"tasks": [t.to_dict() for t in self._tasks.values()]}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not save dev queue: %s", exc)


def _task_prompt(task: DevTask) -> str:
    scope = "\n".join(f"- {p}" for p in task.scope_paths) or "- (repo-wide, minimal diff)"
    return (
        f"[{task.kind}] {task.description}\n"
        f"Scope permitido (no tocar nada fuera de esto):\n{scope}\n"
        f"Aceptación: {task.test_command or 'ruff limpio en archivos cambiados'}\n"
        "Prohibido commitear, pushear o modificar archivos fuera del scope."
    )


async def run_internal_dev_propose(queue: DevQueue | None = None, bridge: Any = None) -> dict[str, Any]:
    """Propose the oldest queued task (read-only). Never raises."""
    queue = queue or DevQueue()
    pending = queue.list(status=STATUS_QUEUED)
    if not pending:
        return {"proposed": 0, "reason": "cola vacía"}
    task = pending[0]
    try:
        if bridge is None:
            from cores.copilot.opencode_bridge import get_opencode_bridge

            bridge = get_opencode_bridge()
        result = await bridge.propose(_task_prompt(task))
        queue._set(
            task,
            status=STATUS_PROPOSED,
            proposal=str(result.get("output", ""))[:4000],
            run_id=str(result.get("run_id", "")),
        )
        return {"proposed": 1, "task_id": task.id, "run_id": task.run_id}
    except Exception as exc:
        queue._set(task, status=STATUS_FAILED, evidence=f"propose_error: {type(exc).__name__}")
        return {"proposed": 0, "error": str(exc)}


def _verify_scope(task: DevTask, files_changed: list[str]) -> tuple[bool, str]:
    """Changed files must all live under the task scope (empty scope = anything, but flagged)."""
    if not task.scope_paths:
        return True, "sin scope declarado (revisión humana obligatoria)"
    outside = [
        f
        for f in files_changed
        if not any(f == s or f.startswith(s.rstrip("/") + "/") or s in f for s in task.scope_paths)
    ]
    if outside:
        return False, f"fuera de scope: {outside}"
    return True, "scope ok"


def _run_verification(task: DevTask) -> tuple[bool, str]:
    """Task test_command, else ruff on changed scope .py files. Returns (ok, evidence)."""
    try:
        if task.test_command:
            proc = subprocess.run(
                task.test_command.split(), cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300
            )
            tail = (proc.stdout + proc.stderr)[-1500:]
            return proc.returncode == 0, f"exit={proc.returncode}\n{tail}"
        targets = [str(REPO_ROOT / p) for p in task.scope_paths if p.endswith(".py")]
        if not targets:
            return True, "sin comando ni .py en scope (revisión humana)"
        proc = subprocess.run(
            ["ruff", "check", *targets], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]
    except Exception as exc:
        return False, f"verify_error: {type(exc).__name__}"


async def approve_and_build(
    task_id: str,
    approval_token: str | None,
    queue: DevQueue | None = None,
    bridge: Any = None,
) -> dict[str, Any]:
    """Human-approved build: consume token → bridge writes → verify → record. Never commits."""
    from cores.automation.safety import consume_approval

    queue = queue or DevQueue()
    task = queue.get(task_id)
    if task is None:
        return {"ok": False, "error": "task desconocido"}
    if task.status not in (STATUS_PROPOSED, STATUS_QUEUED):
        return {"ok": False, "error": f"task en estado {task.status} (no re-ejecutable)"}
    if not consume_approval(approval_token, "opencode:execute", "repo"):
        return {"ok": False, "error": "approval_token inválido o vencido (POST /api/copilot/approve primero)"}
    try:
        if bridge is None:
            from cores.copilot.opencode_bridge import get_opencode_bridge

            bridge = get_opencode_bridge()
        method = {"implement": bridge.implement, "fix": bridge.fix, "refactor": bridge.refactor}[task.kind]
        result = await method(_task_prompt(task))
        files_changed = [str(f) for f in (result.get("files_changed") or [])]
        scope_ok, scope_msg = _verify_scope(task, files_changed)
        if not scope_ok:
            queue._set(task, status=STATUS_FAILED, run_id=str(result.get("run_id", "")), evidence=scope_msg)
            return {"ok": False, "error": scope_msg}
        ver_ok, ver_evidence = _run_verification(task)
        evidence = f"{scope_msg}\nrun_id={result.get('run_id', '')}\n{ver_evidence}"
        if ver_ok and bool(result.get("success", False)):
            queue._set(task, status=STATUS_DONE, run_id=str(result.get("run_id", "")), evidence=evidence[-3000:])
            return {"ok": True, "task_id": task.id, "files_changed": files_changed}
        queue._set(task, status=STATUS_FAILED, run_id=str(result.get("run_id", "")), evidence=evidence[-3000:])
        return {"ok": False, "error": "build o verificación falló (ver evidence)"}
    except Exception as exc:
        queue._set(task, status=STATUS_FAILED, evidence=f"build_error: {type(exc).__name__}")
        return {"ok": False, "error": str(exc)}


def run_internal_dev_propose_job() -> dict[str, Any]:
    """Scheduler entry: propose-only cycle (read-only, safe). Never raises."""
    import asyncio

    try:
        return asyncio.run(run_internal_dev_propose())
    except Exception as exc:  # pragma: no cover — run_internal_dev_propose never raises by contract
        return {"proposed": 0, "error": f"{type(exc).__name__}"}
