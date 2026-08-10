"""Transactional mail via SMTP (stdlib only).

Configuration (env vars, matching OWNEX_* convention):

- OWNNEX_MAIL_SMTP_HOST   (required for mail to be enabled)
- OWNNEX_MAIL_SMTP_PORT   (default 587)
- OWNNEX_MAIL_USERNAME
- OWNNEX_MAIL_PASSWORD
- OWNNEX_MAIL_FROM        (default: "OWNEX OMEGA <noreply@ownex.local>")
- OWNNEX_MAIL_USE_TLS     (default true)

When OWNNEX_MAIL_SMTP_HOST is unset, ``mail_configured()`` returns False and
accounts are created pre-verified (local-first behavior).
"""

import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger("ownex.mail")


def mail_configured() -> bool:
    return bool(os.environ.get("OWNNEX_MAIL_SMTP_HOST", "").strip())


def _mail_from() -> tuple[str, str]:
    raw = os.environ.get("OWNNEX_MAIL_FROM", "OWNEX OMEGA <noreply@ownex.local>")
    if "<" in raw and ">" in raw:
        name, addr = raw.split("<", 1)
        return name.strip(), addr.rstrip(">").strip()
    return "", raw


def send_verification_email(to_email: str, username: str, token: str) -> None:
    """Send a verification email. Raises on failure so the caller can decide."""
    host = os.environ["OWNNEX_MAIL_SMTP_HOST"]
    port = int(os.environ.get("OWNNEX_MAIL_SMTP_PORT", "587"))
    smtp_user = os.environ.get("OWNNEX_MAIL_USERNAME", "")
    smtp_password = os.environ.get("OWNNEX_MAIL_PASSWORD", "")
    use_tls = os.environ.get("OWNNEX_MAIL_USE_TLS", "true").lower() != "false"

    name, from_addr = _mail_from()

    base_url = os.environ.get("OWNNEX_PUBLIC_URL", "http://localhost:5173")
    verify_url = f"{base_url.rstrip('/')}/verify?token={token}"

    msg = EmailMessage()
    msg["Subject"] = f"OWNEX — Verifica tu correo, {username}"
    msg["From"] = formataddr((name, from_addr))
    msg["To"] = to_email
    msg.set_content(
        f"Hola {username},\n\n"
        "Confirmá tu dirección de correo para activar tu cuenta OWNEX.\n\n"
        f"Enlace de verificación (válido 24 h):\n{verify_url}\n\n"
        "Si no creaste esta cuenta, ignorá este mensaje.\n"
    )

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user or smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
    logger.info("Verification email sent to %s", to_email)
