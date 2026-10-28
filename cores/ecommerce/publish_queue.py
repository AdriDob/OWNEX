"""Cola de publicación IG — el pack semanal con estado persistente.

Flujo honesto semiautomático: OWNEX arma QUÉ publicar cada día (pack) y el
humano publica (IG no tiene token) y marca ✓. Sin token de Meta no hay
auto-posteo real: esta cola es lo máximo automatizable sin mentir.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.ecommerce.publish_queue")

QUEUE_FILENAME = "ecommerce_publish_queue.json"
ESTADOS_VALIDOS = ("pendiente", "publicado")


def _queue_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / QUEUE_FILENAME


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class PublishQueue:
    """Pack semanal persistido con estado por día. Tolerante a corrupción."""

    def __init__(self, path: Path | None = None):
        self.path = path or _queue_path()
        self._days: list[dict[str, Any]] = []
        self._built_at: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            days = raw.get("days")
            if not isinstance(days, list):
                return
            kept = [d for d in days if isinstance(d, dict) and d.get("dia")]
            for d in kept:
                d.setdefault("estado", "pendiente")
            self._days = kept
            self._built_at = raw.get("built_at")
        except (OSError, ValueError, AttributeError) as exc:
            logger.warning("publish_queue: store ilegible, se empieza vacío: %s", exc)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"built_at": self._built_at, "days": self._days}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("publish_queue: no se pudo persistir: %s", exc)

    def rebuild(self, products: list[dict[str, Any]]) -> dict[str, Any]:
        """Regenera la semana preservando los días ya publicados (no se pierde trabajo)."""
        from cores.ecommerce.design import weekly_pack

        done = {d.get("dia") for d in self._days if d.get("estado") == "publicado"}
        pack = weekly_pack(products)
        self._days = []
        for d in pack.get("days", []):
            entry = dict(d)
            if d.get("dia") in done and d.get("producto"):
                entry["estado"] = "publicado"
            else:
                entry["estado"] = "pendiente"
            self._days.append(entry)
        self._built_at = _now_iso()
        self._save()
        return self.to_dict()

    def mark_published(self, dia: str) -> dict[str, Any] | None:
        """Marca un día como publicado. None si el día no existe."""
        for d in self._days:
            if str(d.get("dia", "")).lower() == str(dia or "").lower():
                d["estado"] = "publicado"
                d["published_at"] = _now_iso()
                self._save()
                return dict(d)
        return None

    def to_dict(self) -> dict[str, Any]:
        pendientes = sum(1 for d in self._days if d.get("estado") != "publicado")
        return {
            "built_at": self._built_at,
            "total": len(self._days),
            "pendientes": pendientes,
            "publicados": len(self._days) - pendientes,
            "days": [dict(d) for d in self._days],
        }


_store: PublishQueue | None = None


def get_publish_queue() -> PublishQueue:
    global _store
    if _store is None:
        _store = PublishQueue()
    return _store
