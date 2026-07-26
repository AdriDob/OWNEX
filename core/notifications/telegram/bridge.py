"""EventBus → Telegram bridge — notificaciones automáticas inteligentes."""

from __future__ import annotations

import logging
from typing import Any

from core.notifications.telegram import get_telegram_bot

logger = logging.getLogger("orion.telegram.bridge")


# ── Event → Notification mapping ─────────────────────────────────────────

EVENT_PRIORITY: dict[str, str] = {
    # Critical — always notify
    "finding:confirmed": "high",
    "financial:payout_received": "high",
    "revenue:payout_recorded": "high",
    "system:error": "critical",
    "system:degraded": "high",
    "system:alert": "high",
    "hermes:security:blocked": "critical",
    "hermes:permission:required": "high",
    "execution:approval:requested": "high",
    "execution:workflow:failed": "high",
    "recovery:failed": "critical",
    "anomaly:detected": "high",
    # Normal — notify if enabled
    "finding:created": "info",
    "finding:status_changed": "info",
    "report:generated": "info",
    "report:accepted": "info",
    "report:rejected": "info",
    "discovery:completed": "info",
    "opportunity:found": "info",
    "opportunity:updated": "info",
    "quick_win:detected": "info",
    "financial:payout_confirmed": "info",
    "revenue:report_submitted": "info",
    "revenue:sync_completed": "info",
    "revenue:status_changed": "info",
    "copilot:recommendation": "info",
    "copilot:decision": "info",
    "execution:workflow:completed": "info",
    "execution:approval:approved": "info",
    "execution:approval:rejected": "info",
    "hermes:action:completed": "info",
    "hermes:action:failed": "info",
    "recovery:success": "info",
    "recovery:started": "info",
    "f1:alert": "info",
    "f1:question": "info",
    # Low — digest only
    "finding:*": "low",
    "target:created": "low",
    "hermes:action:started": "low",
    "execution:workflow:started": "low",
    "execution:checkpoint:saved": "low",
    "f1:daily_briefing": "low",
    "f1:status": "low",
    "command:executed": "low",
    "cli:command:executed": "low",
}

# Event types that should always be notified (regardless of auto_notify setting)
ALWAYS_NOTIFY = {
    "system:error",
    "system:alert",
    "system:degraded",
    "hermes:security:blocked",
    "recovery:failed",
    "anomaly:detected",
    "execution:approval:requested",
}

# Events that are grouped for digest
DIGEST_EVENTS = {
    "finding:*",
    "target:created",
    "hermes:action:started",
    "command:executed",
    "cli:command:executed",
    "f1:status",
}


def get_priority(event_type: str) -> str:
    """Get priority for an event type, with wildcard fallback."""
    if event_type in EVENT_PRIORITY:
        return EVENT_PRIORITY[event_type]
    prefix = event_type.split(":")[0] + ":*"
    if prefix in EVENT_PRIORITY:
        return EVENT_PRIORITY[prefix]
    return "info"


def should_always_notify(event_type: str) -> bool:
    return event_type in ALWAYS_NOTIFY


def is_digest_event(event_type: str) -> bool:
    if event_type in DIGEST_EVENTS:
        return True
    prefix = event_type.split(":")[0] + ":*"
    return prefix in DIGEST_EVENTS


# ── Event formatters ─────────────────────────────────────────────────────


def _fmt_finding(event_type: str, data: dict[str, Any]) -> str:
    sev = data.get("severity", "medium")
    sev_icon = "🔴" if sev == "critical" else "🟠" if sev == "high" else "🟡" if sev == "medium" else "🔵"
    if event_type == "finding:created":
        return f"{sev_icon} *Nuevo hallazgo*: {data.get('title', 'unknown')} ({sev})"
    if event_type == "finding:confirmed":
        return f"✅ *Hallazgo confirmado*: {data.get('title', 'unknown')} — ${data.get('potential_payout', 0):,.0f}"
    if event_type == "finding:status_changed":
        old = data.get("old_status", "?")
        new = data.get("new_status", "?")
        return f"📋 *Hallazgo actualizado*: {data.get('title', 'unknown')} ({old} → {new})"
    return f"📋 {data.get('title', 'unknown')}"


def _fmt_report(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "report:generated":
        return f"📄 *Reporte generado*: {data.get('title', data.get('vulnerability', 'unknown'))}"
    if event_type == "report:accepted":
        payout = data.get("payout", data.get("amount", 0))
        return f"💰 *Reporte ACEPTADO* — ${payout:,.0f} 🎉"
    if event_type == "report:rejected":
        return f"❌ *Reporte rechazado*: {data.get('reason', 'sin motivo')}"
    return "📄"


def _fmt_revenue(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "revenue:payout_recorded":
        return f"💰 *Pago registrado*: ${data.get('amount', 0):,.0f} — {data.get('platform', '?')}"
    if event_type == "revenue:report_submitted":
        return f"📤 *Reporte enviado* a {data.get('platform', '?')}"
    if event_type == "revenue:status_changed":
        return f"📋 *Estado actualizado*: {data.get('title', '?')} → {data.get('status', '?')}"
    return "💰"


def _fmt_system(event_type: str, data: dict[str, Any]) -> str:
    msg = data.get("message", data.get("error", ""))
    if event_type == "system:error":
        return f"🚨 *Error del sistema*\n{msg[:200]}"
    if event_type == "system:degraded":
        return f"⚠️ *Sistema degradado*\n{msg[:200]}"
    if event_type == "system:alert":
        return f"🔔 *Alerta*\n{msg[:200]}"
    if event_type == "anomaly:detected":
        return f"🕵️ *Anomalía detectada*\n{data.get('description', msg)[:200]}"
    return "🔔"


def _fmt_opportunity(event_type: str, data: dict[str, Any]) -> str:
    score = data.get("score", data.get("opportunity_score", "?"))
    return f"🎯 *Oportunidad*: {data.get('title', data.get('name', '?'))} (score: {score})"


def _fmt_execution(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "execution:approval:requested":
        return f"✋ *Aprobación requerida*: {data.get('reason', data.get('title', '?'))}"
    if event_type == "execution:workflow:failed":
        return f"💥 *Workflow falló*: {data.get('name', data.get('workflow_name', '?'))}"
    if event_type == "execution:workflow:completed":
        return f"✅ *Workflow completado*: {data.get('name', data.get('workflow_name', '?'))}"
    return "⚙️"


def _fmt_hermes(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "hermes:security:blocked":
        return f"🛡️ *Hermes: Acción bloqueada*\n{data.get('reason', data.get('command', '?'))[:200]}"
    if event_type == "hermes:permission:required":
        return f"🔑 *Hermes: Permiso requerido*\n{data.get('command', '?')}"
    if event_type == "hermes:action:completed":
        return f"✅ *Hermes: {data.get('command', 'acción')}* completado"
    if event_type == "hermes:action:failed":
        return f"❌ *Hermes: {data.get('command', 'acción')}* falló\n{data.get('error', '')[:200]}"
    return "🤖"


def _fmt_recovery(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "recovery:failed":
        return f"🚨 *Recuperación falló*: {data.get('reason', data.get('error', '?'))[:200]}"
    if event_type == "recovery:success":
        return f"🔄 *Recuperación exitosa*: {data.get('message', 'sistema restaurado')}"
    if event_type == "recovery:started":
        return f"🔄 *Recuperación iniciada*: {data.get('reason', '?')}"
    return "🔄"


def _fmt_f1(event_type: str, data: dict[str, Any]) -> str:
    msg = data.get("message", data.get("text", ""))
    if event_type == "f1:alert":
        return f"🔔 *F1 Alerta*\n{msg[:200]}"
    if event_type == "f1:question":
        return f"❓ *F1 Consulta*\n{msg[:200]}"
    return "📋"


def _fmt_financial(event_type: str, data: dict[str, Any]) -> str:
    if event_type == "financial:payout_received":
        return f"💰 *Pago recibido*: ${data.get('amount', 0):,.0f}"
    return "💳"


def format_event(event_type: str, data: dict[str, Any]) -> str:
    """Format an event into a Telegram message string."""
    category = event_type.split(":")[0]
    formatters = {
        "finding": _fmt_finding,
        "report": _fmt_report,
        "revenue": _fmt_revenue,
        "system": _fmt_system,
        "opportunity": _fmt_opportunity,
        "execution": _fmt_execution,
        "hermes": _fmt_hermes,
        "recovery": _fmt_recovery,
        "f1": _fmt_f1,
        "financial": _fmt_financial,
    }
    fmt = formatters.get(category)
    if fmt:
        return fmt(event_type, data)
    return f"📬 *{event_type}*"


# ── Digest accumulator ───────────────────────────────────────────────────


class DigestAccumulator:
    """Accumula eventos de baja prioridad para enviar como digest periódico."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def add(self, event_type: str, data: dict[str, Any]) -> None:
        key = f"{event_type}:{data.get('id', data.get('title', ''))}"
        if key in self._seen:
            return
        self._seen.add(key)
        self._items.append({"event_type": event_type, "data": data, "text": format_event(event_type, data)})

    def pop(self) -> list[dict[str, Any]]:
        items = list(self._items)
        self._items.clear()
        self._seen.clear()
        return items

    @property
    def count(self) -> int:
        return len(self._items)


_DIGEST = DigestAccumulator()


# ── Bridge handler ───────────────────────────────────────────────────────


def handle_event(event_type: str, **data: Any) -> None:
    """EventBus handler: decide if/how to notify via Telegram."""
    bot = get_telegram_bot()
    if not bot.config.enabled:
        return

    priority = get_priority(event_type)
    auto_notify = bot.config.auto_notify

    # Always notify critical/high priority events
    if priority in ("critical", "high") or should_always_notify(event_type):
        text = format_event(event_type, data)
        bot.send_alert(title=text[:50], body=text, priority=priority)
        return

    # Auto-notify normal events only if enabled
    if auto_notify and priority == "info":
        text = format_event(event_type, data)
        bot.send(text)
        return

    # Low priority → digest
    if priority == "low" or is_digest_event(event_type):
        _DIGEST.add(event_type, data)


def send_digest() -> str | None:
    """Send accumulated digest, return message or None if empty."""
    items = _DIGEST.pop()
    if not items:
        return None
    bot = get_telegram_bot()
    if not bot.config.enabled:
        return None
    result = bot.send_digest(items)
    return "digest sent" if result.get("ok") else None
