"""Dev Bounty Autopilot — auto-discovery + auto-proposal de bounts de código.

Riega descubrimiento de bounts (Opire/Superteam/Algora), los ranquea por $/esfuerzo,
ejecuta el pipeline de solución (análisis de repo/issue + código) y prepara propuestas
listas para que el operador solo VALIDE y SUBIR.

El operador es el gatekeeper: nada se envía sin su validación.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.dev_bounty_autopilot")

ENABLED_PLATFORMS = ["opire", "superteam", "algora", "gitcoin"]


class DevBountyAutopilot:
    """Auto-discovery + auto-proposal de dev bounts."""

    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/dev_bounty/")
        os.makedirs(self.data_dir, exist_ok=True)

    # ── Estado persistente ──

    @property
    def flag_file(self) -> str:
        return os.path.join(self.data_dir, ".active")

    def is_active(self) -> bool:
        return os.path.exists(self.flag_file)

    def activate(self) -> dict[str, Any]:
        with open(self.flag_file, "w") as f:
            f.write(datetime.now(UTC).isoformat())
        # persiste actualizaciones
        cfg = self._load()
        cfg["auto_discover"] = True
        cfg["auto_proposal"] = True
        cfg["requires_validation"] = True
        cfg.setdefault("beginner_mode", True)
        self._save(cfg)
        logger.info("[DEV_BOUNTY] Autopilot activado — vos solo validás y subís.")
        return {"success": True, "active": True, "config": cfg}

    def deactivate(self) -> dict[str, Any]:
        if os.path.exists(self.flag_file):
            os.remove(self.flag_file)
        cfg = self._load()
        cfg["auto_discover"] = False
        cfg["auto_proposal"] = False
        self._save(cfg)
        return {"success": True, "active": False}

    def _load(self) -> dict[str, Any]:
        path = os.path.join(self.data_dir, "config.json")
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"auto_discover": True, "auto_proposal": True, "requires_validation": True, "beginner_mode": True}

    def _save(self, cfg: dict[str, Any]) -> None:
        path = os.path.join(self.data_dir, "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def get_status(self) -> dict[str, Any]:
        cfg = self._load()
        return {
            "active": self.is_active(),
            "auto_discover": cfg.get("auto_discover", False),
            "auto_proposal": cfg.get("auto_proposal", False),
            "requires_validation": cfg.get("requires_validation", True),
            "beginner_mode": cfg.get("beginner_mode", True),
            "platforms": ENABLED_PLATFORMS,
            "ready_to_validate": self._count_pending_proposals(),
        }

    def set_beginner_mode(self, enabled: bool) -> dict[str, Any]:
        """Enciende/apaga el filtro de bounts aptos para principiantes."""
        cfg = self._load()
        cfg["beginner_mode"] = bool(enabled)
        self._save(cfg)
        return {"success": True, "beginner_mode": cfg["beginner_mode"]}

    # ── Filtrado por aptitud ──

    def _beginner_ready(self, opp: dict[str, Any]) -> bool:
        """Aptitud para arrancar: good-first-issue / bugs simples / bajo esfuerzo."""
        if not self._load().get("beginner_mode", True):
            return True
        haystack = (
            " ".join(
                str(opp.get(k, ""))
                for k in ("title", "description", "labels", "tags", "category", "complexity", "difficulty")
            )
        ).lower()
        beginner_hints = [
            "good first issue",
            "good-first-issue",
            "beginner",
            "easy",
            "novice",
            "bug",
            "fix",
            "small",
            "low effort",
            "low-effort",
            "simple",
            "docs",
            "typo",
            "refactor",
            "junior",
            "starter",
            "help wanted",
            "label: easy",
        ]
        # Símbolos de complejidad o estilo de URL que señalan tareas puntuales
        if "complex" in haystack or "high effort" in haystack or "hard" in haystack or "epic" in haystack:
            return False
        return any(h in haystack for h in beginner_hints)

    async def _rank_and_filter(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ranquea por $/esfuerzo y deja las aptas para principiantes."""
        scored = []
        for opp in opportunities:
            if not self._beginner_ready(opp):
                continue
            try:
                effort = float(
                    opp.get("estimated_effort_hours", opp.get("complexity", opp.get("difficulty", 1)) or 1) or 1
                )
            except (TypeError, ValueError):
                effort = 1.0
            reward = float(opp.get("reward", 0) or 0)
            scored.append((reward / max(effort, 0.1), opp))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [o for _, o in scored]

    # ── Propuestas pendientes de validar ──

    def _proposal_path(self) -> str:
        return os.path.join(self.data_dir, "proposals.json")

    def _read_proposals(self) -> list[dict[str, Any]]:
        try:
            with open(self._proposal_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _count_pending_proposals(self) -> int:
        return sum(1 for p in self._read_proposals() if not p.get("validated"))

    def _save_result(self, result: dict[str, Any], title: str, platform: str, repo: str) -> None:
        proposals = self._read_proposals()
        solution = result.get("solution", {}) if isinstance(result, dict) else {}
        entry = {
            "id": f"db-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "platform": platform,
            "repo": repo,
            "status": "ready",
            "validated": False,
            "created_at": datetime.now(UTC).isoformat(),
            "solution_preview": solution.get("summary", "") if isinstance(solution, dict) else "",
            "solution_files": solution.get("files", []) if isinstance(solution, dict) else [],
            "verdict": result.get("verdict", "ready"),
            "needs_user": True,
            "user_action": "Valida y cargá la solución (tu parte: revisar + subir)",
        }
        proposals.insert(0, entry)
        with open(self._proposal_path(), "w", encoding="utf-8") as f:
            json.dump(proposals, f, indent=2, ensure_ascii=False)

    # ── Descubrimiento + propuesta (orquestación) ──

    async def run_discovery_cycle(self) -> dict[str, Any]:
        """Corre un ciclo de descubrimiento + prepara propuesta."""
        if not self.is_active():
            return {"success": False, "message": "Dev Bounty Autopilot no está activo. Activalo primero."}

        # Buscar oportunidades de bounts (reusa discovery/sources) y filtrar/rankear
        opportunities = await self._discover_bounts()
        opportunities = await self._rank_and_filter(opportunities)
        created = 0
        for opp in opportunities[:5]:
            repo = opp.get("repo", "")
            if not repo:
                continue
            try:
                result = await self._run_pipeline(opp)
                if result.get("success"):
                    self._save_result(result, opp.get("title", "Bounty"), opp.get("platform", "opire"), repo)
                    created += 1
            except Exception as e:
                logger.warning("[DEV_BOUNTY] error: %s", e)

        return {
            "success": True,
            "discovered": len(opportunities),
            "proposals_ready": created,
            "pending_validation": self._count_pending_proposals(),
        }

    async def _discover_bounts(self) -> list[dict[str, Any]]:
        """Descubre bounts de código disponibles."""
        candidates: list[dict[str, Any]] = []
        try:
            # Reusa redes de descubrimiento y observación disponibles
            from core.autonomy.workflow_engine import get_workflow_engine

            engine = get_workflow_engine()
            if hasattr(engine, "scan_opportunities"):
                scan = await engine.scan_opportunities(platforms=ENABLED_PLATFORMS, limit=15)
                candidates = (
                    scan
                    if isinstance(scan, list)
                    else (scan.get("opportunities", []) if isinstance(scan, dict) else [])
                )
        except Exception as e:
            logger.warning("[DEV_BOUNTY] discovery fallback: %s", e)
        return candidates or []

    async def _run_pipeline(self, opp: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta el pipeline de bounty para una oportunidad y deja propuesta lista."""
        from core.autonomy.bounty_pipeline import get_bounty_pipeline

        pipeline = get_bounty_pipeline()
        result = await pipeline.execute_bounty(
            bounty_id=opp.get("id", ""),
            repo=opp.get("repo", ""),
            issue_number=opp.get("issue_number", 0),
            issue_url=opp.get("issue_url", ""),
            title=opp.get("title", ""),
            description=opp.get("description", ""),
        )
        return result.__dict__ if hasattr(result, "__dict__") else dict(result)

    # ── Qué debe hacer el operador ──

    def get_validation_queue(self) -> dict[str, Any]:
        """Propuestas listas para validar."""
        proposals = self._read_proposals()
        pending = [p for p in proposals if not p.get("validated")]
        return {
            "success": True,
            "pending": pending,
            "count": len(pending),
            "workflow_note": "Tu parte: revisá la propuesta, corre los tests, y cuando esté listo enviá. El autopilote NO envía sin tu validación.",
        }

    def validate_proposal(self, proposal_id: str, action: str = "approved") -> dict[str, Any]:
        """Marca la propuesta como validada (approved/rejected) y registra envío."""
        proposals = self._read_proposals()
        updated = False
        for p in proposals:
            if p.get("id") == proposal_id:
                p["validated"] = True
                p["status"] = "submitted" if action == "approved" else "rejected"
                p["validated_at"] = datetime.now(UTC).isoformat()
                updated = True
                break
        if updated:
            with open(self._proposal_path(), "w", encoding="utf-8") as f:
                json.dump(proposals, f, indent=2, ensure_ascii=False)
        return {"success": updated, "action": action, "proposal_id": proposal_id}


def get_dev_bounty_autopilot() -> DevBountyAutopilot:
    global _autopilot
    if _autopilot is None:
        _autopilot = DevBountyAutopilot()
    return _autopilot


_autopilot: DevBountyAutopilot | None = None
