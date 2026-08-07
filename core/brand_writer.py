"""Brand Writer — contenido público desde evidencia real.

Convierte cada write-up / bounty aprobado / episodio de post-mortem en
borradores de contenido para X, LinkedIn y blog. Acelera la reputación
sin que el operador tenga que escribir desde cero.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.brand_writer")

_DEFAULT_STATE = {
    "drafts": [],
}


class BrandWriter:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/brand_writer/")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                state = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    state.setdefault(k, v)
                return state
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, state: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def generate(self, topic: str, detail: str = "", channels: list[str] | None = None) -> dict[str, Any]:
        channels = channels or ["x", "linkedin"]
        now = datetime.now(UTC)
        drafts = []
        for ch in channels:
            text = self._template(ch, topic, detail, now)
            drafts.append({"channel": ch, "text": text})
        entry = {
            "id": f"bw-{int(now.timestamp() * 1000)}",
            "topic": topic.strip(),
            "created_at": now.isoformat(),
            "drafts": drafts,
            "published": False,
        }
        state = self._load()
        state["drafts"].append(entry)
        self._save(state)
        return {"success": True, "entry": entry}

    def _template(self, channel: str, topic: str, detail: str, now: datetime) -> str:
        d = detail.strip() or "un hallazgo/avance real de esta semana."
        if channel == "x":
            return (
                f"🕸️ {topic}\n\n{d}\n\n"
                "Progreso real semana a semana, documentado. Si haces "
                "lo mismo que hago, no hay sorteos: hay work.\n\n"
                "#hunting #bugbounty #openSource"
            )
        if channel == "linkedin":
            return (
                f"**{topic}**\n\n{d}\n\n"
                "Mantuve la consistencia. Recordá: repositorios y write-ups valen más "
                "que CV. Comparto porque el feedback real mejora el próximo hallazgo.\n\n"
                f"_—- Generated en {now.strftime('%Y-%m-%d')} por OWNEX Brand Writer._"
            )
        return f"{topic}\n\n{d}"

    def mark_published(self, draft_id: str, channel: str = "") -> dict[str, Any]:
        state = self._load()
        for d in state["drafts"]:
            if d.get("id") == draft_id:
                if channel and channel in (c["channel"] for c in d.get("drafts", [])):
                    for c in d["drafts"]:
                        if c["channel"] == channel:
                            c["published"] = True
                else:
                    d["published"] = True
                self._save(state)
                return {"success": True}
        return {"success": False, "message": "Borrador no encontrado."}

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        return {"success": True, "drafts": state["drafts"][-10:][::-1], "total": len(state["drafts"])}


_bw: BrandWriter | None = None


def get_brand_writer() -> BrandWriter:
    global _bw
    if _bw is None:
        _bw = BrandWriter()
    return _bw
