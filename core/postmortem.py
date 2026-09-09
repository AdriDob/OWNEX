"""Post Mortem — episodios de aprendizaje por cada trabajo cerrado.

El 0,1% mantiene un "brainlog": qué salió, qué no, qué repetir. OWNEX
genera un episodio por cada bounty validado (aprobado o rechazado) y
lo reutiliza en recomendaciones y skill sessions.

Persistencia: ~/.config/ownex/postmortem/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.postmortem")

_DEFAULT_STATE = {
    "episodes": [],
}


class PostMortem:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/postmortem/")
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

    def register(
        self,
        item_type: str,
        item_title: str,
        outcome: str,
        learned: str = "",
        repeat: str = "",
        avoid: str = "",
    ) -> dict[str, Any]:
        if outcome not in ("approved", "rejected", "closed", "paused"):
            return {"success": False, "message": "Resultado inválido."}
        state = self._load()
        now = datetime.now(UTC)
        entry = {
            "id": f"pm-{int(now.timestamp() * 1000)}",
            "item_type": item_type,
            "item_title": item_title.strip(),
            "outcome": outcome,
            "learned": learned.strip(),
            "repeat": repeat.strip(),
            "avoid": avoid.strip(),
            "created_at": now.isoformat(),
        }
        state["episodes"].append(entry)
        self._save(state)
        return {"success": True, "entry": entry, "total": len(state["episodes"])}

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        eps = state.get("episodes", [])
        approved = sum(1 for e in eps if e.get("outcome") == "approved")
        rejected = sum(1 for e in eps if e.get("outcome") == "rejected")
        return {
            "success": True,
            "episodes": eps[-10:][::-1],
            "total": len(eps),
            "approved": approved,
            "rejected": rejected,
            "closed": len(eps) - approved - rejected,
            "learnings": self.lessons(),
        }

    def lessons(self) -> list[str]:
        state = self._load()
        lessons = []
        for e in state.get("episodes", [])[-20:]:
            if e.get("repeat"):
                lessons.append(f"Repetir: {e['repeat']}")
            if e.get("avoid"):
                lessons.append(f"Evitar: {e['avoid']}")
        return lessons[-10:]


_pm: PostMortem | None = None


def get_postmortem() -> PostMortem:
    global _pm
    if _pm is None:
        _pm = PostMortem()
    return _pm
