"""Auto-Email Handler — gestiona verificaciones y comunicaciones por email.

Monitorea emails de plataformas y:
- Verifica cuentas automáticamente (links de verificación)
- Responde preguntas de triage vía email
- Notifica pagos recibidos
- Alerta de deadlines próximos
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger("orion.auto_email")


class AutoEmailHandler:
    """Handles automated email interactions with platforms."""

    # Common email patterns for platform communications
    VERIFICATION_PATTERNS = [
        r"verify.*email",
        r"confirm.*account",
        r"activation.*link",
        r"click.*verify",
    ]

    PAYOUT_PATTERNS = [
        r"payout.*processed",
        r"payment.*sent",
        r"bounty.*paid",
        r"reward.*transferred",
        r"received.*payment",
    ]

    TRIAGE_PATTERNS = [
        r"triage.*question",
        r"need.*more.*info",
        r"clarification.*needed",
        r"additional.*information",
    ]

    def __init__(self) -> None:
        self._inbox_path = os.path.expanduser("~/.config/ownex/emails/")
        os.makedirs(self._inbox_path, exist_ok=True)

    async def check_emails(self) -> list[dict[str, Any]]:
        """Check for new emails from platforms."""
        actions = []

        # Check Gmail if configured
        gmail_actions = await self._check_gmail()
        actions.extend(gmail_actions)

        # Check Outlook if configured
        outlook_actions = await self._check_outlook()
        actions.extend(outlook_actions)

        return actions

    async def _check_gmail(self) -> list[dict[str, Any]]:
        """Check Gmail for platform emails."""
        try:
            import email
            import imaplib

            gmail_user = os.getenv("GMAIL_USER", "")
            gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")

            if not gmail_user or not gmail_pass:
                return []

            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(gmail_user, gmail_pass)
            mail.select("inbox")

            _, search_data = mail.search(None, "UNSEEN")
            actions = []

            for num in search_data[0].split():
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = msg.get("Subject", "")
                sender = msg.get("From", "")

                action = self._classify_email(subject, sender)
                if action:
                    actions.append(action)

            mail.logout()
            return actions

        except Exception as e:
            logger.debug("Gmail check failed: %s", e)
            return []

    async def _check_outlook(self) -> list[dict[str, Any]]:
        """Check Outlook for platform emails."""
        # Would use exchangelib or Microsoft Graph API
        return []

    def _classify_email(self, subject: str, sender: str) -> dict[str, Any] | None:
        """Classify an email and determine action needed."""
        subject_lower = subject.lower()

        # Check for verification emails
        for pattern in self.VERIFICATION_PATTERNS:
            if re.search(pattern, subject_lower):
                return {
                    "type": "verification",
                    "subject": subject,
                    "sender": sender,
                    "action": "Click verification link (may require manual intervention)",
                    "auto": False,
                }

        # Check for payout notifications
        for pattern in self.PAYOUT_PATTERNS:
            if re.search(pattern, subject_lower):
                return {
                    "type": "payout",
                    "subject": subject,
                    "sender": sender,
                    "action": "Record payment and reinvest",
                    "auto": True,
                }

        # Check for triage questions
        for pattern in self.TRIAGE_PATTERNS:
            if re.search(pattern, subject_lower):
                return {
                    "type": "triage",
                    "subject": subject,
                    "sender": sender,
                    "action": "Generate response with AI Worker",
                    "auto": True,
                }

        return None

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: str = "",
    ) -> dict[str, Any]:
        """Send an email via configured SMTP."""
        try:
            import smtplib
            from email.mime.text import MIMEText

            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", from_addr)
            smtp_pass = os.getenv("SMTP_PASSWORD", "")

            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return {"success": True, "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}


_handler: AutoEmailHandler | None = None


def get_email_handler() -> AutoEmailHandler:
    """Get singleton AutoEmailHandler."""
    global _handler
    if _handler is None:
        _handler = AutoEmailHandler()
    return _handler
