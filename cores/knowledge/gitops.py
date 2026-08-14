"""Git operations, secret scanning, local snapshots and safe writes.

Security model:
- paths are validated against the vault root (no traversal, no symlinks)
- secret scan runs before every commit/push; push is BLOCKED on findings
- writes are never silent: SafeWriter returns a diff preview unless the
  caller marks the operation as authorized
- every automated write first takes a snapshot of the affected file
"""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.knowledge.index import DATA_DIR

logger = __import__("logging").getLogger("ownex.knowledge")

DEFAULT_BACKUP_DIR = DATA_DIR / "knowledge" / "backups"

# ── Secret scanner ─────────────────────────────────────────────────────────

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-(proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_live", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "generic_password",
        re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^'\"]{8,}", re.IGNORECASE),
    ),
    ("wallet_seed", re.compile(r"\b(?:seed|mnemonic|recovery)[ _-]?(?:phrase|words?)\b", re.IGNORECASE)),
    ("private_key_hex", re.compile(r"\b(?:private[_-]?key|privkey|wallet[_-]?pk)\s*[:=]\s*['\"]?[0-9a-fA-F]{32,}")),
]

_SUSPICIOUS_FILES: list[tuple[str, re.Pattern[str]]] = [
    ("env_file", re.compile(r"(^|/)(\.env|\.env\..*)$")),
    ("keystore", re.compile(r"\.(pem|p12|pfx|key|jks|keystore)$")),
    ("wallet_file", re.compile(r"(keystore|wallet|id_rsa|id_ed25519|credentials)\.?(json|txt|md)?$")),
]

_IGNORED_SCAN_DIRS = {".ownex", ".obsidian", ".git", "node_modules", ".trash"}


@dataclass
class SecretFinding:
    file: str
    kind: str
    line: int
    snippet: str


@dataclass
class SecretScanResult:
    findings: list[SecretFinding] = field(default_factory=list)
    clean: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "findings": [{"file": f.file, "kind": f.kind, "line": f.line, "snippet": f.snippet} for f in self.findings],
        }


class SecretScanner:
    """Scans the vault working tree for credentials before Git operations."""

    def __init__(self, vault_root: Path):
        self._root = vault_root.resolve()

    def _iter_files(self) -> list[Path]:
        out: list[Path] = []
        for f in self._root.rglob("*"):
            if not f.is_file() or f.is_symlink():
                continue
            parts = set(f.relative_to(self._root).parts)
            if parts & _IGNORED_SCAN_DIRS:
                continue
            out.append(f)
        return out

    def scan(self) -> SecretScanResult:
        result = SecretScanResult()
        for f in self._iter_files():
            rel = str(f.relative_to(self._root)).replace("\\", "/")
            name = f.name.lower()
            if any(p.search(rel) for _, p in _SUSPICIOUS_FILES) and (name.endswith(".md") or f.suffix == ""):
                result.findings.append(SecretFinding(rel, "suspicious_file", 1, name))
                continue
            try:
                if f.stat().st_size > 2_000_000:
                    continue
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, start=1):
                if len(line) > 1000:
                    continue
                for kind, pattern in _SECRET_PATTERNS:
                    if pattern.search(line):
                        snippet = line.strip()[:80]
                        result.findings.append(SecretFinding(rel, kind, lineno, snippet))
                        break
        result.findings.sort(key=lambda x: x.file)
        result.clean = len(result.findings) == 0
        return result


# ── Git operations ─────────────────────────────────────────────────────────


@dataclass
class GitResult:
    ok: bool
    action: str
    detail: str
    blocked: bool = False
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "detail": self.detail,
            "blocked": self.blocked,
            "findings": self.findings,
        }


def _run_git(vault: Path, *args: str, timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(vault), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


class GitOps:
    def __init__(self, vault_root: Path):
        self._root = vault_root.resolve()

    def is_repo(self) -> bool:
        code, _, _ = _run_git(self._root, "rev-parse", "--is-inside-work-tree")
        return code == 0

    def status(self) -> dict[str, Any]:
        if not self.is_repo():
            return {"repo": False}
        code, stdout, _ = _run_git(self._root, "status", "--porcelain")
        code_branch, branch, _ = _run_git(self._root, "branch", "--show-current")
        return {
            "repo": True,
            "branch": branch or "detached",
            "dirty": bool(stdout),
            "changes": [line[:200] for line in stdout.splitlines()],
            "clean": not stdout,
        }

    def diff(self) -> dict[str, Any]:
        code, stdout, _ = _run_git(self._root, "diff", "--stat")
        code2, lines, _ = _run_git(self._root, "diff", "--numstat")
        return {
            "stat": stdout or "(no changes)",
            "changed_files": [ln for ln in lines.splitlines()],
            "ok": code == 0 and code2 == 0,
        }

    def commit(self, message: str) -> GitResult:
        scan = SecretScanner(self._root).scan()
        if not scan.clean:
            return GitResult(
                ok=False,
                action="commit",
                detail=f"BLOCKED by security scan ({len(scan.findings)} finding(s))",
                blocked=True,
                findings=scan.to_dict()["findings"],
            )
        code, out, err = _run_git(self._root, "add", "-A")
        if code != 0:
            return GitResult(ok=False, action="commit", detail=err or out)
        code, out, err = _run_git(self._root, "commit", "-m", message)
        if code != 0:
            return GitResult(ok=False, action="commit", detail=err or out)
        return GitResult(ok=True, action="commit", detail=out)

    def push(self) -> GitResult:
        scan = SecretScanner(self._root).scan()
        if not scan.clean:
            return GitResult(
                ok=False,
                action="push",
                detail=f"BLOCKED by security scan ({len(scan.findings)} finding(s))",
                blocked=True,
                findings=scan.to_dict()["findings"],
            )
        code, out, err = _run_git(self._root, "push")
        if code != 0:
            return GitResult(ok=False, action="push", detail=err or out)
        return GitResult(ok=True, action="push", detail=out)

    def pull(self) -> GitResult:
        code, out, err = _run_git(self._root, "pull")
        if code != 0:
            return GitResult(ok=False, action="pull", detail=err or out)
        return GitResult(ok=True, action="pull", detail=out)


# ── Local snapshots (backup / restore) ─────────────────────────────────────


class SnapshotManager:
    """Zip snapshots of the vault stored OUTSIDE it by default (data/knowledge/backups)."""

    def __init__(self, vault_root: Path, backup_dir: Path | None = None):
        self._root = vault_root.resolve()
        self._backup_dir = Path(backup_dir or DEFAULT_BACKUP_DIR).resolve()
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, ts: str | None = None) -> Path:
        stamp = ts or datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return self._backup_dir / f"vault_{stamp}.zip"

    def create(self, keep: int = 10) -> dict[str, Any]:
        dest = self._snapshot_path()
        count = 0
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in self._root.rglob("*"):
                if not f.is_file() or f.is_symlink():
                    continue
                rel = f.relative_to(self._root)
                if any(part.startswith(".ownex") or part == ".git" for part in rel.parts):
                    continue
                zf.write(f, rel.as_posix())
                count += 1
        # prune old snapshots
        snapshots = sorted(self._backup_dir.glob("vault_*.zip"), reverse=True)
        for old in snapshots[keep:]:
            old.unlink(missing_ok=True)
        return {
            "ok": True,
            "snapshot": dest.name,
            "path": str(dest),
            "files": count,
            "size_bytes": dest.stat().st_size,
            "kept": min(keep, len(snapshots)),
        }

    def list(self) -> list[dict[str, Any]]:
        out = []
        for snap in sorted(self._backup_dir.glob("vault_*.zip"), reverse=True):
            out.append(
                {
                    "name": snap.name,
                    "path": str(snap),
                    "size_bytes": snap.stat().st_size,
                    "created": datetime.fromtimestamp(snap.stat().st_mtime).isoformat(),
                }
            )
        return out

    def restore(self, snapshot_name: str, authorized: bool = False) -> dict[str, Any]:
        """Restore a snapshot over the vault. Never runs without authorization."""
        if not authorized:
            return {"ok": False, "error": "authorization required"}
        target = self._backup_dir / snapshot_name
        if not target.exists() or not target.is_file():
            return {"ok": False, "error": "snapshot not found"}
        with zipfile.ZipFile(target, "r") as zf:
            for member in zf.infolist():
                name = member.filename
                if name.startswith("/") or ".." in name.split("/"):
                    continue
                dest = (self._root / name).resolve()
                if self._root not in dest.parents:
                    continue
                if member.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as out:  # noqa: SIM117
                    shutil.copyfileobj(src, out)
        return {"ok": True, "snapshot": snapshot_name}


# ── Safe writer ────────────────────────────────────────────────────────────


class SafeWriter:
    """Create/update notes with explicit authorization and diff previews."""

    def __init__(self, vault_root: Path, snapshots: SnapshotManager):
        self._root = vault_root.resolve()
        self._snapshots = snapshots

    def _resolve(self, rel_path: str) -> Path:
        target = (self._root / rel_path).resolve()
        if target == self._root:
            raise ValueError("cannot write the vault root")
        if self._root not in target.parents:
            raise ValueError("path escapes vault")
        return target

    def preview(self, rel_path: str, content: str) -> dict[str, Any]:
        target = self._resolve(rel_path)
        if not target.exists():
            return {
                "action": "create",
                "path": rel_path,
                "added": len(content.splitlines()),
                "removed": 0,
            }
        existing = target.read_text(encoding="utf-8", errors="replace")
        old_lines = existing.splitlines()
        new_lines = content.splitlines()
        added = sum(1 for ln in new_lines if ln not in set(old_lines))
        removed = sum(1 for ln in old_lines if ln not in set(new_lines))
        return {"action": "update", "path": rel_path, "added": added, "removed": removed}

    def write(self, rel_path: str, content: str, authorized: bool = False) -> dict[str, Any]:
        if not authorized:
            return {"ok": False, "authorization_required": True, **self.preview(rel_path, content)}
        target = self._resolve(rel_path)
        exists = target.exists()
        pre_snapshot = None
        if exists:
            pre_snapshot = self._backup_file(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "action": "update" if exists else "create",
            "path": rel_path,
            "pre_snapshot": pre_snapshot,
        }

    def _backup_file(self, rel_path: str) -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        snap_dir = self._snapshots._backup_dir / "preserve"  # noqa: SLF001
        snap_dir.mkdir(parents=True, exist_ok=True)
        src = self._root / rel_path
        dest = snap_dir / f"{stamp}_{Path(rel_path).name}"
        shutil.copy2(src, dest)
        return str(dest)
