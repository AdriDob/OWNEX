"""Discord notification adapter — webhook-based."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from cores.env.config import get_config

logger = logging.getLogger("cateye.notifications.discord")


class DiscordAdapter:
    def __init__(self) -> None:
        cfg = get_config()
        self._webhook_url = cfg.discord_webhook_url or ""
        self._enabled = bool(self._webhook_url and self._webhook_url.startswith("https://discord.com/api/webhooks/"))

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def send(self, title: str, message: str, priority: str = "medium", metadata: dict[str, Any] | None = None) -> bool:
        if not self._enabled:
            logger.debug("Discord disabled — set CATEYE_DISCORD_WEBHOOK_URL")
            return False

        color_map = {"low": 0x6B7280, "medium": 0xF59E0B, "high": 0xEF4444, "critical": 0x7C3AED}
        color = color_map.get(priority, 0x6B7280)

        embed = {
            "title": str(title)[:256],
            "description": str(message)[:2048],
            "color": color,
            "footer": {"text": f"ORION · {priority}"},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        payload = {
            "username": "ORION",
            "embeds": [embed],
        }

        try:
            with httpx.Client() as client:
                resp = client.post(self._webhook_url, json=payload, timeout=15)
                if resp.is_success:
                    logger.info("Discord sent: %s", title)
                    return True
                logger.warning("Discord send failed: %s — %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.warning("Discord request error: %s", exc)
            return False


_DISCORD: DiscordAdapter | None = None


def get_discord_adapter() -> DiscordAdapter:
    global _DISCORD
    if _DISCORD is None:
        _DISCORD = DiscordAdapter()
    return _DISCORD
