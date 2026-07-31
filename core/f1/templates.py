"""Plantillas en español para el asistente F1 — lenguaje natural y amigable."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def _hora_saludo() -> str:
    h = datetime.now(UTC).hour
    if h < 12:
        return "¡Buenos días"
    if h < 18:
        return "¡Buenas tardes"
    return "¡Buenas noches"


def saludo(nombre: str = "Adriel") -> str:
    return f"{_hora_saludo()}, {nombre} ⚡"


def resumen_diario(data: dict[str, Any]) -> str:
    targets = data.get("targets", 0)
    findings = data.get("findings", 0)
    confirmed = data.get("confirmed_findings", 0)
    revenue_hoy = data.get("revenue_today", 0)
    trades = data.get("trades_today", 0)
    return (
        f"📋 **Resumen del día**\n"
        f"• {targets} targets activos\n"
        f"• {findings} hallazgos ({confirmed} confirmados)\n"
        f"• ${revenue_hoy:.2f} generados hoy\n"
        f"• {trades} trades ejecutados"
    )


def estado_sistema(data: dict[str, Any]) -> str:
    health = data.get("health_score", 0)
    scheduler = "✅ activo" if data.get("scheduler_running") else "⏸ detenido"
    agents = data.get("active_agents", 0)
    pipelines = data.get("pipelines_active", 0)
    estado = "excelente" if health >= 90 else "bueno" if health >= 70 else "regular"
    return (
        f"🖥 **Estado del sistema**\n"
        f"• Salud: {health}/100 ({estado})\n"
        f"• Scheduler: {scheduler}\n"
        f"• {agents} agentes activos\n"
        f"• {pipelines} pipelines en ejecución"
    )


def oportunidad_alta(op: dict[str, Any]) -> str:
    name = op.get("name", "Oportunidad")
    score = op.get("score", 0)
    reward = op.get("estimated_reward", 0)
    domain = op.get("domain", "")
    return (
        f"🎯 **Oportunidad de alto valor detectada**\n"
        f"• {name} ({domain})\n"
        f"• Score: {score:.1f}/10\n"
        f"• Recompensa estimada: ${reward:.2f}"
    )


def alerta_critica(titulo: str, detalle: str) -> str:
    return f"🚨 **{titulo}**\n{detalle}"


def alerta_advertencia(titulo: str, detalle: str) -> str:
    return f"⚠️ **{titulo}**\n{detalle}"


def alerta_info(titulo: str, detalle: str) -> str:
    return f"ℹ️ **{titulo}**\n{detalle}"


def revenue_actual(data: dict[str, Any]) -> str:
    total = data.get("total_revenue", Decimal("0"))
    monthly = data.get("monthly_revenue", Decimal("0"))
    yearly = data.get("estimated_annual", Decimal("0"))
    bounty = data.get("bounty_revenue", Decimal("0"))
    trading = data.get("trading_revenue", Decimal("0"))
    return (
        f"💰 **Revenue Multiplier — Estado Financiero**\n"
        f"• Total acumulado: ${float(total):.2f}\n"
        f"• Este mes: ${float(monthly):.2f}\n"
        f"• Proyección anual: ${float(yearly):.2f}\n"
        f"• Bug Bounty: ${float(bounty):.2f}\n"
        f"• Crypto Trading: ${float(trading):.2f}"
    )


def caza_completada(target: str, findings: int, high_value: int) -> str:
    emoji = "🤑" if high_value > 0 else "📊"
    return f"{emoji} **Cacería completada**: {target}\n• {findings} hallazgos encontrados\n• {high_value} de alto valor"


def trade_ejecutado(pair: str, side: str, cantidad: Decimal, precio: Decimal) -> str:
    lado = "compra" if side == "buy" else "venta"
    return f"🔄 **Trade ejecutado**: {lado} {pair}\n• Cantidad: {float(cantidad):.4f}\n• Precio: ${float(precio):.4f}"


def max_revenue_resultado(resultado: dict[str, Any]) -> str:
    session = resultado.get("session_id", "—")
    mode = resultado.get("mode", "—")
    bounty = resultado.get("bounty", {})
    crypto = resultado.get("crypto", {})
    targets_proc = len(bounty.get("targets", []))
    signals = crypto.get("signals", 0)
    trades = crypto.get("trades_executed", 0)
    return (
        f"🚀 **MAX REVENUE MODE — Reporte**\n"
        f"• Sesión: {session}\n"
        f"• Modo: {mode}\n"
        f"• Targets escaneados: {targets_proc}\n"
        f"• Señales de trading: {signals}\n"
        f"• Trades ejecutados: {trades}"
    )


def sugerencias(acciones: list[str]) -> str:
    if not acciones:
        return ""
    lines = "\n".join(f"  → {a}" for a in acciones[:5])
    return f"💡 **Sugerencias**:\n{lines}"


def pie() -> str:
    return "¿Necesitás algo más, Adriel? Estoy acá para ayudarte."
