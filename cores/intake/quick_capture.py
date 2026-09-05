"""Quick Capture — zero-friction finding ingestion via global hotkeys.

The hunter lives in the browser/terminal; one hotkey (Ctrl+Shift+O) opens a
minimal capture that snapshots a URL → auto-enriches → lands in the Work Bank
as a zero-barrier item for processing. Companion to the Tauri tray/hotkey UX.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.quick_capture")


@dataclass
class QuickCaptureRecord:
    """A single quick capture."""

    id: str
    url: str
    title: str
    category: str
    severity: str
    notes: str = ""
    platform_hint: str | None = None
    source: str = "hotkey"  # hotkey | tray | manual
    captured_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "new"  # new | enriched | queued | dropped
    enrichment: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class QuickCaptureEngine:
    """Persists captures and enriches them into WorkBank items."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        base = os.environ.get("OWNEX_DATA_DIR")
        self.data_dir = (
            Path(data_dir) if data_dir else (Path(base) if base else Path(__file__).resolve().parents[3] / "data")
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.captures_file = self.data_dir / "quick_captures.json"

    def capture(
        self,
        url: str,
        title: str,
        category: str = "bug_bounty",
        severity: str = "medium",
        notes: str = "",
        source: str = "hotkey",
    ) -> QuickCaptureRecord:
        """Store a capture and return it with enrichment."""
        rec = QuickCaptureRecord(
            id=f"cap_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            url=url.strip(),
            title=title.strip() or url.strip(),
            category=category,
            severity=severity,
            notes=notes,
            source=source,
        )
        rec.enrichment = self._enrich(url)
        captures = self._load()
        captures[rec.id] = rec.to_dict()
        self._save(captures)
        logger.info("Captured %s (%s)", rec.title, rec.source)
        return rec

    def _enrich(self, url: str) -> dict[str, Any]:
        """Deterministic enrichment from the URL (zero network)."""
        parsed = urllib.parse.urlsplit(url)
        host = parsed.netloc
        path = parsed.path or "/"
        query_keys = list(urllib.parse.parse_qs(parsed.query).keys())
        return {
            "domain": host,
            "path": path,
            "query_params": query_keys,
            "has_params": bool(query_keys),
            "platform": self._guess_platform(host),
            "requires_focus": not bool(query_keys),
        }

    @staticmethod
    def _guess_platform(host: str) -> str | None:
        h = (host or "").lower()
        table = [
            ("hackerone.com", "hackerone"),
            ("bugcrowd.com", "bugcrowd"),
            ("intigriti.com", "intigriti"),
            ("yeswehack.com", "yeswehack"),
            ("opire.dev", "opire"),
            ("issuehunt.io", "issuehunt"),
            ("algora.io", "algora"),
            ("freelancer.com", "freelancer"),
        ]
        for needle, name in table:
            if needle in h:
                return name
        return None

    def list(self, limit: int = 20) -> list[QuickCaptureRecord]:
        captures = self._load()
        recs = [QuickCaptureRecord(**c) for c in captures.values()]
        recs.sort(key=lambda r: r.captured_at, reverse=True)
        return recs[:limit]

    def get(self, capture_id: str) -> QuickCaptureRecord | None:
        captures = self._load()
        if capture_id in captures:
            return QuickCaptureRecord(**captures[capture_id])
        return None

    def mark(self, capture_id: str, status: str) -> bool:
        captures = self._load()
        if capture_id not in captures:
            return False
        captures[capture_id]["status"] = status
        self._save(captures)
        return True

    def queue_to_workbank(self, capture_id: str) -> dict[str, Any]:
        """Push a capture into the Work Bank as a zero-barrier opportunity.

        Best-effort; if enrichment already produced an item this is a no-op
        re-queue. Returns whether it was queued and any error surfaced.
        """
        rec = self.get(capture_id)
        if not rec:
            return {"queued": False, "error": "capture_not_found"}
        try:
            from cores.direct_work_engine.models import (
                EmploymentType,
                Opportunity,
                OpportunityCategory,
                WorkPlatform,
            )
            from cores.direct_work_engine.workbank import get_workbank

            category = (
                OpportunityCategory(rec.category)
                if rec.category in OpportunityCategory.__members__
                else OpportunityCategory.BUG_BOUNTY
            )
            hint = (rec.platform_hint or "").lower()
            platform = WorkPlatform.OTHER
            for member in WorkPlatform:
                if member.value == hint or hint in member.name.lower():
                    platform = member
                    break
            opp = Opportunity(
                id=f"quick_{capture_id}",
                title=rec.title,
                description=rec.notes + f"\nURL: {rec.url}",
                platform=platform,
                category=category,
                payment=0.0,  # unknown → scored by barrier only
                employment_type=EmploymentType.MICROTASK,
                url=rec.url,
            )
            summary = get_workbank().daily_cycle([opp], target=1)
            self.mark(capture_id, "queued")
            return {
                "queued": True,
                "item_id": opp.id,
                "in_bank": summary.get("total_in_bank", 0),
            }
        except Exception as exc:
            logger.warning("queue_to_workbank failed: %s", exc)
            return {"queued": False, "error": str(exc)}

    # ── Persistence ──

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            with open(self.captures_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, captures: dict[str, dict[str, Any]]) -> None:
        with open(self.captures_file, "w", encoding="utf-8") as f:
            json.dump(captures, f, indent=2, ensure_ascii=False)


# ── Singleton ──────────────────────────────────────────────────────

_engine: QuickCaptureEngine | None = None


def get_quick_capture_engine() -> QuickCaptureEngine:
    global _engine
    if _engine is None:
        _engine = QuickCaptureEngine()
    return _engine
