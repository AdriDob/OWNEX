"""ORION Command Center — comandos ultra simples para gestionar el sistema."""

from __future__ import annotations

import logging
from typing import Any

from core.f1 import templates  # noqa: N812
from core.f1.assistant import F1Assistant, get_f1
from core.orion_cli.models import CommandResult

logger = logging.getLogger("orion.cli")


class OrionCLI:
    """Centro de comando unificado. Cada comando retorna CommandResult listo para F1 o API."""

    def __init__(self, f1: F1Assistant | None = None) -> None:
        self._f1 = f1 or get_f1()

    # ── Help ──

    def help(self, command: str = "") -> CommandResult:
        cmds = {
            "status": "Estado general del sistema y métricas clave",
            "daily": "Briefing diario completo",
            "hunt": "Activar cacería de vulnerabilities",
            "trade": "Activar trading automatizado",
            "revenue": "Estado financiero y revenue actual",
            "max": "MAX REVENUE MODE — todo al máximo",
            "health": "Salud del sistema y servicios",
            "help": "Mostrar esta ayuda",
        }
        if command:
            desc = cmds.get(command, "Comando no encontrado")
            return CommandResult(command="help", summary=f"`orion {command}`: {desc}")
        lines = ["**ORION Command Center — Comandos disponibles:**"]
        for cmd, desc in cmds.items():
            lines.append(f"  • `orion {cmd}` — {desc}")
        lines.append("\nUsá `orion help <comando>` para más detalles.")
        lines.append("Agregá `--detalles` o `--debug` para más información.")
        return CommandResult(command="help", summary="\n".join(lines))

    # ── Status ──

    def status(self, detail: int = 1) -> CommandResult:
        try:
            data = self._gather_status_data()
            f1_msg = self._f1.status(data, detail=detail)
            result = CommandResult(
                command="status",
                summary=f1_msg if detail == 1 else "",
                details=f1_msg if detail >= 2 else "",
                debug=data,
            )
            suggestions = self._build_suggestions(data)
            if suggestions:
                result.suggestions = suggestions
                result.summary = f1_msg + "\n\n" + templates.sugerencias(suggestions)
            return result
        except Exception as e:
            logger.exception("status command failed")
            return CommandResult(success=False, command="status", error=str(e))

    # ── Daily Briefing ──

    def daily(self, detail: int = 1) -> CommandResult:
        try:
            data = self._gather_daily_data()
            if detail >= 3:
                result = CommandResult(
                    command="daily",
                    summary=self._f1.daily_briefing(data),
                    debug=data,
                )
            else:
                result = CommandResult(
                    command="daily",
                    summary=self._f1.daily_briefing(data),
                )
            result.suggestions = data.get("suggestions", [])
            return result
        except Exception as e:
            logger.exception("daily command failed")
            return CommandResult(success=False, command="daily", error=str(e))

    # ── Hunt ──

    def hunt(self, target: str = "", detail: int = 1) -> CommandResult:
        try:
            from core.revenue_multiplier import (
                RevenueMultiplierConfig,
                RevenueMultiplierOrchestrator,
            )

            cfg = RevenueMultiplierConfig(
                max_concurrent_tools=4,
                max_daily_bounty_targets=5,
                auto_report_enabled=True,
            )
            engine = RevenueMultiplierOrchestrator(cfg)
            result_data = engine.activate_max_revenue_mode()
            bounty = result_data.get("bounty", {})
            targets_proc = len(bounty.get("targets", []))
            total_findings = bounty.get("total_findings", 0)
            high_value = bounty.get("high_value_findings", 0)

            msg = templates.caza_completada(
                target or ("varios targets" if targets_proc > 0 else "N/A"),
                total_findings,
                high_value,
            )
            if detail >= 2:
                msg += "\n\n📋 Detalle:\n" + "\n".join(
                    f"  • {t.get('domain', '?')}: {t.get('findings', 0)} findings ({t.get('elapsed_s', 0)}s)"
                    for t in bounty.get("targets", [])
                )

            return CommandResult(
                command="hunt",
                summary=msg,
                details=msg if detail >= 2 else "",
                debug=result_data,
                suggestions=["Revisá los hallazgos en el dashboard", "Generá reportes para los findings confirmados"],
            )
        except Exception as e:
            logger.exception("hunt command failed")
            return CommandResult(success=False, command="hunt", error=str(e))

    # ── Trade ──

    def trade(self, detail: int = 1) -> CommandResult:
        try:
            from core.revenue_multiplier import (
                RevenueMultiplierConfig,
                RevenueMultiplierOrchestrator,
            )

            cfg = RevenueMultiplierConfig(
                max_concurrent_trades=3,
                auto_trade_enabled=True,
            )
            engine = RevenueMultiplierOrchestrator(cfg)
            result_data = engine.activate_max_revenue_mode()
            crypto = result_data.get("crypto", {})
            signals = crypto.get("signals", 0)
            executed = crypto.get("trades_executed", 0)
            errors = crypto.get("errors", 0)

            msg = (
                f"📊 **Trading Pipeline**\n"
                f"• {signals} señales encontradas\n"
                f"• {executed} trades ejecutados\n"
                f"• {errors} errores"
            )
            return CommandResult(
                command="trade",
                summary=msg,
                debug=result_data,
                suggestions=["Revisá las posiciones abiertas", "Ajustá los pares en la whitelist si es necesario"],
            )
        except Exception as e:
            logger.exception("trade command failed")
            return CommandResult(success=False, command="trade", error=str(e))

    # ── Revenue ──

    def revenue(self, detail: int = 1) -> CommandResult:
        try:
            from core.revenue_multiplier import get_revenue_multiplier

            rm = get_revenue_multiplier()
            metrics = rm.metrics.to_dict()
            data = {
                "total_revenue": sum(
                    float(v)
                    for v in metrics.get("revenue", {}).values()
                    if isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit()
                ),
                "monthly_revenue": float(metrics.get("revenue", {}).get("30d", "0")),
                "estimated_annual": float(metrics.get("revenue", {}).get("estimated_annual", "0")),
                "bounty_revenue": 0.0,
                "trading_revenue": 0.0,
                "metrics": metrics,
            }
            msg = self._f1.revenue(data, detail=detail)
            return CommandResult(
                command="revenue",
                summary=msg,
                debug=data,
                suggestions=["Activá MAX REVENUE MODE para maximizar", "Revisá el Revenue Dashboard completo"],
            )
        except Exception as e:
            logger.exception("revenue command failed")
            return CommandResult(success=False, command="revenue", error=str(e))

    # ── Max Revenue Mode ──

    def max_revenue(self, detail: int = 1) -> CommandResult:
        try:
            from core.revenue_multiplier import (
                RevenueMultiplierConfig,
                RevenueMultiplierOrchestrator,
            )

            cfg = RevenueMultiplierConfig(
                max_concurrent_tools=4,
                max_concurrent_trades=3,
                max_daily_bounty_targets=10,
                auto_report_enabled=True,
                auto_trade_enabled=True,
            )
            engine = RevenueMultiplierOrchestrator(cfg)
            result_data = engine.activate_max_revenue_mode()

            msg = self._f1.max_revenue_result(result_data)
            if detail >= 2:
                bounty = result_data.get("bounty", {})
                crypto = result_data.get("crypto", {})
                extra = []
                for t in bounty.get("targets", []):
                    extra.append(f"  • {t.get('domain', '?')}: {t.get('findings', 0)} en {t.get('elapsed_s', 0)}s")
                if extra:
                    msg += "\n\n📋 Targets:\n" + "\n".join(extra)
                msg += (
                    f"\n\n📊 Crypto: {crypto.get('signals', 0)} señales, {crypto.get('trades_executed', 0)} ejecutados"
                )

            return CommandResult(
                command="max",
                summary=msg,
                debug=result_data,
                suggestions=[
                    "Revisá los resultados en Revenue Dashboard",
                    "Verificá findings de alta confianza para reportes",
                ],
            )
        except Exception as e:
            logger.exception("max_revenue command failed")
            return CommandResult(success=False, command="max", error=str(e))

    # ── Health ──

    def health(self, detail: int = 1) -> CommandResult:
        try:
            data = self._gather_health_data()
            score = data.get("health_score", 0)
            estado = "excelente" if score >= 90 else "bueno" if score >= 70 else "regular"
            msg = (
                f"🩺 **Health Check — ORION**\n"
                f"• Score: {score}/100 ({estado})\n"
                f"• Scheduler: {'✅' if data.get('scheduler') else '❌'}\n"
                f"• EventBus: {'✅' if data.get('eventbus') else '❌'}\n"
                f"• Agentes activos: {data.get('agents', 0)}"
            )
            if detail >= 2:
                snap = data.get("snapshot", {})
                if snap:
                    msg += "\n\n📋 Snapshot:\n" + "\n".join(f"  • {k}: {v}" for k, v in snap.items())

            return CommandResult(
                command="health",
                summary=msg,
                debug=data,
                suggestions=[
                    "Si hay servicios caídos, revisá Health Center",
                    "Ejecutá `orion status` para ver el panorama completo",
                ],
            )
        except Exception as e:
            logger.exception("health command failed")
            return CommandResult(success=False, command="health", error=str(e))

    # ── Data gathering (best-effort, graceful degradation) ──

    def _gather_status_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "health_score": 0,
            "scheduler_running": False,
            "active_agents": 0,
            "pipelines_active": 0,
            "targets": 0,
            "findings": 0,
            "confirmed_findings": 0,
            "events_24h": 0,
        }
        try:
            from fastapi.testclient import TestClient

            from api.main import app

            c = TestClient(app)
            try:
                r = c.get("/api/system/status")
                if r.status_code == 200:
                    d = r.json()
                    data["health_score"] = d.get("health_score", 0)
                    data["scheduler_running"] = d.get("scheduler", {}).get("running", False)
                    data["active_agents"] = d.get("agents", 0)
                    data["pipelines_active"] = d.get("pipelines", 0)
                    data["events_24h"] = d.get("events_24h", 0)
            except Exception:
                pass
            try:
                r = c.get("/api/overview")
                if r.status_code == 200:
                    d = r.json()
                    data["targets"] = d.get("total_targets", 0)
                    data["findings"] = d.get("total_findings", 0)
                    data["confirmed_findings"] = d.get("confirmed_findings", 0)
            except Exception:
                pass
        except Exception:
            logger.debug("Could not gather status data from API")
        return data

    def _gather_daily_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "targets": 0,
            "endpoints": 0,
            "findings": 0,
            "confirmed_findings": 0,
            "pending_findings": 0,
            "reports_pending": 0,
            "reports_submitted": 0,
            "opportunities": 0,
            "revenue_today": 0.0,
            "trades_today": 0,
            "health_score": 0,
            "scheduler_running": False,
            "active_agents": 0,
            "pipelines_active": 0,
            "bottlenecks": [],
            "suggestions": [],
            "events_24h": 0,
        }
        try:
            from fastapi.testclient import TestClient

            from api.main import app

            c = TestClient(app)
            try:
                r = c.get("/api/system/status")
                if r.status_code == 200:
                    d = r.json()
                    data["health_score"] = d.get("health_score", 0)
                    data["scheduler_running"] = d.get("scheduler", {}).get("running", False)
                    data["active_agents"] = d.get("agents", 0)
                    data["events_24h"] = d.get("events_24h", 0)
            except Exception:
                pass
            try:
                r = c.get("/api/overview")
                if r.status_code == 200:
                    d = r.json()
                    data["targets"] = d.get("total_targets", 0)
                    data["endpoints"] = d.get("total_endpoints", 0)
                    data["findings"] = d.get("total_findings", 0)
                    data["confirmed_findings"] = d.get("confirmed_findings", 0)
                    data["pending_findings"] = max(0, d.get("total_findings", 0) - d.get("confirmed_findings", 0))
            except Exception:
                pass
            try:
                r = c.get("/api/revenue-multiplier/metrics")
                if r.status_code == 200:
                    m = r.json().get("metrics", {})
                    rev = m.get("revenue", {})
                    data["revenue_today"] = float(rev.get("24h", "0"))
                    data["trades_today"] = m.get("trading", {}).get("total_trades", 0)
            except Exception:
                pass
            data["suggestions"] = self._build_suggestions(data)
        except Exception:
            logger.debug("Could not gather daily data from API")
        return data

    def _gather_health_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "health_score": 0,
            "scheduler": False,
            "eventbus": False,
            "agents": 0,
            "snapshot": {},
        }
        try:
            from fastapi.testclient import TestClient

            from api.main import app

            c = TestClient(app)
            try:
                r = c.get("/api/system/status")
                if r.status_code == 200:
                    d = r.json()
                    data["health_score"] = d.get("health_score", 0)
                    data["scheduler"] = d.get("scheduler", {}).get("running", False)
                    data["agents"] = d.get("agents", 0)
            except Exception:
                pass
        except Exception:
            logger.debug("Could not gather health data from API")
        return data

    def _build_suggestions(self, data: dict[str, Any]) -> list[str]:
        suggestions = []
        if data.get("pending_findings", 0) > 5:
            suggestions.append(f"Tenés {data['pending_findings']} findings sin validar")
        if not data.get("scheduler_running"):
            suggestions.append("El scheduler no está corriendo — activalo en Health Center")
        if data.get("opportunities", 0) > 3:
            suggestions.append(f"Revisá {data['opportunities']} oportunidades nuevas")
        if not suggestions and data.get("targets", 0) == 0:
            suggestions.append("No hay targets cargados — agregá uno para empezar")
        if not suggestions:
            suggestions.append("Todo en orden — sistema funcionando con normalidad")
        return suggestions


_CLI: OrionCLI | None = None


def get_cli() -> OrionCLI:
    global _CLI
    if _CLI is None:
        _CLI = OrionCLI()
    return _CLI
