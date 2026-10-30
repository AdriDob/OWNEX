"""Git worktree isolation for OWNEX Finisher workers.

Megaprompt §7: "Utiliza worktrees y ramas independientes cuando sean adecuados."

A worker running `opencode run` in the main checkout edits the same tree the
user works in. Each task that declares files can instead run in its own
worktree, so a failed or rogue worker cannot corrupt the primary checkout.

Safety:
  * Worktrees live under ``.finisher/worktrees`` (never outside the repo).
  * Removal is explicit and never automatic — work may still be uncommitted.
  * No reset/clean/rebase is ever issued.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import scripts.finisher.state as state_mod

_SAFE_BRANCH = re.compile(r"[^A-Za-z0-9._/-]+")


@dataclass
class WorktreeInfo:
    path: str
    branch: str
    created: bool
    reason: str = ""


def _git(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def is_within_root(root: str | Path, candidate: str | Path) -> bool:
    """True si `candidate` queda dentro de `root`, tras resolver `..`,
    rutas absolutas y enlaces simbólicos.

    Un worktree es solo un directorio de trabajo: NO es una barrera del SO.
    Esta función existe para que la verificación RECHACE resultados con
    escrituras fuera del worktree autorizado, no para impedirlas.
    Rutas inexistentes se evalúan léxicamente (sin seguir symlinks que no
    existen); los symlinks existentes se resuelven con realpath.
    """
    import os

    root_real = os.path.realpath(root)
    cand = os.fspath(candidate)
    joined = cand if os.path.isabs(cand) else os.path.join(root_real, cand)
    cand_real = os.path.realpath(joined)
    return cand_real == root_real or cand_real.startswith(root_real + os.sep)


class WorktreeManager:
    def __init__(self, repo_root: Path | None = None, base_dir: Path | None = None):
        self._repo_root = repo_root
        self._base_dir = base_dir

    @property
    def repo_root(self) -> Path:
        """Resolved lazily so state-dir redirection (tests, sandbox runs) is honoured."""
        return self._repo_root or state_mod.REPO_ROOT

    @property
    def base_dir(self) -> Path:
        return self._base_dir or (state_mod.FINISHER_STATE_DIR / "worktrees")

    @staticmethod
    def branch_name(task_id: str) -> str:
        """Build a branch name that can never escape its namespace.

        A task id of `../../etc/passwd` must not become a traversal path when
        passed to `git worktree add`.
        """
        raw = task_id.replace("\\", "/")
        parts = [p for p in raw.split("/") if p not in ("", ".", "..")]
        slug = _SAFE_BRANCH.sub("-", "_".join(parts)).strip("-")
        return f"finisher/{slug or 'task'}"

    def available(self) -> tuple[bool, str]:
        if shutil.which("git") is None:
            return False, "git not on PATH"
        if not (self.repo_root / ".git").exists():
            return False, f"{self.repo_root} is not a git repository"
        return True, ""

    def create(self, task_id: str, base_ref: str | None = None) -> WorktreeInfo:
        ok, reason = self.available()
        if not ok:
            return WorktreeInfo(path="", branch="", created=False, reason=reason)

        branch = self.branch_name(task_id)
        path = self.base_dir / branch.replace("/", "_")

        existing = _git(["worktree", "list", "--porcelain"], self.repo_root)
        if existing.returncode != 0:
            return WorktreeInfo(path="", branch=branch, created=False, reason="git worktree list failed")

        if str(path) in existing.stdout:
            return WorktreeInfo(path=str(path), branch=branch, created=True, reason="reused existing worktree")

        self.base_dir.mkdir(parents=True, exist_ok=True)
        args = ["worktree", "add", "-b", branch, str(path)]
        if base_ref:
            args.append(base_ref)

        result = _git(args, self.repo_root, timeout=120)
        if result.returncode != 0:
            return WorktreeInfo(
                path="", branch=branch, created=False, reason=f"git worktree add failed: {result.stderr[:200]}"
            )
        return WorktreeInfo(path=str(path), branch=branch, created=True)

    def has_uncommitted(self, worktree_path: str) -> bool:
        result = _git(["status", "--porcelain"], Path(worktree_path), timeout=30)
        return result.returncode == 0 and bool(result.stdout.strip())

    def remove(self, worktree_path: str, force: bool = False) -> tuple[bool, str]:
        """Never automatic. Refuses while the worktree holds uncommitted work
        unless the caller explicitly forces it."""
        if not worktree_path:
            return False, "no path"
        p = Path(worktree_path)
        if not p.exists():
            return True, "already gone"

        if not force and self.has_uncommitted(worktree_path):
            return False, "refusing: worktree has uncommitted changes"

        args = ["worktree", "remove", str(p)]
        if force:
            args.append("--force")
        result = _git(args, self.repo_root, timeout=60)
        if result.returncode != 0:
            return False, result.stderr[:200]
        return True, "removed"

    def list_worktrees(self) -> list[dict[str, str]]:
        result = _git(["worktree", "list", "--porcelain"], self.repo_root, timeout=30)
        if result.returncode != 0:
            return []
        entries: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if not line.strip():
                if current:
                    entries.append(current)
                    current = {}
                continue
            key, _, value = line.partition(" ")
            if key == "worktree":
                current["path"] = value
            elif key == "branch":
                current["branch"] = value.replace("refs/heads/", "")
        if current:
            entries.append(current)
        return entries

    def finisher_worktrees(self) -> list[dict[str, str]]:
        prefix = str(self.base_dir)
        return [wt for wt in self.list_worktrees() if wt.get("path", "").startswith(prefix)]


worktree_manager = WorktreeManager()
