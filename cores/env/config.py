"""CATEYEConfig — single source of truth for all environment configuration.

Centralizes ALL environment variable reading with defaults, type coercion,
and backward-compatible RASTRO_* fallbacks. Used by desktop, API, scripts,
and service wrappers.

Usage:
    from cores.env.config import CATEYEConfig
    cfg = CATEYEConfig()
    port = cfg.port

Migration note:
    RASTRO_* env vars are accepted with a deprecation warning but will be
    removed in a future release. Use CATEYE_* equivalents.
"""

from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("cateye.config")


def _env(name: str, default: str, legacy_name: str | None = None) -> str:
    """Read env var with CATEYE_ prefix, with optional legacy RASTRO_ fallback."""
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
class CATEYEConfig:
    # ── Server ──
    port: int = field(default_factory=lambda: _env_int("CATEYE_PORT", 8000))
    host: str = field(default_factory=lambda: _env("CATEYE_HOST", "127.0.0.1"))

    # ── Mode ──
    desktop: bool = field(default_factory=lambda: _env_bool("CATEYE_DESKTOP"))
    debug: bool = field(default_factory=lambda: _env_bool("CATEYE_DEBUG"))
    build_env: str = field(default_factory=lambda: _env("CATEYE_BUILD_ENV", "production"))

    # ── Logging ──
    log_level: str = field(default_factory=lambda: _env("CATEYE_LOG_LEVEL", "INFO"))
    auth_secret: str = field(
        default_factory=lambda: _env("CATEYE_AUTH_SECRET", "", "RASTRO_AUTH_SECRET")
    )

    # ── Paths ──
    base_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_BASE_DIR",
            Path(__file__).resolve().parent.parent.parent,
        )
    )
    data_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_DATA_DIR",
            Path.home() / ".local" / "share" / "CATEYE",
        )
    )
    config_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_CONFIG_DIR",
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "CATEYE",
        )
    )
    output_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_OUTPUT_DIR",
            Path.home() / ".local" / "share" / "CATEYE" / "output",
            "RASTRO_OUTPUT_DIR",
        )
    )
    frontend_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_FRONTEND_DIR",
            Path(__file__).resolve().parent.parent.parent / "frontend",
        )
    )
    frontend_dist_dir: Path = field(
        default_factory=lambda: _env_path(
            "CATEYE_FRONTEND_DIST_DIR",
            Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        )
    )
    disable_frontend: bool = field(
        default_factory=lambda: _env_bool("CATEYE_DISABLE_FRONTEND")
    )
    no_browser: bool = field(default_factory=lambda: _env_bool("CATEYE_NO_BROWSER"))

    # ── Database ──
    database_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            f"sqlite:///{Path.home() / '.local' / 'share' / 'CATEYE' / 'database' / 'cateye.db'}",
        )
    )

    # ── Scanning ──
    scan_interval: int = field(
        default_factory=lambda: _env_int("CATEYE_SCAN_INTERVAL", 30)
    )
    scan_mode: str = field(default_factory=lambda: _env("CATEYE_SCAN_MODE", "DEEP"))

    # ── Desktop / Recovery ──
    max_restart_retries: int = field(
        default_factory=lambda: _env_int("CATEYE_MAX_RESTART_RETRIES", 3)
    )
    health_check_interval: int = field(
        default_factory=lambda: _env_int("CATEYE_HEALTH_CHECK_INTERVAL", 10)
    )
    safe_mode: bool = field(default_factory=lambda: _env_bool("CATEYE_SAFE_MODE"))

    # ── Demo ──
    demo: bool = field(default_factory=lambda: _env_bool("CATEYE_DEMO"))
    backend: str = field(default_factory=lambda: _env("CATEYE_BACKEND", ""))

    # ── Performance ──
    cache_size: int = field(
        default_factory=lambda: _env_int("CATEYE_CACHE_SIZE", 4096)
    )

    # ── License ──
    license_secret: str = field(
        default_factory=lambda: _env(
            "CATEYE_LICENSE_SECRET", "", "RASTRO_LICENSE_SECRET"
        )
    )

    # ── Notifications ──
    smtp_host: str = field(
        default_factory=lambda: _env("CATEYE_SMTP_HOST", "", "RASTRO_SMTP_HOST")
    )
    smtp_port: int = field(
        default_factory=lambda: _env_int(
            "CATEYE_SMTP_PORT", 587, "RASTRO_SMTP_PORT"
        )
    )
    smtp_user: str = field(
        default_factory=lambda: _env("CATEYE_SMTP_USER", "", "RASTRO_SMTP_USER")
    )
    smtp_password: str = field(
        default_factory=lambda: _env(
            "CATEYE_SMTP_PASSWORD", "", "RASTRO_SMTP_PASSWORD"
        )
    )
    smtp_from: str = field(
        default_factory=lambda: _env("CATEYE_SMTP_FROM", "", "RASTRO_SMTP_FROM")
    )
    notification_email: str = field(
        default_factory=lambda: _env(
            "CATEYE_NOTIFICATION_EMAIL", "", "RASTRO_NOTIFICATION_EMAIL"
        )
    )
    twilio_account_sid: str = field(
        default_factory=lambda: _env("CATEYE_TWILIO_ACCOUNT_SID", "")
    )
    twilio_auth_token: str = field(
        default_factory=lambda: _env("CATEYE_TWILIO_AUTH_TOKEN", "")
    )
    twilio_whatsapp_from: str = field(
        default_factory=lambda: _env("CATEYE_TWILIO_WHATSAPP_FROM", "14155238886")
    )
    notification_whatsapp_to: str = field(
        default_factory=lambda: _env("CATEYE_NOTIFICATION_WHATSAPP_TO", "")
    )
    gmail_client_id: str = field(
        default_factory=lambda: _env("CATEYE_GMAIL_CLIENT_ID", "")
    )
    gmail_client_secret: str = field(
        default_factory=lambda: _env("CATEYE_GMAIL_CLIENT_SECRET", "")
    )
    gmail_refresh_token: str = field(
        default_factory=lambda: _env("CATEYE_GMAIL_REFRESH_TOKEN", "")
    )
    gmail_from: str = field(default_factory=lambda: _env("CATEYE_GMAIL_FROM", ""))
    fcm_server_key: str = field(
        default_factory=lambda: _env(
            "CATEYE_FCM_SERVER_KEY", "", "RASTRO_FCM_SERVER_KEY"
        )
    )
    fcm_project_id: str = field(
        default_factory=lambda: _env(
            "CATEYE_FCM_PROJECT_ID", "", "RASTRO_FCM_PROJECT_ID"
        )
    )

    # ── Test flags ──
    smoke_test: bool = field(default_factory=lambda: _env_bool("CATEYE_SMOKE_TEST"))
    portable_test: bool = field(
        default_factory=lambda: _env_bool("CATEYE_PORTABLE_TEST")
    )
    installer_test: bool = field(
        default_factory=lambda: _env_bool("CATEYE_INSTALLER_TEST")
    )

    # ── Legacy ──
    memory_consume: int = field(
        default_factory=lambda: _env_int(
            "CATEYE_MEMORY_CONSUME", 1, "RASTRO_MEMORY_CONSUME"
        )
    )

    @property
    def is_production(self) -> bool:
        return self.build_env == "production"


# Backward-compatible alias
EnvConfig = CATEYEConfig

_CONFIG_INSTANCE: CATEYEConfig | None = None


def get_config() -> CATEYEConfig:
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = CATEYEConfig()
    return _CONFIG_INSTANCE
