"""OWNEX OMEGA Config — single source of truth for all environment configuration.

Centralizes ALL environment variable reading with defaults, type coercion,
and backward-compatible CATEYE_* fallbacks. Used by desktop, API, scripts,
and service wrappers.

Usage:
    from cores.env.config import OWNEXConfig
    cfg = OWNEXConfig()
    port = cfg.port

Migration note:
    CATEYE_* env vars are accepted with a deprecation warning but will be
    removed in a future release. Use OWNEX_* equivalents.
"""

from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("ownex.config")


def _env(name: str, default: str, legacy_name: str | None = None) -> str:
    """Read env var with OWNEX_ prefix, with optional legacy CATEYE_ fallback."""
    val = os.environ.get(name)
    if val is not None:
        return val
    if legacy_name:
        legacy = os.environ.get(legacy_name)
        if legacy is not None:
            warnings.warn(
                f"{legacy_name} is deprecated, use {name} instead",
                DeprecationWarning,
                stacklevel=3,
            )
            return legacy
    return default


def _env_int(name: str, default: int, legacy_name: str | None = None) -> int:
    return int(_env(name, str(default), legacy_name))


def _env_bool(name: str, *, legacy_name: str | None = None) -> bool:
    return _env(name, "0", legacy_name) == "1"


def _env_path(name: str, default: Path, legacy_name: str | None = None) -> Path:
    return Path(_env(name, str(default), legacy_name))


@dataclass(frozen=True)
class OWNEXConfig:
    # ── Server ──
    port: int = field(default_factory=lambda: _env_int("OWNEX_PORT", 8000, "CATEYE_PORT"))
    host: str = field(default_factory=lambda: _env("OWNEX_HOST", "127.0.0.1"))

    # ── Mode ──
    desktop: bool = field(default_factory=lambda: _env_bool("OWNEX_DESKTOP", legacy_name="CATEYE_DESKTOP"))
    debug: bool = field(default_factory=lambda: _env_bool("OWNEX_DEBUG", legacy_name="CATEYE_DEBUG"))
    build_env: str = field(default_factory=lambda: _env("OWNEX_BUILD_ENV", "production"))

    # ── Logging ──
    log_level: str = field(default_factory=lambda: _env("OWNEX_LOG_LEVEL", "INFO"))
    auth_secret: str = field(default_factory=lambda: _env("OWNEX_AUTH_SECRET", "", "CATEYE_AUTH_SECRET"))

    # ── Paths ──
    base_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_BASE_DIR",
            Path(__file__).resolve().parent.parent.parent,
        )
    )
    data_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_DATA_DIR",
            Path.home() / ".local" / "share" / "OWNEX",
        )
    )
    config_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_CONFIG_DIR",
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "OWNEX",
        )
    )
    output_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_OUTPUT_DIR",
            Path.home() / ".local" / "share" / "OWNEX" / "output",
            "CATEYE_OUTPUT_DIR",
        )
    )
    frontend_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_FRONTEND_DIR",
            Path(__file__).resolve().parent.parent.parent / "frontend",
        )
    )
    frontend_dist_dir: Path = field(
        default_factory=lambda: _env_path(
            "OWNEX_FRONTEND_DIST_DIR",
            Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        )
    )
    disable_frontend: bool = field(default_factory=lambda: _env_bool("OWNEX_DISABLE_FRONTEND"))
    no_browser: bool = field(default_factory=lambda: _env_bool("OWNEX_NO_BROWSER"))

    # ── Database ──
    database_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            f"sqlite:///{Path.home() / '.local' / 'share' / 'OWNEX' / 'database' / 'ownex.db'}",
        )
    )

    # ── Scanning ──
    scan_interval: int = field(default_factory=lambda: _env_int("OWNEX_SCAN_INTERVAL", 30))
    scan_mode: str = field(default_factory=lambda: _env("OWNEX_SCAN_MODE", "DEEP"))

    # ── Desktop / Recovery ──
    max_restart_retries: int = field(default_factory=lambda: _env_int("OWNEX_MAX_RESTART_RETRIES", 3))
    health_check_interval: int = field(default_factory=lambda: _env_int("OWNEX_HEALTH_CHECK_INTERVAL", 10))
    safe_mode: bool = field(default_factory=lambda: _env_bool("OWNEX_SAFE_MODE"))

    # ── Demo ──
    demo: bool = field(default_factory=lambda: _env_bool("OWNEX_DEMO"))
    backend: str = field(default_factory=lambda: _env("OWNEX_BACKEND", ""))

    # ── Performance ──
    cache_size: int = field(default_factory=lambda: _env_int("OWNEX_CACHE_SIZE", 4096))

    # ── License ──
    license_secret: str = field(default_factory=lambda: _env("OWNEX_LICENSE_SECRET", "", "CATEYE_LICENSE_SECRET"))

    # ── Notifications ──
    smtp_host: str = field(default_factory=lambda: _env("OWNEX_SMTP_HOST", "", "CATEYE_SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: _env_int("OWNEX_SMTP_PORT", 587, "CATEYE_SMTP_PORT"))
    smtp_user: str = field(default_factory=lambda: _env("OWNEX_SMTP_USER", "", "CATEYE_SMTP_USER"))
    smtp_password: str = field(default_factory=lambda: _env("OWNEX_SMTP_PASSWORD", "", "CATEYE_SMTP_PASSWORD"))
    smtp_from: str = field(default_factory=lambda: _env("OWNEX_SMTP_FROM", "", "CATEYE_SMTP_FROM"))
    notification_email: str = field(
        default_factory=lambda: _env("OWNEX_NOTIFICATION_EMAIL", "", "CATEYE_NOTIFICATION_EMAIL")
    )
    twilio_account_sid: str = field(default_factory=lambda: _env("OWNEX_TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = field(default_factory=lambda: _env("OWNEX_TWILIO_AUTH_TOKEN", ""))
    twilio_whatsapp_from: str = field(default_factory=lambda: _env("OWNEX_TWILIO_WHATSAPP_FROM", "14155238886"))
    notification_whatsapp_to: str = field(default_factory=lambda: _env("OWNEX_NOTIFICATION_WHATSAPP_TO", ""))
    gmail_client_id: str = field(default_factory=lambda: _env("OWNEX_GMAIL_CLIENT_ID", ""))
    gmail_client_secret: str = field(default_factory=lambda: _env("OWNEX_GMAIL_CLIENT_SECRET", ""))
    gmail_refresh_token: str = field(default_factory=lambda: _env("OWNEX_GMAIL_REFRESH_TOKEN", ""))
    gmail_from: str = field(default_factory=lambda: _env("OWNEX_GMAIL_FROM", ""))
    fcm_server_key: str = field(default_factory=lambda: _env("OWNEX_FCM_SERVER_KEY", "", "CATEYE_FCM_SERVER_KEY"))
    fcm_project_id: str = field(default_factory=lambda: _env("OWNEX_FCM_PROJECT_ID", "", "CATEYE_FCM_PROJECT_ID"))
    discord_webhook_url: str = field(default_factory=lambda: _env("OWNEX_DISCORD_WEBHOOK_URL", ""))

    # ── Test flags ──
    smoke_test: bool = field(default_factory=lambda: _env_bool("OWNEX_SMOKE_TEST"))
    portable_test: bool = field(default_factory=lambda: _env_bool("OWNEX_PORTABLE_TEST"))
    installer_test: bool = field(default_factory=lambda: _env_bool("OWNEX_INSTALLER_TEST"))

    # ── Legacy ──
    memory_consume: int = field(default_factory=lambda: _env_int("OWNEX_MEMORY_CONSUME", 1, "CATEYE_MEMORY_CONSUME"))

    @property
    def is_production(self) -> bool:
        return self.build_env == "production"


# Backward-compatible alias (deprecated)
EnvConfig = OWNEXConfig

_CONFIG_INSTANCE: OWNEXConfig | None = None


def get_config() -> OWNEXConfig:
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = OWNEXConfig()
    return _CONFIG_INSTANCE