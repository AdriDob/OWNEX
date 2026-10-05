"""Hunt Crew — equipo de cazadores sobre el pipeline vivo (Sprint 1).

Un crew NO ejecuta scans por su cuenta: el loop del scheduler singleton es
el único que escanea (api/scheduler.py; crear otro scheduler diverge estado
y quema presupuesto). El crew organiza la cobertura en paralelo:

- agentes con targets asignados, modo y rate-limit propio;
- validación en asignación (DNS escaneable, cupo, sin duplicar entre agentes);
- runs persistidos + métricas por agente (scans, findings, confirmados);
- gating solo-público: el programa se valida en la capa sources/unlock.

Todo best-effort, nunca raisea. Acciones externas siguen tras Human Gate.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.hunt.crew")

CREW_FILENAME = "hunt_crew.json"
RUNS_FILENAME = "hunt_crew_runs.jsonl"
DEFAULT_MAX_TARGETS = 5
DEFAULT_MIN_INTERVAL_S = 60
VALID_MODES = ("FAST", "DEEP", "API")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _crew_path() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data")) / CREW_FILENAME


def _runs_path() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data")) / RUNS_FILENAME


@dataclass(slots=True)
class HuntAgent:
    agent_id: str
    name: str
    targets: list[str] = field(default_factory=list)
    mode: str = "FAST"
    max_targets: int = DEFAULT_MAX_TARGETS
    min_interval_s: int = DEFAULT_MIN_INTERVAL_S
    program: str = "public"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HuntCrew:
    """Registro persistente de agentes + asignaciones. Nunca raisea."""

    def __init__(self, path: Path | None = None, runs_path: Path | None = None) -> None:
        self.path = path or _crew_path()
        self.runs_path = runs_path or _runs_path()
        self._agents: dict[str, HuntAgent] = {}
        self._load()

    def _load(self) -> None:
        try:
            if not self.path.exists():
                return
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            agents = raw.get("agents", {}) if isinstance(raw, dict) else {}
            for aid, data in agents.items():
                if isinstance(data, dict):
                    self._agents[str(aid)] = HuntAgent(
                        agent_id=str(aid),
                        name=str(data.get("name", aid)),
                        targets=[str(t) for t in data.get("targets", []) or []],
                        mode=str(data.get("mode", "FAST")),
                        max_targets=int(data.get("max_targets", DEFAULT_MAX_TARGETS)),
                        min_interval_s=int(data.get("min_interval_s", DEFAULT_MIN_INTERVAL_S)),
                        program=str(data.get("program", "public")),
                        created_at=str(data.get("created_at", "")),
                    )
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("hunt_crew: store ilegible, se empieza vacío: %s", exc)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {"agents": {a: ag.to_dict() for a, ag in self._agents.items()}}, ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("hunt_crew: no se pudo persistir: %s", exc)

    def create_agent(
        self, agent_id: str, name: str = "", mode: str = "FAST", max_targets: int = DEFAULT_MAX_TARGETS
    ) -> dict[str, Any]:
        aid = (agent_id or "").strip()
        if not aid:
            return {"ok": False, "reason": "agent_id vacío"}
        if aid in self._agents:
            return {"ok": False, "reason": "ya existe"}
        mode_up = (mode or "FAST").upper()
        if mode_up not in VALID_MODES:
            return {"ok": False, "reason": f"mode debe ser {'/'.join(VALID_MODES)}"}
        self._agents[aid] = HuntAgent(
            agent_id=aid,
            name=(name or aid).strip(),
            mode=mode_up,
            max_targets=max(1, int(max_targets or 1)),
            created_at=_now_iso(),
        )
        self._save()
        return {"ok": True, "agent": self._agents[aid].to_dict()}

    def remove_agent(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self._agents:
            return {"ok": False, "reason": "no existe"}
        del self._agents[agent_id]
        self._save()
        return {"ok": True}

    def assign(self, agent_id: str, target: str) -> dict[str, Any]:
        """Asigna un target con validación. Nunca raisea."""
        try:
            from cores.recon.hostname import scannable_domain

            ag = self._agents.get(agent_id)
            if ag is None:
                return {"ok": False, "reason": "agente no existe"}
            domain = (target or "").strip()
            if not domain:
                return {"ok": False, "reason": "target vacío"}
            if not scannable_domain(domain, domain):
                return {"ok": False, "reason": "dominio no escaneable (DNS imposible)"}
            if domain in ag.targets:
                return {"ok": False, "reason": "ya asignado a este agente"}
            for other_id, other in self._agents.items():
                if other_id != agent_id and domain in other.targets:
                    return {"ok": False, "reason": f"ya lo cubre {other_id} (sin duplicar scans)"}
            if len(ag.targets) >= ag.max_targets:
                return {"ok": False, "reason": f"cupo lleno ({ag.max_targets})"}
            ag.targets.append(domain)
            self._save()
            return {"ok": True, "agent": agent_id, "target": domain}
        except Exception as exc:
            logger.warning("hunt_crew: assign falló: %s", exc)
            return {"ok": False, "reason": "error interno"}

    def unassign(self, agent_id: str, target: str) -> dict[str, Any]:
        ag = self._agents.get(agent_id)
        if ag is None:
            return {"ok": False, "reason": "agente no existe"}
        if target not in ag.targets:
            return {"ok": False, "reason": "no estaba asignado"}
        ag.targets.remove(target)
        self._save()
        return {"ok": True}

    def list_agents(self) -> list[dict[str, Any]]:
        return [ag.to_dict() for ag in self._agents.values()]

    def record_scan(self, agent_id: str, target: str, findings_found: int = 0, confirmed: int = 0) -> dict[str, Any]:
        """Registra un scan ejecutado por el loop vivo a cuenta del agente."""
        try:
            self.runs_path.parent.mkdir(parents=True, exist_ok=True)
            with self.runs_path.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "at": _now_iso(),
                            "agent_id": agent_id,
                            "target": target,
                            "findings_found": max(0, int(findings_found or 0)),
                            "confirmed": max(0, int(confirmed or 0)),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            return {"ok": True}
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("hunt_crew: no se pudo registrar scan: %s", exc)
            return {"ok": False, "reason": "persistencia falló"}

    def agent_stats(self, agent_id: str) -> dict[str, Any]:
        """Métricas por agente desde el log de runs. Vacío honesto sin runs."""
        stats: dict[str, Any] = {"agent_id": agent_id, "scans": 0, "findings": 0, "confirmed": 0, "targets": []}
        try:
            ag = self._agents.get(agent_id)
            if ag is not None:
                stats["targets"] = list(ag.targets)
            if not self.runs_path.exists():
                return stats
            for line in self.runs_path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row, dict) or row.get("agent_id") != agent_id:
                    continue
                stats["scans"] += 1
                stats["findings"] += int(row.get("findings_found", 0) or 0)
                stats["confirmed"] += int(row.get("confirmed", 0) or 0)
        except OSError as exc:
            logger.warning("hunt_crew: no se pudo leer stats: %s", exc)
        return stats


_store: HuntCrew | None = None


def get_hunt_crew() -> HuntCrew:
    global _store
    if _store is None:
        _store = HuntCrew()
    return _store
