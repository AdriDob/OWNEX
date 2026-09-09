"""Renderizado de mensajes para Telegram con 3 niveles de detalle."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.notifications.hierarchy import InfoLevel


def status_l1(data: dict[str, Any]) -> str:
    targets = data.get("targets", 0)
    findings = data.get("findings", 0)
    confirmed = data.get("confirmed_findings", 0)
    health = data.get("health_score", 0)
    scheduler = "✅" if data.get("scheduler_running") else "❌"
    return (
        f"🖥 *ORION — Resumen*\n"
        f"Salud: {health}/100  |  Scheduler: {scheduler}\n"
        f"Targets: {targets}  |  Hallazgos: {findings} ({confirmed}✅)\n"
        f"Usá /vermas para más detalles"
    )


def status_l2(data: dict[str, Any]) -> str:
    base = status_l1(data)
    agents = data.get("active_agents", 0)
    pipelines = data.get("pipelines_active", 0)
    events = data.get("events_24h", 0)
    pending = data.get("pending_findings", 0)
    return (
        f"{base}\n\n"
        f"📊 *Detalles*\n"
        f"Agentes: {agents}  |  Pipelines: {pipelines}\n"
        f"Pendientes: {pending}  |  Eventos 24h: {events}"
    )


def status_l3(data: dict[str, Any]) -> str:
    import json

    return status_l2(data) + f"\n\n🔍 *Debug*\n```\n{json.dumps(data, indent=2, default=str)[:1000]}\n```"


def daily_l1(data: dict[str, Any]) -> str:
    targets = data.get("targets", 0)
    findings = data.get("findings", 0)
    confirmed = data.get("confirmed_findings", 0)
    revenue = data.get("revenue_today", 0)
    trades = data.get("trades_today", 0)
    health = data.get("health_score", 0)
    estado = "🟢 excelente" if health >= 90 else "🟡 bueno" if health >= 70 else "🔴 regular"
    return (
        f"☀️ *Briefing Diario — {datetime.now(UTC).strftime('%d/%m/%Y')}*\n\n"
        f"📊 *Sistema* — Salud: {health}/100 ({estado})\n"
        f"🎯 *Targets*: {targets} activos\n"
        f"🔍 *Hallazgos*: {findings} total ({confirmed} confirmados)\n"
        f"💰 *Revenue*: ${revenue:.2f} hoy  |  {trades} trades"
    )


def daily_l2(data: dict[str, Any]) -> str:
    base = daily_l1(data)
    pending = data.get("pending_findings", 0)
    reports_pending = data.get("reports_pending", 0)
    reports_submitted = data.get("reports_submitted", 0)
    opps = data.get("opportunities", 0)
    agents = data.get("active_agents", 0)
    pipelines = data.get("pipelines_active", 0)
    return (
        f"{base}\n\n"
        f"📋 *Más detalles*\n"
        f"Pendientes: {pending} hallazgos, {reports_pending} reportes\n"
        f"Enviados: {reports_submitted} reportes\n"
        f"Oportunidades: {opps}  |  Agentes: {agents}  |  Pipelines: {pipelines}"
    )


def daily_l3(data: dict[str, Any]) -> str:
    import json

    return daily_l2(data) + f"\n\n🔍 *Debug*\n```\n{json.dumps(data, indent=2, default=str)[:1000]}\n```"


def revenue_l1(data: dict[str, Any]) -> str:
    total = data.get("total_revenue", 0)
    monthly = data.get("monthly_revenue", 0)
    yearly = data.get("estimated_annual", 0)
    return (
        f"💰 *Revenue Multiplier*\n"
        f"Total: ${float(total):.2f}\n"
        f"Este mes: ${float(monthly):.2f}\n"
        f"Proyección anual: ${float(yearly):.2f}"
    )


def revenue_l2(data: dict[str, Any]) -> str:
    base = revenue_l1(data)
    bounty = data.get("bounty_revenue", 0)
    trading = data.get("trading_revenue", 0)
    metrics = data.get("metrics", {})
    b = metrics.get("bounty", {})
    t = metrics.get("trading", {})
    return (
        f"{base}\n\n"
        f"📊 *Desglose*\n"
        f"Bug Bounty: ${float(bounty):.2f}\n"
        f"Crypto Trading: ${float(trading):.2f}\n\n"
        f"Hallazgos: {b.get('findings_total', 0)} "
        f"(críticos: {b.get('findings_critical', 0)})\n"
        f"Trades: {t.get('total_trades', 0)} "
        f"(win rate: {t.get('win_rate', 0)}%)"
    )


def hunt_l1(data: dict[str, Any], target: str = "") -> str:
    bounty = data.get("bounty", {})
    targets_proc = len(bounty.get("targets", []))
    findings = bounty.get("total_findings", 0)
    high = bounty.get("high_value_findings", 0)
    session = data.get("session_id", "")[:8]
    return (
        f"🎯 *Cacería completada* — sesión {session}\n"
        if not target
        else f"🎯 *Target escaneado*: {target}\n{targets_proc} targets • {findings} findings • {high} de alto valor"
    )


def trade_l1(data: dict[str, Any]) -> str:
    crypto = data.get("crypto", {})
    signals = crypto.get("signals", 0)
    executed = crypto.get("trades_executed", 0)
    errors = crypto.get("errors", 0)
    return f"📊 *Trading Pipeline*\nSeñales: {signals}  |  Ejecutados: {executed}  |  Errores: {errors}"


def max_revenue_l1(data: dict[str, Any]) -> str:
    session = data.get("session_id", "")[:8]
    mode = data.get("mode", "—")
    bounty = data.get("bounty", {})
    crypto = data.get("crypto", {})
    targets_proc = len(bounty.get("targets", []))
    total_findings = bounty.get("total_findings", 0)
    high_value = bounty.get("high_value_findings", 0)
    signals = crypto.get("signals", 0)
    trades = crypto.get("trades_executed", 0)
    return (
        f"🚀 *MAX REVENUE MODE* — sesión {session}\n"
        f"Modo: {mode}\n"
        f"🎯 Bounty: {targets_proc} targets, {total_findings} findings "
        f"({high_value} alto valor)\n"
        f"📊 Trading: {signals} señales, {trades} trades"
    )


def notification_alert(n: dict[str, Any]) -> str:
    emoji = n.get("emoji", "ℹ️")
    title = n.get("title", "")
    body = n.get("body", "")
    priority = n.get("priority", "info")
    tag = "🔴" if priority == "critical" else "🟡" if priority == "high" else "ℹ️"
    return f"{tag} {emoji} *{title}*\n{body}" if body else f"{tag} {emoji} *{title}*"


def config_status(cfg: dict[str, Any]) -> str:
    ready = cfg.get("is_ready", False)
    enabled = cfg.get("enabled", False)
    mode = cfg.get("mode", "normal")
    status = "✅ listo" if ready and enabled else "❌ no configurado"
    return (
        f"🤖 *Telegram Bot*\n"
        f"Estado: {status}\n"
        f"Modo: {mode}\n"
        f"Briefing mañana: {'✅' if cfg.get('morning_briefing') else '❌'}\n"
        f"Briefing noche: {'✅' if cfg.get('evening_briefing') else '❌'}\n"
        f"Notif. automáticas: {'✅' if cfg.get('auto_notify') else '❌'}"
    )


def help_text() -> str:
    return (
        "🤖 *ORION Bot — Comandos disponibles*\n\n"
        "/status — Resumen general del sistema\n"
        "/daily — Briefing del día\n"
        "/revenue — Estado financiero\n"
        "/hunt — Activar cacería\n"
        "/trade — Activar trading\n"
        "/max — MAX REVENUE MODE\n"
        "/health — Salud del sistema\n"
        "/vermas — Sube un nivel de detalle\n"
        "/todo — Modo debug (nivel 3)\n"
        "/config — Estado del bot\n"
        "/help — Esta ayuda\n\n"
        "Agregá `mas`, `detalles` o `todo` al final de cualquier comando "
        "para cambiar el nivel de detalle.\n"
        "Ej: `/status mas` o `/daily todo`"
    )


def render_by_level(base_l1: str, data: dict[str, Any], level: InfoLevel, l2_fn=None, l3_fn=None) -> str:
    if level == InfoLevel.SUMMARY:
        return base_l1
    if level == InfoLevel.DETAILS and l2_fn:
        return l2_fn(data)
    if level == InfoLevel.DEBUG and l3_fn:
        return l3_fn(data)
    return base_l1
