"""Manejadores de comandos de Telegram."""

from __future__ import annotations

import logging
from typing import Any

from core.notifications.hierarchy import InfoLevel
from core.notifications.telegram import renderer as _r  # noqa: N812

logger = logging.getLogger("orion.telegram.handlers")


def handle_command(text: str, level: InfoLevel = InfoLevel.SUMMARY, chat_id: str = "") -> str | None:
    """Procesa un comando de texto y retorna la respuesta."""
    cmd = _extract_command(text)

    if cmd in ("/start", "/help"):
        return _r.help_text()

    if cmd == "/status":
        return _do_status(level)

    if cmd == "/daily":
        return _do_daily(level)

    if cmd == "/revenue":
        return _do_revenue(level)

    if cmd == "/hunt":
        return _do_hunt()

    if cmd == "/trade":
        return _do_trade()

    if cmd == "/max":
        return _do_max()

    if cmd == "/health":
        return _do_health(level)

    if cmd == "/config":
        return _do_config()

    if cmd in ("/vermas", "mas", "más", "detalles", "detail"):
        return _do_status(InfoLevel.DETAILS)

    if cmd in ("/todo", "debug", "todo"):
        return _do_status(InfoLevel.DEBUG)

    if cmd.startswith("/"):
        return f"❌ Comando no reconocido: {cmd}\nUsá /help para ver los disponibles."

    return None


def _extract_command(text: str) -> str:
    text = text.strip().lower()
    # Remove level suffix and extract base command
    for suffix in (" todo", " debug", " mas", " más", " detalles", " detail", " vermas"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text.strip()


def _gather_status_data() -> dict[str, Any]:
    data: dict[str, Any] = {
        "targets": 0,
        "findings": 0,
        "confirmed_findings": 0,
        "pending_findings": 0,
        "health_score": 0,
        "scheduler_running": False,
        "active_agents": 0,
        "pipelines_active": 0,
        "events_24h": 0,
    }
    try:
        from fastapi.testclient import TestClient

        from api.main import app

        c = TestClient(app)
        r = c.get("/api/system/status")
        if r.status_code == 200:
            d = r.json()
            data["health_score"] = d.get("health_score", 0)
            data["scheduler_running"] = d.get("scheduler", {}).get("running", False)
            data["active_agents"] = d.get("agents", 0)
            data["pipelines_active"] = d.get("pipelines", 0)
            data["events_24h"] = d.get("events_24h", 0)
        r = c.get("/api/overview")
        if r.status_code == 200:
            d = r.json()
            data["targets"] = d.get("total_targets", 0)
            data["findings"] = d.get("total_findings", 0)
            data["confirmed_findings"] = d.get("confirmed_findings", 0)
            data["pending_findings"] = max(0, data["findings"] - data["confirmed_findings"])
    except Exception:
        logger.debug("Could not gather status data")
    return data


def _gather_daily_data() -> dict[str, Any]:
    data = _gather_status_data()
    try:
        from fastapi.testclient import TestClient

        from api.main import app

        c = TestClient(app)
        r = c.get("/api/revenue-multiplier/metrics")
        if r.status_code == 200:
            m = r.json().get("metrics", {})
            rev = m.get("revenue", {})
            data["revenue_today"] = float(rev.get("24h", "0"))
            data["trades_today"] = m.get("trading", {}).get("total_trades", 0)
    except Exception:
        pass
    data["suggestions"] = _build_suggestions(data)
    return data


def _gather_revenue_data() -> dict[str, Any]:
    data: dict[str, Any] = {
        "total_revenue": 0,
        "monthly_revenue": 0,
        "estimated_annual": 0,
        "bounty_revenue": 0,
        "trading_revenue": 0,
        "metrics": {},
    }
    try:
        from core.revenue_multiplier import get_revenue_multiplier

        rm = get_revenue_multiplier()
        metrics = rm.metrics.to_dict()
        rev = metrics.get("revenue", {})
        data.update(
            {
                "total_revenue": sum(
                    float(v)
                    for v in rev.values()
                    if isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit()
                ),
                "monthly_revenue": float(rev.get("30d", "0")),
                "estimated_annual": float(rev.get("estimated_annual", "0")),
                "bounty_revenue": 0,
                "trading_revenue": 0,
                "metrics": metrics,
            }
        )
    except Exception:
        logger.debug("Could not gather revenue data")
    return data


def _run_max() -> dict[str, Any]:
    try:
        from core.revenue_multiplier import RevenueMultiplierConfig, RevenueMultiplierOrchestrator

        cfg = RevenueMultiplierConfig(
            max_concurrent_tools=4,
            max_concurrent_trades=3,
            max_daily_bounty_targets=10,
            auto_report_enabled=True,
            auto_trade_enabled=True,
        )
        engine = RevenueMultiplierOrchestrator(cfg)
        return engine.activate_max_revenue_mode()
    except Exception as e:
        logger.exception("Max revenue failed")
        return {"error": str(e)}


def _build_suggestions(data: dict[str, Any]) -> list[str]:
    s = []
    if data.get("pending_findings", 0) > 5:
        s.append(f"Tenés {data['pending_findings']} findings sin validar")
    if not data.get("scheduler_running"):
        s.append("El scheduler no está corriendo")
    if not s and data.get("targets", 0) == 0:
        s.append("No hay targets — agregá uno para empezar")
    if not s:
        s.append("Todo en orden — sistema funcionando")
    return s


def _do_status(level: InfoLevel) -> str:
    data = _gather_status_data()
    if level == InfoLevel.SUMMARY:
        return _r.status_l1(data)
    if level == InfoLevel.DETAILS:
        return _r.status_l2(data)
    return _r.status_l3(data)


def _do_daily(level: InfoLevel) -> str:
    data = _gather_daily_data()
    if level == InfoLevel.SUMMARY:
        return _r.daily_l1(data)
    if level == InfoLevel.DETAILS:
        return _r.daily_l2(data)
    return _r.daily_l3(data)


def _do_revenue(level: InfoLevel) -> str:
    data = _gather_revenue_data()
    if level == InfoLevel.SUMMARY:
        return _r.revenue_l1(data)
    if level == InfoLevel.DETAILS:
        return _r.revenue_l2(data)
    # L3 for revenue = same as L2 + debug
    return _r.revenue_l2(data) + f"\n\n🔍 Debug:\n{data}"


def _do_hunt() -> str:
    result = _run_max()
    return _r.hunt_l1(result)


def _do_trade() -> str:
    result = _run_max()
    return _r.trade_l1(result)


def _do_max() -> str:
    result = _run_max()
    return _r.max_revenue_l1(result)


def _do_health(level: InfoLevel) -> str:
    data = _gather_status_data()
    health = data.get("health_score", 0)
    estado = "excelente" if health >= 90 else "bueno" if health >= 70 else "regular"
    msg = (
        f"🩺 *Salud del sistema*\n"
        f"Score: {health}/100 ({estado})\n"
        f"Scheduler: {'✅' if data.get('scheduler_running') else '❌'}\n"
        f"Agentes: {data.get('active_agents', 0)}"
    )
    if level >= InfoLevel.DETAILS:
        msg += f"\nPipelines: {data.get('pipelines_active', 0)}"
        msg += f"\nEventos 24h: {data.get('events_24h', 0)}"
    return msg


def _do_config() -> str:
    from core.notifications.telegram.config import TelegramConfig

    cfg = TelegramConfig.from_file()
    return _r.config_status(cfg.to_dict())
