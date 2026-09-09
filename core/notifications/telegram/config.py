"""Configuración del bot de Telegram."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TelegramConfig:
    """Configuración del bot.

    Para obtener el token: hablá con @BotFather en Telegram, creá un bot y copiá el token.
    Para obtener el chat_id: enviale un mensaje al bot y visitá https://api.telegram.org/bot<TOKEN>/getUpdates
    """

    token: str = ""
    chat_id: str = ""
    mode: str = "normal"  # normal | silencioso | detallado
    morning_briefing: bool = True
    evening_briefing: bool = True
    auto_notify: bool = True
    enabled: bool = False
    allowed_usernames: list[str] = field(default_factory=lambda: ["adriel"])

    @property
    def is_ready(self) -> bool:
        return bool(self.token and self.chat_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": "***" if self.token else "",
            "chat_id": self.chat_id or "",
            "mode": self.mode,
            "morning_briefing": self.morning_briefing,
            "evening_briefing": self.evening_briefing,
            "auto_notify": self.auto_notify,
            "enabled": self.enabled,
            "is_ready": self.is_ready,
            "allowed_usernames": self.allowed_usernames,
        }

    @classmethod
    def from_env(cls) -> TelegramConfig:
        """Carga configuración desde variables de entorno."""
        import os

        return cls(
            token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            mode=os.environ.get("TELEGRAM_MODE", "normal"),
            enabled=bool(os.environ.get("TELEGRAM_ENABLED", "")),
        )

    @classmethod
    def from_file(cls, path: str | Path = "~/.orion/telegram_config.json") -> TelegramConfig:
        """Carga configuración desde archivo JSON."""
        path = Path(path).expanduser()
        if not path.exists():
            return cls()
        try:
            import json

            data = json.loads(path.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()

    def save(self, path: str | Path = "~/.orion/telegram_config.json") -> None:
        """Guarda configuración a archivo JSON."""
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        import json

        path.write_text(json.dumps(self.to_dict(), indent=2))
