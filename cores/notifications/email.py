"""Email notification adapter — sends via SMTP with priority headers.

Configuration (env vars):
- OWNEX_SMTP_HOST / CATEYE_SMTP_HOST  (required for email)
- OWNEX_SMTP_PORT / CATEYE_SMTP_PORT  (default 587)
- OWNEX_SMTP_USER / CATEYE_SMTP_USER
- OWNEX_SMTP_PASSWORD / CATEYE_SMTP_PASSWORD
- OWNEX_SMTP_FROM / CATEYE_SMTP_FROM
- OWNEX_NOTIFICATION_EMAIL / CATEYE_NOTIFICATION_EMAIL  (configurable recipient)

Priority headers (when priority=critical or priority=high):
- Importance: high
- X-Priority: 1
- X-MSMail-Priority: High

Note: The client (Gmail, Outlook, Apple Mail) decides how to display priority.
OWNEX cannot force any client to show an "Important" label.
For maximum deliverability, configure SPF + DKIM + DMARC on your domain.
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("cateye.notifications.email")

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


class EmailDeliveryRecord:
    """Track email delivery status for audit trail."""

    def __init__(self, to: str, subject: str, priority: str, success: bool, error: str | None = None):
        self.to = to
        self.subject = subject
        self.priority = priority
        self.success = success
        self.error = error
        self.timestamp = time.time()
        self.delivered_at: float | None = None if not success else self.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "to": self.to,
            "subject": self.subject,
            "priority": self.priority,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
            "delivered_at": self.delivered_at,
        }


class EmailAdapter:
    """Email adapter with priority headers, configurable recipient, and retry logic."""

    def __init__(self) -> None:
        cfg = get_config()
        # Prefer OWNEX_SMTP_*/CATEYE_SMTP_* config, fall back to the OWNNEX_MAIL_*
        # verification SMTP settings so one `.env` configures both.
        self._host = cfg.smtp_host or os.environ.get("OWNNEX_MAIL_SMTP_HOST", "")
        self._port = cfg.smtp_port or int(os.environ.get("OWNNEX_MAIL_SMTP_PORT", "587"))
        self._user = cfg.smtp_user or os.environ.get("OWNNEX_MAIL_USERNAME", "")
        self._password = cfg.smtp_password or os.environ.get("OWNNEX_MAIL_PASSWORD", "")
        self._from = cfg.smtp_from or os.environ.get("OWNNEX_MAIL_FROM", "")
        self._to = cfg.notification_email or os.environ.get("OWNEX_NOTIFICATION_EMAIL", self._user)
        self._enabled = bool(self._host and self._to)
        self._delivery_history: list[EmailDeliveryRecord] = []
        self._max_history = 100

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def configured_recipient(self) -> str:
        """Return the currently configured recipient email."""
        return self._to

    def _get_priority_headers(self, priority: str) -> dict[str, str]:
        """Get email headers based on priority level.

        Priority mapping:
        - critical: Importance: high, X-Priority: 1
        - high: Importance: high, X-Priority: 1
        - medium: Importance: normal, X-Priority: 3
        - low: Importance: low, X-Priority: 5

        Note: These are hints to the mail client. Gmail, Outlook, Apple Mail
        decide independently how to display priority. OWNEX cannot force
        any client to show an "Important" label.
        """
        if priority in ("critical", "high"):
            return {
                "Importance": "high",
                "X-Priority": "1",
                "X-MSMail-Priority": "High",
            }
        elif priority == "low":
            return {
                "Importance": "low",
                "X-Priority": "5",
                "X-MSMail-Priority": "Low",
            }
        else:
            return {
                "Importance": "normal",
                "X-Priority": "3",
                "X-MSMail-Priority": "Normal",
            }

    def send(
        self,
        title: str,
        message: str,
        priority: str = "medium",
        metadata: dict[str, Any] | None = None,
        to: str | None = None,
    ) -> bool:
        """Send an email notification with priority headers and retry logic.

        Args:
            title: Email subject (prefixed with [OWNEX])
            message: HTML body content
            priority: Priority level (critical/high/medium/low)
            metadata: Optional metadata for logging
            to: Override recipient (uses configured recipient if None)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._enabled:
            logger.debug("Email disabled — set OWNEX_SMTP_HOST and OWNEX_NOTIFICATION_EMAIL")
            return False

        recipient = to or self._to
        if not recipient:
            logger.warning("No recipient configured — set OWNEX_NOTIFICATION_EMAIL")
            return False

        # Get priority headers
        priority_headers = self._get_priority_headers(priority)

        # Build HTML content
        priority_label = priority.upper() if priority != "medium" else ""
        html = f"""<html><body style="font-family:sans-serif;padding:20px">
<h2 style="color:#7c3aed;">{title}</h2>
<p>{message}</p>
<hr>
<p style="color:#999;font-size:11px;">
    OWNEX Notification · Priority: {priority_label or "NORMAL"}<br>
    This is an automated message from OWNEX OMEGA.
</p>
</body></html>"""

        # Retry logic
        last_error: str | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                msg = MIMEText(html, "html")
                msg["Subject"] = f"[OWNEX] {title}"
                msg["From"] = self._from
                msg["To"] = recipient

                # Add priority headers
                for header, value in priority_headers.items():
                    msg[header] = value

                with smtplib.SMTP(self._host, self._port, timeout=30) as server:
                    server.starttls()
                    if self._user:
                        server.login(self._user, self._password)
                    server.send_message(msg)

                # Record success
                record = EmailDeliveryRecord(
                    to=recipient,
                    subject=title,
                    priority=priority,
                    success=True,
                )
                self._record_delivery(record)

                logger.info(
                    "Email sent: %s -> %s (priority=%s, attempt=%d/%d)",
                    title,
                    recipient,
                    priority,
                    attempt,
                    MAX_RETRIES,
                )
                return True

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Email send failed (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS * attempt)  # Exponential backoff

        # All retries failed
        record = EmailDeliveryRecord(
            to=recipient,
            subject=title,
            priority=priority,
            success=False,
            error=last_error,
        )
        self._record_delivery(record)

        logger.error(
            "Email delivery failed after %d attempts: %s -> %s",
            MAX_RETRIES,
            title,
            recipient,
        )
        return False

    def _record_delivery(self, record: EmailDeliveryRecord) -> None:
        """Record delivery status for audit trail."""
        self._delivery_history.append(record)
        if len(self._delivery_history) > self._max_history:
            self._delivery_history = self._delivery_history[-self._max_history :]

    def get_delivery_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent delivery records."""
        return [r.to_dict() for r in self._delivery_history[-limit:]]

    def get_delivery_stats(self) -> dict[str, Any]:
        """Get delivery statistics."""
        total = len(self._delivery_history)
        successful = sum(1 for r in self._delivery_history if r.success)
        return {
            "total_sent": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "configured_recipient": self._to,
            "smtp_configured": bool(self._host),
        }


_EMAIL: EmailAdapter | None = None


def get_email_adapter() -> EmailAdapter:
    global _EMAIL
    if _EMAIL is None:
        _EMAIL = EmailAdapter()
    return _EMAIL
