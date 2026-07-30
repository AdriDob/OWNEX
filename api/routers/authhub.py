"""AuthHub API router — OAuth2 and messaging provider management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from cores.authhub import AuthHubEvent, get_authhub
from cores.gateway.schemas import error, ok
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("ownex.api.authhub")

router = APIRouter(prefix="/api/authhub", tags=["authhub"])


@router.get("/providers")
async def list_providers():
    hub = get_authhub()
    providers = hub.get_all_providers()
    result = {}
    for name, provider in providers.items():
        authed = False
        if hasattr(provider, "is_authenticated"):
            try:
                authed = provider.is_authenticated()
            except Exception:
                authed = False
        result[name] = {
            "type": type(provider).__name__,
            "authenticated": authed,
        }
    return ok(result)


@router.post("/gmail/authorize")
async def gmail_authorize():
    hub = get_authhub()
    provider = hub.get_provider("gmail")
    if not provider:
        return error("Gmail provider not registered", version="1.0")
    url = provider.authorize_url()
    return ok({"authorize_url": url})


@router.post("/gmail/callback")
async def gmail_callback(request: Request):
    body = await request.json()
    code = body.get("code", "")
    state = body.get("state", "")
    if not code:
        return error("code is required", version="1.0")

    hub = get_authhub()
    provider = hub.get_provider("gmail")
    if not provider:
        return error("Gmail provider not registered", version="1.0")

    tokens = provider.exchange_code(code, state=state)
    if not tokens or "access_token" not in tokens:
        return error("Failed to exchange authorization code", version="1.0")

    hub._publish_event(AuthHubEvent.GMAIL_AUTHENTICATED, provider="gmail")
    return ok({"status": "authenticated", "email": tokens.get("email", "")})


@router.post("/whatsapp/send")
async def whatsapp_send(request: Request):
    body = await request.json()
    to = body.get("to", "")
    content = body.get("content", "")
    if not content:
        return error("content is required", version="1.0")
    if not to:
        return error("to is required", version="1.0")

    hub = get_authhub()
    provider = hub.get_provider("whatsapp")
    if not provider:
        return error("WhatsApp provider not registered", version="1.0")

    success = provider.send_message(to, content)
    if success:
        return ok({"status": "sent", "to": to})
    return error("Failed to send WhatsApp message", version="1.0")


@router.post("/telegram/send")
async def telegram_send(request: Request):
    body = await request.json()
    to = body.get("to", "")
    content = body.get("content", "")
    if not content:
        return error("content is required", version="1.0")

    hub = get_authhub()
    provider = hub.get_provider("telegram")
    if not provider:
        return error("Telegram provider not registered", version="1.0")

    success = provider.send_message(to, content)
    if success:
        return ok({"status": "sent", "to": to or "(default chat)"})
    return error("Failed to send Telegram message", version="1.0")


@router.post("/register")
async def register_provider(request: Request):
    body = await request.json()
    provider_name = body.get("provider", "")
    if not provider_name:
        return error("provider name is required", version="1.0")

    metadata = {k: v for k, v in body.get("credentials", {}).items()}
    vault = get_identity_vault()
    vault.store_credentials(
        provider=provider_name,
        email=body.get("email", ""),
        token=metadata.pop("token", ""),
        password=metadata.pop("password", ""),
        metadata=metadata,
    )

    hub = get_authhub()
    if provider_name == "gmail":
        from cores.authhub.gmail import GmailOAuth2

        hub.register_provider("gmail", GmailOAuth2())
    elif provider_name == "twilio":
        from cores.authhub.whatsapp import WhatsAppTwilio

        hub.register_provider("whatsapp", WhatsAppTwilio())
    elif provider_name == "telegram":
        from cores.authhub.telegram import TelegramBot

        hub.register_provider("telegram", TelegramBot())

    return ok({"status": "registered", "provider": provider_name})
