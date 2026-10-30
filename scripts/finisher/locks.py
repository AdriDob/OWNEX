"""Path-scoped locks for OWNEX Finisher.

Megaprompt §7: "No asignes varios trabajadores a modificar
simultáneamente los mismos archivos o zonas críticas... Para tareas que no
puedan aislarse, usa locks con propietario, expiración y recuperación."

Design:
  * A lock covers a set of repo-relative paths (files or directory prefixes).
  * ``GLOBAL_LOCK`` covers the whole repo and conflicts with everything.
  * Overlap is prefix-aware: ``cores/`` conflicts with ``cores/auth/x.py``.
  * Locks are persisted, so a crash does not leak them forever, and they expire.
  * A lock whose owner worker is no longer alive is reclaimed automatically.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.finisher.state import FinisherState

GLOBAL_LOCK = "**"
DEFAULT_TTL_SECONDS = 3600
PATH_SEP = os.sep


def normalize_path(path: str) -> str:
    """Normalize to a repo-relative, slash-separated, comparison-safe key."""
    p = path.strip().replace("\\", "/")
    while p.endswith("/") and len(p) > 1:
        p = p[:-1]
    if p.startswith("./"):
        p = p[2:]
    return p or "."


def paths_conflict(a: str, b: str) -> bool:
    """True when two paths cover overlapping territory.

    Normalizes internally so callers cannot get a false negative by passing an
    un-normalized value (e.g. "cores/" vs "cores/auth/x.py").
    """
    a = normalize_path(a)
    b = normalize_path(b)
    if a == GLOBAL_LOCK or b == GLOBAL_LOCK:
        return True
    if a == b:
        return True
    if a == "." or b == ".":
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def is_within_repo(path: str | Path, repo_root: Path | None = None) -> bool:
    """True si `path` queda dentro del repo, tras resolver symlinks y ``..``.

    Un path relativo se resuelve relativo a REPO_ROOT.
    Rutas inexistentes se evalúan léxicamente (sin seguir symlinks);
    paths existentes se resuelven con realpath.
    """
    from scripts.finisher.state import REPO_ROOT

    repo_root = Path(repo_root or REPO_ROOT).resolve()
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / path).resolve()
        else:
            candidate = Path(path).resolve()
    except Exception:
        return False
    try:
        repo_root_resolved = repo_root.resolve()
        candidate_resolved = Path(path).resolve()
        return candidate.is_relative_to(repo_root) or candidate == repo_root
    except Exception:
        return False


def resolve_safely(path: str | Path, repo_root: Path | None = None) -> str:
    """Resuelve symlinks y verifica que el path NO escape del repo.

    Args:
        path: Path a resolver (relativo o absoluto)
        repo_root: Raíz del repo (default: REPO_ROOT)

    Returns:
        Path resuelto (absoluto, sin symlinks) si está dentro del repo.

    Raises:
        ValueError: Si el path escapa del repo o no puede resolverse.
    """
    from scripts.finisher.state import REPO_ROOT

    repo_root = Path(repo_root or REPO_ROOT).resolve()
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / path).resolve()
        else:
            candidate = Path(path).resolve()
    except Exception as e:
        raise ValueError(f"No se pudo resolver el path {path!r}: {e}")

    try:
        repo_root_resolved = repo_root.resolve()
        candidate_resolved = Path(path).resolve()
        if not (candidate_resolved == repo_root_resolved or candidate_resolved.is_relative_to(repo_root_resolved)):
            raise ValueError(
                f"El path {path!r} resuelve a {candidate_resolved} que está fuera del repo ({repo_root_resolved})"
            )
    except Exception as e:
        raise ValueError(f"No se pudo verificar que {path!r} esté dentro del repo: {e}")

    # Retornar path normalizado (relativo al repo si es posible, sino absoluto)
    try:
        relative = candidate_resolved.relative_to(repo_root)
        return str(relative)
    except ValueError:
        return str(candidate_resolved)


def validate_task_scope(files: list[str] | None) -> list[str]:
    """Errores si el alcance declarado escapa del repo. Vacío = limpio.

    Una tarea sin archivos es global a propósito (GLOBAL_LOCK) y se permite.
    Rutas absolutas y escapes `..` se rechazan: el worktree es un directorio
    de trabajo, no una barrera del SO, así que el alcance declarado es la
    única frontera verificable antes de lanzar.
    """
    errors: list[str] = []
    for raw in files or []:
        if not isinstance(raw, str) or not raw.strip():
            errors.append(f"scope vacío o no texto: {raw!r}")
            continue
        p = raw.strip()
        if p.startswith("/") or p.startswith("\\") or (len(p) > 1 and p[1] == ":"):
            errors.append(f"ruta absoluta fuera del repo: {raw!r}")
            continue
        parts = [seg for seg in p.replace("\\", "/").split("/")]
        if ".." in parts:
            errors.append(f"escape '..' fuera del repo: {raw!r}")
    return errors


@dataclass
class LockResult:
    acquired: bool
    lock_id: str | None = None
    reason: str = ""
    conflicts_with: list[str] = field(default_factory=list)


class PathLockManager:
    def __init__(self, state: FinisherState, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.state = state
        self.ttl_seconds = ttl_seconds

    # -- inspection ---------------------------------------------------------

    def active_locks(self, now: float | None = None) -> dict[str, dict[str, Any]]:
        """Locks that are neither expired nor owned by a dead worker."""
        now = now if now is not None else time.time()
        out: dict[str, dict[str, Any]] = {}
        for lock_id, lock in self.state.locks.items():
            if float(lock.get("expires_at", 0)) <= now:
                continue
            if self._owner_is_dead(lock):
                continue
            out[lock_id] = lock
        return out

    def _owner_is_dead(self, lock: dict[str, Any]) -> bool:
        """True only when the owning worker is known to be gone.

        An owner with no worker record is NOT assumed dead: under-locking
        lets two agents corrupt the same files, which is worse than a lock
        that expires. Such locks are surfaced separately as orphans.
        """
        owner = lock.get("owner")
        if not owner:
            return False
        worker = self.state.workers.get(owner)
        if worker is None:
            return False
        from scripts.finisher.state import WorkerStatus

        return worker.status in (
            WorkerStatus.CRASHED,
            WorkerStatus.TERMINATED,
            WorkerStatus.TIMEOUT,
        )

    def orphan_locks(self) -> list[dict[str, Any]]:
        """Locks whose owner has no worker record at all — typically left by a
        crash. Reclaimable, but only during explicit recovery."""
        return [
            lock for lock in self.state.locks.values() if lock.get("owner") and lock["owner"] not in self.state.workers
        ]

    def conflicting_locks(self, paths: list[str]) -> list[dict[str, Any]]:
        held = self.active_locks()
        found: list[dict[str, Any]] = []
        for lock in held.values():
            for held_path in lock.get("paths", []):
                if any(paths_conflict(p, held_path) for p in paths):
                    found.append(lock)
                    break
        return found

    def conflicts_with_active(self, paths: list[str], exclude_task: str | None = None) -> bool:
        conflicts = self.conflicting_locks(paths)
        if not conflicts:
            return False
        if exclude_task is None:
            return True
        return any(c.get("task_id") != exclude_task for c in conflicts)

    # -- mutation -----------------------------------------------------------

    def acquire(
        self,
        owner: str,
        paths: list[str],
        task_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> LockResult:
        paths = [normalize_path(p) for p in paths] or [GLOBAL_LOCK]
        conflicts = self.conflicting_locks(paths)
        if conflicts:
            return LockResult(
                acquired=False,
                reason=f"paths locked by {[c.get('owner') for c in conflicts]}",
                conflicts_with=[c["lock_id"] for c in conflicts],
            )

        lock_id = f"lock_{owner}_{time.time_ns()}"
        ttl = ttl_seconds or self.ttl_seconds
        self.state.locks[lock_id] = {
            "lock_id": lock_id,
            "owner": owner,
            "task_id": task_id,
            "paths": paths,
            "acquired_at": time.time(),
            "expires_at": time.time() + ttl,
        }
        self._persist()
        return LockResult(acquired=True, lock_id=lock_id)

    def release(self, lock_id: str) -> bool:
        released = self.state.locks.pop(lock_id, None) is not None
        if released:
            self._persist()
        return released

    def release_for_owner(self, owner: str) -> int:
        released = [k for k, v in self.state.locks.items() if v.get("owner") == owner]
        for lock_id in released:
            del self.state.locks[lock_id]
        if released:
            self._persist()
        return len(released)

    def reap_expired(self, now: float | None = None) -> list[str]:
        now = now if now is not None else time.time()
        expired = [lock_id for lock_id, lock in self.state.locks.items() if float(lock.get("expires_at", 0)) <= now]
        for lock_id in expired:
            del self.state.locks[lock_id]
        if expired:
            self._persist()
        return expired

    def _persist(self) -> None:
        """Locks must survive a crash; otherwise two daemons could each believe
        they own the same paths."""
        try:
            from scripts.finisher.state import state_manager

            state_manager.save()
        except Exception:
            pass

    def heartbeat(self, lock_id: str, ttl_seconds: int | None = None) -> bool:
        """Extend a lock so long-running work is not evicted mid-task."""
        lock = self.state.locks.get(lock_id)
        if lock is None:
            return False
        lock["expires_at"] = time.time() + (ttl_seconds or self.ttl_seconds)
        self._persist()
        return True
