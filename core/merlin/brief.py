"""MERLIN Daily Brief — morning summary of system state, priorities, and opportunities.

Queries ORION's subsystems (targets, endpoints, findings, pipeline, financial)
and generates a structured daily briefing for Adriel.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database import db, models

logger = logging.getLogger("orion.core.merlin.brief")


def _safe_int(val: Any) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


class MerlinBrief:
    """Generates daily briefings from ORION system state."""

    def __init__(self) -> None:
        self._session = db.SessionLocal()

    def close(self) -> None:
        self._session.close()

    def generate(self) -> dict[str, Any]:
        """Generate a complete daily brief. Returns structured dict."""
        brief = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "targets": self._target_summary(),
            "pipeline": self._pipeline_summary(),
            "findings": self._findings_summary(),
            "opportunities": self._opportunity_summary(),
            "priorities": self._priority_actions(),
        }
        return brief

    def format_text(self, brief: dict[str, Any] | None = None) -> str:
        """Format the brief as a human-readable text summary."""
        if brief is None:
            brief = self.generate()

        lines = [
            "╔══════════════════════════════════════╗",
            "║        MERLIN DAILY BRIEF            ║",
            "╚══════════════════════════════════════╝",
            f"Generado: {brief['generated_at'][:19]}",
            "",
        ]

        t = brief["targets"]
        lines.append(f"🎯 Targets: {t['total']} total, {t['with_endpoints']} con endpoints")
        lines.append(f"   Endpoints: {t['endpoints']} descubiertos, {t['with_hypotheses']} con hipótesis")
        lines.append("")

        p = brief["pipeline"]
        lines.append(f"⚙️  Pipeline: {p['hypotheses_tested']} hipótesis probadas")
        if p["last_scan"]:
            lines.append(f"   Último scan: {p['last_scan']}")
        lines.append("")

        f = brief["findings"]
        lines.append(f"🔍 Findings: {f['total']} totales ({f['confirmed']} confirmados)")
        lines.append("")

        opp = brief["opportunities"]
        if opp:
            lines.append("💡 Oportunidades:")
            for o in opp[:5]:
                lines.append(f"   • {o['name']}: {o['description']}")
            if len(opp) > 5:
                lines.append(f"   ... y {len(opp) - 5} más")
            lines.append("")

        prio = brief["priorities"]
        if prio:
            lines.append("⚡ Acciones prioritarias:")
            for i, action in enumerate(prio[:3], 1):
                lines.append(f"   {i}. {action}")
            lines.append("")

        return "\n".join(lines)

    def _target_summary(self) -> dict[str, Any]:
        try:
            total = self._session.query(models.Target).count()
            with_endpoints = self._session.query(models.Endpoint.target_id).distinct().count()
            endpoints = self._session.query(models.Endpoint).count()
            with_hypotheses = (
                self._session.query(models.Endpoint).filter(models.Endpoint.hypothesis_id.isnot(None)).count()
            )
            return {
                "total": total,
                "with_endpoints": with_endpoints,
                "endpoints": endpoints,
                "with_hypotheses": with_hypotheses,
            }
        except Exception as e:
            logger.warning("Failed to get target summary: %s", e)
            return {"total": 0, "with_endpoints": 0, "endpoints": 0, "with_hypotheses": 0}

    def _pipeline_summary(self) -> dict[str, Any]:
        try:
            last_scans = self._session.execute(
                "SELECT target_name, status, started_at FROM scan_runs ORDER BY started_at DESC LIMIT 3"
            ).fetchall()
            last_scan = str(last_scans[0][2])[:19] if last_scans else None
            return {
                "hypotheses_tested": self._session.query(models.Endpoint)
                .filter(models.Endpoint.hypothesis_id.isnot(None))
                .count(),
                "last_scan": last_scan,
            }
        except Exception:
            return {"hypotheses_tested": 0, "last_scan": None}

    def _findings_summary(self) -> dict[str, Any]:
        try:
            total = self._session.query(models.Finding).count()
            confirmed = self._session.query(models.Finding).filter(models.Finding.status == "confirmed").count()
            return {"total": total, "confirmed": confirmed}
        except Exception:
            return {"total": 0, "confirmed": 0}

    def _opportunity_summary(self) -> list[dict[str, str]]:
        try:
            newest_targets = self._session.query(models.Target).order_by(models.Target.created_at.desc()).limit(5).all()
            return [
                {
                    "name": t.name,
                    "description": f"Activo cargado ({t.domain or 'sin dominio'})",
                    "type": "target",
                }
                for t in newest_targets
            ]
        except Exception:
            return []

    def _priority_actions(self) -> list[str]:
        actions = []
        try:
            pending_hyps = self._session.query(models.Endpoint).filter(models.Endpoint.hypothesis_id.is_(None)).count()
            if pending_hyps > 0:
                actions.append(f"Generar hipótesis para {pending_hyps} endpoints sin procesar")
        except Exception:
            pass

        try:
            recent_targets = self._session.query(models.Target).order_by(models.Target.created_at.desc()).limit(3).all()
            for t in recent_targets:
                ep_count = self._session.query(models.Endpoint).filter(models.Endpoint.target_id == t.id).count()
                if ep_count == 0:
                    actions.append(f"Ejecutar recon en {t.name} ({t.domain})")
        except Exception:
            pass

        return actions[:5]
