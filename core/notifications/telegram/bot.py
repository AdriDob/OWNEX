"""Telegram Bot — interfaz principal vía Telegram usando raw API."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from core.notifications.hierarchy import InfoLevel
from core.notifications.telegram.config import TelegramConfig

logger = logging.getLogger("orion.telegram.bot")

API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramBot:
    """Bot de Telegram usando API REST directa (sin dependencias pesadas)."""

    def __init__(self, config: TelegramConfig | None = None) -> None:
        self._config = config or TelegramConfig.from_env()
        self._http = httpx.Client(timeout=15)
        self._level: InfoLevel = InfoLevel.SUMMARY
        self._last_update_id = 0
        self._polling = False
        self._pending_level: dict[int, InfoLevel] = {}  # chat_id -> level

    @property
    def config(self) -> TelegramConfig:
        return self._config

    @property
    def level(self) -> InfoLevel:
        return self._level

    @level.setter
    def level(self, value: InfoLevel) -> None:
        self._level = value

    # ── API calls ──

    def _api(self, method: str, **kwargs: Any) -> dict[str, Any]:
        if not self._config.token:
            return {"ok": False, "error": "token not configured"}
        url = API_BASE.format(token=self._config.token, method=method)
        try:
            resp = self._http.post(url, json=kwargs, timeout=15)
            return resp.json()
        except Exception as e:
            logger.error("Telegram API error: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Send message ──

    def send(self, text: str, chat_id: str | None = None, parse_mode: str = "Markdown") -> dict[str, Any]:
        cid = chat_id or self._config.chat_id
        if not cid:
            return {"ok": False, "error": "chat_id not configured"}
        return self._api("sendMessage", chat_id=cid, text=text, parse_mode=parse_mode)

    def send_alert(self, title: str, body: str = "", priority: str = "info") -> dict[str, Any]:
        tag = "🚨" if priority == "critical" else "⚠️" if priority == "high" else "ℹ️"
        text = f"{tag} *{title}*" + (f"\n{body}" if body else "")
        return self.send(text)

    def send_digest(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            return {"ok": True, "result": "no items"}
        lines = ["📬 *Resumen de notificaciones*"]
        for item in items:
            emoji = item.get("emoji", "•")
            title = item.get("title", "")
            lines.append(f"\n{emoji} {title}")
        return self.send("\n".join(lines))

    def send_error(self, error_text: str) -> dict[str, Any]:
        return self.send(f"❌ *Error*\n{error_text}")

    # ── Polling (long-poll for incoming commands) ──

    def poll_once(self) -> list[dict[str, Any]]:
        if not self._config.token:
            return []
        url = API_BASE.format(token=self._config.token, method="getUpdates")
        try:
            resp = self._http.post(
                url,
                json={
                    "offset": self._last_update_id + 1,
                    "timeout": 10,
                    "allowed_updates": ["message"],
                },
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            logger.debug("Poll error: %s", e)
            return []

        messages = []
        for update in data.get("result", []):
            self._last_update_id = update.get("update_id", 0)
            msg = update.get("message", {})
            if msg:
                messages.append(msg)
        return messages

    # ── Handle incoming commands ──

    def handle_message(self, msg: dict[str, Any]) -> str | None:
        text = (msg.get("text") or "").strip().lower()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text:
            return None

        # Parse level suffix
        level = self._parse_level(text)

        from core.notifications.telegram.handlers import handle_command

        response = handle_command(text, level, chat_id)
        return response

    def _parse_level(self, text: str) -> InfoLevel:
        text_lower = text.lower()
        if text_lower.endswith(" todo") or text_lower.endswith(" debug") or text_lower == "/todo":
            return InfoLevel.DEBUG
        if any(text_lower.endswith(s) for s in (" mas", " más", " detalles", " detail", " vermas", " /vermas")):
            return InfoLevel.DETAILS
        return InfoLevel.SUMMARY

    # ── Polling loop ──

    def poll_loop(self, iterations: int = 0) -> int:
        """Poll for messages. iterations=0 means infinite."""
        self._polling = True
        count = 0
        try:
            while self._polling:
                msgs = self.poll_once()
                for msg in msgs:
                    response = self.handle_message(msg)
                    if response:
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        self.send(response, chat_id=chat_id)
                    count += 1
                if iterations and count >= iterations:
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            self._polling = False
        return count

    def stop(self) -> None:
        self._polling = False

    # ── Lifecycle ──

    def close(self) -> None:
        self._http.close()


_BOT: TelegramBot | None = None


def get_telegram_bot() -> TelegramBot:
    global _BOT
    if _BOT is None:
        _BOT = TelegramBot()
    return _BOT


def reset_telegram_bot(config: TelegramConfig | None = None) -> TelegramBot:
    global _BOT
    if _BOT:
        _BOT.close()
    _BOT = TelegramBot(config)
    return _BOT
