"""Auto-Changelog Generator — automated changelog from VERSION.txt + git history.

Generates professional CHANGELOG.md following Keep a Changelog format.
Captures system state before/after each modification for full traceability.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.auto_changelog")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION.txt"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
SNAPSHOT_DIR = PROJECT_ROOT / ".ownex" / "snapshots"


def get_current_version() -> str:
    """Read current version from VERSION.txt."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "0.1.0"


def run_git_log(since: str | None = None, max_count: int = 50) -> list[dict[str, str]]:
    """Get formatted git log entries."""
    try:
        cmd = [
            "git",
            "log",
            f"--max-count={max_count}",
            "--format=%H|%an|%at|%s",
        ]
        if since:
            cmd.insert(2, f"--since={since}")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                sha, author, timestamp, message = parts
                commits.append(
                    {
                        "sha": sha[:8],
                        "author": author,
                        "date": datetime.fromtimestamp(int(timestamp), tz=UTC).isoformat(),
                        "message": message,
                    }
                )
        return commits
    except Exception as e:
        logger.warning("Git log failed: %s", e)
        return []


def classify_commit(message: str) -> tuple[str, str]:
    """Classify a commit message into a changelog category."""
    msg_lower = message.lower()

    categories = [
        ("feat", "feat", ["feat", "feature", "add", "new", "implement"]),
        ("fix", "fix", ["fix", "bug", "hotfix", "patch", "resolve"]),
        ("docs", "docs", ["docs", "documentation", "readme"]),
        ("refactor", "refactor", ["refactor", "clean", "restructure", "rename"]),
        ("test", "test", ["test", "spec", "coverage"]),
        ("perf", "perf", ["perf", "performance", "optimize", "speed"]),
        ("security", "security", ["security", "vuln", "cve", "auth"]),
        ("deps", "deps", ["deps", "dependency", "upgrade", "bump"]),
    ]

    for cat_key, cat_label, keywords in categories:
        for kw in keywords:
            if msg_lower.startswith(kw) or f":{kw}:" in msg_lower:
                return cat_key, cat_label

    return "chore", "chore"


def generate_changelog_entry(version: str, commits: list[dict[str, str]]) -> str:
    """Generate a single changelog entry for a version."""
    classified: dict[str, list[str]] = {
        "feat": [],
        "fix": [],
        "docs": [],
        "refactor": [],
        "test": [],
        "perf": [],
        "security": [],
        "deps": [],
        "chore": [],
    }

    for commit in commits:
        cat_key, _ = classify_commit(commit["message"])
        msg = commit["message"]
        # Clean up conventional commit prefixes
        for prefix in ["feat:", "fix:", "docs:", "refactor:", "test:", "perf:", "security:", "chore:", "deps:"]:
            if msg.lower().startswith(prefix):
                msg = msg[len(prefix) :].strip()
                break
        if msg.lower().startswith(
            ("feat(", "fix(", "docs(", "refactor(", "test(", "perf(", "security(", "chore(", "deps(")
        ):
            msg = msg.split(")", 1)[-1].strip()
            if msg.startswith(":"):
                msg = msg[1:].strip()

        classified[cat_key].append(f"- {msg}")

    labels = {
        "feat": "🚀 Features",
        "fix": "🐛 Bug Fixes",
        "docs": "📖 Documentation",
        "refactor": "♻️ Refactors",
        "test": "🧪 Tests",
        "perf": "⚡ Performance",
        "security": "🔒 Security",
        "deps": "📦 Dependencies",
        "chore": "🔧 Chores",
    }

    sections = []
    for cat_key, label in labels.items():
        if classified[cat_key]:
            sections.append(f"### {label}")
            sections.extend(classified[cat_key])
            sections.append("")

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    header = f"## [{version}] - {today}\n"
    body = "\n".join(sections) if sections else "No significant changes.\n"

    return header + "\n" + body + "\n"


def update_changelog(since: str | None = None, version: str | None = None) -> dict[str, Any]:
    """Update CHANGELOG.md with new entries since the last version."""
    version = version or get_current_version()
    commits = run_git_log(since=since)

    if not commits:
        return {"updated": False, "reason": "No new commits found", "commits": 0}

    # Generate new entry
    new_entry = generate_changelog_entry(version, commits)

    # Read existing changelog or create new
    existing = ""
    if CHANGELOG_FILE.exists():
        existing = CHANGELOG_FILE.read_text()

    if existing:
        # Insert after the header
        lines = existing.split("\n")
        # Find the first ## or end of header
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("## ") and i > 1:
                insert_at = i
                break
        if insert_at == 0:
            insert_at = len(lines)

        lines.insert(insert_at, new_entry)
        content = "\n".join(lines)
    else:
        content = f"# Changelog\n\nAll notable changes to the OWNEX project.\n\n{new_entry}"

    CHANGELOG_FILE.write_text(content)
    logger.info("Changelog updated with %d commits for version %s", len(commits), version)

    return {
        "updated": True,
        "version": version,
        "commits": len(commits),
        "categories": len(set(classify_commit(c["message"])[0] for c in commits)),
    }


def create_snapshot(label: str = "pre-update") -> dict[str, Any]:
    """Create a system state snapshot for traceability."""
    from core.system.version_engine import VersionEngine

    ve = VersionEngine()
    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": ve.get_version(),
        "label": label,
        "files": {},
    }

    key_files = [
        "VERSION.txt",
        "CHANGELOG.md",
        "pyproject.toml",
        "core/__init__.py",
        "frontend/package.json",
    ]

    for rel_path in key_files:
        path = PROJECT_ROOT / rel_path
        if path.exists() and path.stat().st_size < 50000:
            snapshot["files"][rel_path] = path.read_text()

    # Save snapshot
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    snapshot_path = SNAPSHOT_DIR / f"snapshot_{label}_{timestamp}.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2))

    # Clean old snapshots (keep last 20)
    snapshots = sorted(SNAPSHOT_DIR.glob("*.json"))
    for old in snapshots[:-20]:
        old.unlink()

    logger.info("Snapshot created: %s", snapshot_path)
    return {
        "path": str(snapshot_path),
        "version": snapshot["version"],
        "timestamp": snapshot["timestamp"],
        "files_captured": len(snapshot["files"]),
    }


def compare_snapshots(before_label: str = "pre-update", after_label: str = "post-update") -> dict[str, Any]:
    """Compare two snapshots to show what changed."""
    SNAPSHOT_DIR / f"snapshot_{before_label}_"
    SNAPSHOT_DIR / f"snapshot_{after_label}_"

    before_paths = sorted(SNAPSHOT_DIR.glob(f"*{before_label}*"))
    after_paths = sorted(SNAPSHOT_DIR.glob(f"*{after_label}*"))

    if not before_paths or not after_paths:
        return {"error": "Snapshots not found", "before": str(before_paths), "after": str(after_paths)}

    before = json.loads(before_paths[-1].read_text())
    after = json.loads(after_paths[-1].read_text())

    changes = []
    for file_path in set(list(before.get("files", {})) + list(after.get("files", {}))):
        old_content = before.get("files", {}).get(file_path, "")
        new_content = after.get("files", {}).get(file_path, "")
        if old_content != new_content:
            changes.append(file_path)

    return {
        "version_before": before.get("version"),
        "version_after": after.get("version"),
        "timestamp_before": before.get("timestamp"),
        "timestamp_after": after.get("timestamp"),
        "files_changed": changes,
        "total_changes": len(changes),
    }
