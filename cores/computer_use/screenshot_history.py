"""Screenshot History — Store and retrieve screenshots from Computer Use sessions.

During a Computer Use session, each step captures a screenshot. This module
stores them with metadata so users can review the progression of a task,
debug failures, and learn from successful fills.

Architecture:
    capture → store (path + metadata) → retrieve (list/single) → cleanup (old sessions)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.computer_use.history")


@dataclass
class ScreenshotEntry:
    """A single screenshot with metadata."""

    id: str
    session_id: str
    step_number: int
    path: str
    timestamp: float = field(default_factory=time.time)
    action_summary: str = ""
    action_type: str = ""
    success: bool = True
    duration_ms: float = 0.0
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "step_number": self.step_number,
            "path": self.path,
            "timestamp": self.timestamp,
            "action_summary": self.action_summary,
            "action_type": self.action_type,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "width": self.width,
            "height": self.height,
            "file_size_bytes": self.file_size_bytes,
        }


@dataclass
class SessionHistory:
    """Complete history of a Computer Use session."""

    session_id: str
    task: str
    platform: str = ""
    screenshots: list[ScreenshotEntry] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    success: bool = False
    total_steps: int = 0
    total_duration_ms: float = 0.0
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        return self.total_duration_ms / 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "platform": self.platform,
            "screenshots": [s.to_dict() for s in self.screenshots],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "success": self.success,
            "total_steps": self.total_steps,
            "total_duration_ms": self.total_duration_ms,
            "duration_seconds": round(self.duration_seconds, 1),
            "error": self.error,
            "screenshot_count": len(self.screenshots),
        }


class ScreenshotHistory:
    """Manages screenshot history for Computer Use sessions.

    Usage:
        history = ScreenshotHistory()
        session = history.start_session("Open Firefox and search")
        history.add_screenshot(session.session_id, "/tmp/step1.png", step=1, summary="Clicked start menu")
        history.finish_session(session.session_id, success=True)
        history.get_session(session.session_id)  # → full session with screenshots
    """

    def __init__(self, data_dir: str | Path | None = None):
        self._data_dir = Path(data_dir) if data_dir else Path("data/computer_use_history")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SessionHistory] = {}
        self._max_sessions = 100  # keep last 100 sessions
        self._max_screenshots_per_session = 50  # keep last 50 screenshots per session

    def start_session(self, task: str, platform: str = "") -> SessionHistory:
        """Start a new session and return it."""
        import uuid

        session_id = f"cu_{uuid.uuid4().hex[:12]}"
        session = SessionHistory(session_id=session_id, task=task, platform=platform)
        self._sessions[session_id] = session
        logger.info("[HISTORY] Started session %s: %s", session_id, task[:80])
        return session

    def add_screenshot(
        self,
        session_id: str,
        path: str,
        step: int,
        summary: str = "",
        action_type: str = "",
        success: bool = True,
        duration_ms: float = 0.0,
    ) -> ScreenshotEntry | None:
        """Add a screenshot to a session."""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("[HISTORY] Session %s not found", session_id)
            return None

        # Get image dimensions and size
        width, height, file_size = self._get_image_info(path)

        entry = ScreenshotEntry(
            id=f"ss_{len(session.screenshots):04d}",
            session_id=session_id,
            step_number=step,
            path=path,
            action_summary=summary,
            action_type=action_type,
            success=success,
            duration_ms=duration_ms,
            width=width,
            height=height,
            file_size_bytes=file_size,
        )

        session.screenshots.append(entry)

        # Trim old screenshots if too many
        if len(session.screenshots) > self._max_screenshots_per_session:
            session.screenshots = session.screenshots[-self._max_screenshots_per_session :]

        return entry

    def finish_session(
        self,
        session_id: str,
        success: bool = False,
        total_steps: int = 0,
        total_duration_ms: float = 0.0,
        error: str | None = None,
    ) -> None:
        """Mark a session as finished."""
        session = self._sessions.get(session_id)
        if not session:
            return

        session.finished_at = time.time()
        session.success = success
        session.total_steps = total_steps
        session.total_duration_ms = total_duration_ms
        session.error = error

        # Persist session
        self._persist_session(session)

        # Trim old sessions
        self._trim_sessions()

        logger.info(
            "[HISTORY] Finished session %s: %s (%d screenshots, %.1fs)",
            session_id,
            "success" if success else "failed",
            len(session.screenshots),
            total_duration_ms / 1000,
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        return session.to_dict() if session else None

    def list_sessions(self, limit: int = 20, platform: str | None = None) -> list[dict[str, Any]]:
        """List recent sessions."""
        sessions = list(self._sessions.values())
        if platform:
            sessions = [s for s in sessions if s.platform == platform]
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return [s.to_dict() for s in sessions[:limit]]

    def get_screenshots(self, session_id: str) -> list[dict[str, Any]]:
        """Get all screenshots for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [s.to_dict() for s in session.screenshots]

    def get_screenshot_at_step(self, session_id: str, step: int) -> dict[str, Any] | None:
        """Get screenshot at a specific step."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        for s in session.screenshots:
            if s.step_number == step:
                return s.to_dict()
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate stats across all sessions."""
        sessions = list(self._sessions.values())
        total = len(sessions)
        successful = sum(1 for s in sessions if s.success)
        total_screenshots = sum(len(s.screenshots) for s in sessions)
        return {
            "total_sessions": total,
            "successful_sessions": successful,
            "success_rate": round(successful / max(1, total), 3),
            "total_screenshots": total_screenshots,
            "avg_screenshots_per_session": round(total_screenshots / max(1, total), 1),
        }

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Remove sessions older than max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)
        to_remove = [sid for sid, s in self._sessions.items() if s.started_at < cutoff]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def _get_image_info(self, path: str) -> tuple[int, int, int]:
        """Get image dimensions and file size."""
        try:
            p = Path(path)
            file_size = p.stat().st_size if p.exists() else 0

            # Try PIL for dimensions
            try:
                from PIL import Image

                with Image.open(path) as img:
                    return img.width, img.height, file_size
            except ImportError:
                pass
            except Exception:
                pass

            return 0, 0, file_size
        except Exception:
            return 0, 0, 0

    def _persist_session(self, session: SessionHistory) -> None:
        """Save session to disk."""
        session_file = self._data_dir / f"{session.session_id}.json"
        try:
            session_file.write_text(json.dumps(session.to_dict(), indent=2))
        except Exception as exc:
            logger.warning("[HISTORY] Failed to persist session %s: %s", session.session_id, exc)

    def _trim_sessions(self) -> None:
        """Keep only the most recent sessions in memory."""
        if len(self._sessions) <= self._max_sessions:
            return
        sorted_sessions = sorted(self._sessions.items(), key=lambda x: x[1].started_at, reverse=True)
        self._sessions = dict(sorted_sessions[: self._max_sessions])

    def _load_persisted_sessions(self) -> None:
        """Load sessions from disk on startup."""
        for f in self._data_dir.glob("cu_*.json"):
            try:
                data = json.loads(f.read_text())
                session = SessionHistory(
                    session_id=data["session_id"],
                    task=data["task"],
                    platform=data.get("platform", ""),
                    started_at=data.get("started_at", 0),
                    finished_at=data.get("finished_at", 0),
                    success=data.get("success", False),
                    total_steps=data.get("total_steps", 0),
                    total_duration_ms=data.get("total_duration_ms", 0),
                    error=data.get("error"),
                )
                for ss_data in data.get("screenshots", []):
                    session.screenshots.append(ScreenshotEntry(**ss_data))
                self._sessions[session.session_id] = session
            except Exception as exc:
                logger.warning("[HISTORY] Failed to load session %s: %s", f, exc)


# ── Singleton ─────────────────────────────────────────────────────

_history: ScreenshotHistory | None = None


def get_screenshot_history(data_dir: str | Path | None = None) -> ScreenshotHistory:
    """Get or create the screenshot history singleton."""
    global _history
    if _history is None:
        _history = ScreenshotHistory(data_dir)
        _history._load_persisted_sessions()
    return _history
