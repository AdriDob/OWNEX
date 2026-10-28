"""Bounty Tracker — memoria persistente claim → PR → merge → payout (P1 vNext).

El executor corre en memoria: si el proceso muere o el poll expira, el
estado del bounty se pierde. Este módulo es la memoria: estados con
evidencia por transición y PAID SOLO ante evidencia (monto > 0 + referencia
de pago). Sin evidencia no hay PAID — nunca se inventa un cobro.

Puente a calibración: ``to_learning_record()`` convierte terminales en
LearningRecord (merged/paid → accepted; failed → rejected) para
``calibrate()`` / ``p_accept_estimate()``. Sin red, sin polling.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.opportunity.bounty_tracker")

STATUS_CLAIMED = "claimed"
STATUS_PR_OPEN = "pr_open"
STATUS_MERGED = "merged"
STATUS_PAID = "paid"
STATUS_FAILED = "failed"
STATUS_EXPIRED = "expired"

TERMINAL_STATUSES = frozenset({STATUS_MERGED, STATUS_PAID, STATUS_FAILED, STATUS_EXPIRED})
OPEN_STATUSES = frozenset({STATUS_CLAIMED, STATUS_PR_OPEN})


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _default_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "bounty_tracker.json"


@dataclass(slots=True)
class TrackedBounty:
    id: str
    platform: str
    issue_url: str
    pr_url: str = ""
    amount_usd: float = 0.0
    status: str = STATUS_CLAIMED
    merge_sha: str = ""
    paid_ref: str = ""
    fail_reason: str = ""
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BountyTracker:
    """Cola persistente de bounties OSS. I/O best-effort, nunca raisea en load/save."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path) if store_path else _default_store_path()
        self._items: dict[str, TrackedBounty] = {}
        self._load()

    def track(self, platform: str, issue_url: str) -> TrackedBounty:
        """Registra un claim. Idempotente por issue_url: no duplica."""
        clean_url = (issue_url or "").strip()
        if not clean_url:
            raise ValueError("issue_url vacía")
        for item in self._items.values():
            if item.issue_url == clean_url and item.platform == (platform or "").strip().lower():
                return item
        item = TrackedBounty(
            id=f"bounty_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            platform=(platform or "").strip().lower(),
            issue_url=clean_url,
        )
        self._items[item.id] = item
        self._save()
        return item

    def get(self, bounty_id: str) -> TrackedBounty | None:
        return self._items.get(bounty_id)

    def set_pr(self, bounty_id: str, pr_url: str) -> TrackedBounty:
        item = self._require(bounty_id)
        if not (pr_url or "").strip():
            raise ValueError("pr_url vacía")
        item.pr_url = pr_url.strip()
        item.status = STATUS_PR_OPEN
        return self._touch(item)

    def set_merged(self, bounty_id: str, merge_sha: str = "") -> TrackedBounty:
        item = self._require(bounty_id)
        item.merge_sha = (merge_sha or "").strip()
        item.status = STATUS_MERGED
        return self._touch(item)

    def set_paid(self, bounty_id: str, amount_usd: float, paid_ref: str) -> TrackedBounty:
        """PAID solo ante evidencia: monto > 0 Y referencia de pago no vacía."""
        item = self._require(bounty_id)
        if not amount_usd or amount_usd <= 0:
            raise ValueError("PAID exige amount_usd > 0 (sin monto no hay cobro)")
        if not (paid_ref or "").strip():
            raise ValueError("PAID exige paid_ref (evidencia del pago)")
        item.amount_usd = float(amount_usd)
        item.paid_ref = paid_ref.strip()
        item.status = STATUS_PAID
        return self._touch(item)

    def set_failed(self, bounty_id: str, reason: str = "") -> TrackedBounty:
        item = self._require(bounty_id)
        item.fail_reason = (reason or "")[:500]
        item.status = STATUS_FAILED
        return self._touch(item)

    def expire(self, bounty_id: str) -> TrackedBounty:
        item = self._require(bounty_id)
        item.status = STATUS_EXPIRED
        return self._touch(item)

    def list(self, status: str | None = None) -> list[TrackedBounty]:
        items = list(self._items.values())
        if status:
            items = [i for i in items if i.status == status]
        return items

    def pending(self) -> list[TrackedBounty]:
        """En vuelo: claimed/pr_open/merged (merged sin PAID = cobrar pendiente)."""
        return [i for i in self._items.values() if i.status in OPEN_STATUSES or i.status == STATUS_MERGED]

    def to_learning_record(self, bounty_id: str) -> Any | None:
        """Terminal → LearningRecord para calibrate(). No-terminal → None (aún no es outcome)."""
        from cores.direct_work_engine.feedback import LearningRecord

        item = self._require(bounty_id)
        if item.status == STATUS_PAID:
            return LearningRecord(
                platform=item.platform,
                accepted=True,
                amount=item.amount_usd,
                paid=True,
                net_amount=item.amount_usd,
                technique="oss_bounty",
                program=item.platform,
            )
        if item.status == STATUS_MERGED:
            return LearningRecord(
                platform=item.platform,
                accepted=True,
                amount=item.amount_usd,
                technique="oss_bounty",
                program=item.platform,
            )
        if item.status in (STATUS_FAILED, STATUS_EXPIRED):
            return LearningRecord(platform=item.platform, accepted=False, technique="oss_bounty", program=item.platform)
        return None

    def _require(self, bounty_id: str) -> TrackedBounty:
        item = self._items.get(bounty_id)
        if item is None:
            raise KeyError(f"bounty desconocido: {bounty_id}")
        return item

    def _touch(self, item: TrackedBounty) -> TrackedBounty:
        item.updated_at = _utcnow_iso()
        self._save()
        return item

    def _load(self) -> None:
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                for raw in data.get("items", []):
                    try:
                        item = TrackedBounty(**{k: raw[k] for k in TrackedBounty.__dataclass_fields__ if k in raw})
                        self._items[item.id] = item
                    except (TypeError, KeyError):
                        continue
        except (OSError, ValueError) as exc:
            logger.warning("bounty_tracker: store ilegible, se empieza vacío: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(
                json.dumps({"items": [i.to_dict() for i in self._items.values()]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("bounty_tracker: no se pudo persistir: %s", exc)
