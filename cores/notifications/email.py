"""Email notification adapter — sends via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("cateye.notifications.email")


class EmailAdapter:
    def __init__(self) -> None:
        cfg = get_config()
        # Prefer OWNEX_SMTP_*/CATEYE_SMTP_* config, fall back to the OWNNEX_MAIL_*
        # verification SMTP settings so one `.env` configures both.
        self._host = cfg.smtp_host or os.environ.get("OWNNEX_MAIL_SMTP_HOST", "")
        self._port = cfg.smtp_port or int(os.environ.get("OWNNEX_MAIL_SMTP_PORT", "587"))
        self._user = cfg.smtp_user or os.environ.get("OWNNEX_MAIL_USERNAME", "")
        self._password = cfg.smtp_password or os.environ.get("OWNNEX_MAIL_PASSWORD", "")
        self._from = cfg.smtp_from or os.environ.get("OWNNEX_MAIL_FROM", "")
        self._to = cfg.notification_email or os.environ.get("OWNNEX_NOTIFICATION_EMAIL", self._user)
        self._enabled = bool(self._host and self._to)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def send(self, title: str, message: str, priority: str = "medium", metadata: dict[str, Any] | None = None) -> bool:
        if not self._enabled:
            logger.debug("Email disabled — set CATEYE_SMTP_HOST and CATEYE_NOTIFICATION_EMAIL")
            return False

        try:
            html = f"""<html><body style="font-family:sans-serif;padding:20px">
<h2 style="color:#7c3aed;">{title}</h2>
<p>{message}</p>
<hr><p style="color:#999;font-size:11px;">CATEYE Notification · Priority: {priority}</p>
</body></html>"""

            msg = MIMEText(html, "html")
            msg["Subject"] = f"[CATEYE] {title}"
            msg["From"] = self._from
            msg["To"] = self._to

            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                if self._user:
                    server.login(self._user, self._password)
                server.send_message(msg)

            logger.info("Email sent: %s -> %s", title, self._to)
            return True
        except Exception as exc:
            logger.warning("Email send failed: %s", exc)
            return False


_EMAIL: EmailAdapter | None = None


def get_email_adapter() -> EmailAdapter:
    global _EMAIL
    if _EMAIL is None:
        _EMAIL = EmailAdapter()
    return _EMAIL
