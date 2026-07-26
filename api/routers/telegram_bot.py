"""Telegram Bot API — control y monitoreo del bot desde la web."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from core.notifications.telegram import TelegramConfig, get_telegram_bot, reset_telegram_bot
from core.notifications.telegram.handlers import handle_command

logger = logging.getLogger("orion.telegram.api")
router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.get("/status")
async def bot_status():
    """Estado actual del bot de Telegram."""
    bot = get_telegram_bot()
    return {"success": True, "config": bot.config.to_dict(), "polling": bot._polling}


@router.post("/configure")
async def configure_bot(data: dict[str, Any]):
    """Configurar el bot de Telegram."""
    config = TelegramConfig(
        token=data.get("token", ""),
        chat_id=data.get("chat_id", ""),
        mode=data.get("mode", "normal"),
        morning_briefing=data.get("morning_briefing", True),
        evening_briefing=data.get("evening_briefing", True),
        auto_notify=data.get("auto_notify", True),
        enabled=data.get("enabled", False),
        allowed_usernames=data.get("allowed_usernames", ["adriel"]),
    )
    config.save()
    reset_telegram_bot(config)
    return {"success": True, "config": config.to_dict()}


@router.post("/send")
async def send_message(data: dict[str, Any]):
    """Enviar un mensaje por Telegram."""
    bot = get_telegram_bot()
    text = data.get("text", "")
    if not text:
        return {"success": False, "error": "text is required"}
    result = bot.send(text)
    return {"success": result.get("ok", False), "result": result}


@router.post("/send-alert")
async def send_alert(data: dict[str, Any]):
    """Enviar una alerta por Telegram."""
    bot = get_telegram_bot()
    result = bot.send_alert(
        title=data.get("title", "Alerta"),
        body=data.get("body", ""),
        priority=data.get("priority", "info"),
    )
    return {"success": result.get("ok", False), "result": result}


@router.post("/handle")
async def handle_text(data: dict[str, Any]):
    """Procesar un comando de texto como si viniera de Telegram."""
    text = data.get("text", "")
    level_str = data.get("level", "summary")
    from core.notifications.hierarchy import InfoLevel

    level_map = {"summary": InfoLevel.SUMMARY, "details": InfoLevel.DETAILS, "debug": InfoLevel.DEBUG}
    level = level_map.get(level_str, InfoLevel.SUMMARY)
    response = handle_command(text, level=level)
    return {"success": bool(response), "response": response or "no response"}


@router.post("/poll")
async def poll_telegram(count: int = 5):
    """Hacer poll de mensajes de Telegram (procesa hasta N mensajes)."""
    bot = get_telegram_bot()
    if not bot.config.is_ready:
        return {"success": False, "error": "bot not configured"}
    processed = 0
    for _ in range(count):
        msgs = bot.poll_once()
        for msg in msgs:
            response = bot.handle_message(msg)
            if response:
                chat_id = str(msg.get("chat", {}).get("id", ""))
                bot.send(response, chat_id=chat_id)
            processed += 1
        if not msgs:
            break
    return {"success": True, "processed": processed}


@router.post("/start-polling")
async def start_polling():
    """Iniciar polling loop en background (corre en el event loop de FastAPI)."""
    import asyncio

    bot = get_telegram_bot()
    if not bot.config.is_ready:
        return {"success": False, "error": "bot not configured"}
    if bot._polling:
        return {"success": False, "error": "already polling"}

    async def _poll():
        while bot._polling:
            msgs = bot.poll_once()
            for msg in msgs:
                response = bot.handle_message(msg)
                if response:
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    bot.send(response, chat_id=chat_id)
            await asyncio.sleep(2)

    bot._polling = True
    asyncio.create_task(_poll())
    return {"success": True, "message": "polling started"}


@router.post("/stop-polling")
async def stop_polling():
    """Detener polling loop."""
    bot = get_telegram_bot()
    bot.stop()
    return {"success": True, "message": "polling stopped"}
