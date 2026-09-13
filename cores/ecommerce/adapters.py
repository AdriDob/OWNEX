"""E-commerce adapters — MercadoLibre + Instagram/WhatsApp (Meta).

Honest by contract: no credentials -> unavailable (never fake data, never raise).
Meli uses official api.mercadolibre.com OAuth2; IG/WA use Meta Graph API.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from cores.ecommerce.models import Marketplace, MarketplaceListing

logger = logging.getLogger("ownex.ecommerce.adapters")

MELI_API_BASE = "https://api.mercadolibre.com"
MELI_AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
MELI_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def _vault_token(provider: str, key: str = "access_token") -> str:
    """Read a token from vault or env. Empty string = not configured (honest)."""
    try:
        from cores.credentials.vault import get_platform_credentials

        creds = get_platform_credentials(provider) or {}
        token = str(creds.get(key, "") or "").strip()
        if token:
            return token
    except Exception:
        pass
    env_map = {
        "mercadolibre": "MELI_ACCESS_TOKEN",
        "meta": "META_ACCESS_TOKEN",
        "instagram": "META_ACCESS_TOKEN",
        "whatsapp": "META_ACCESS_TOKEN",
    }
    return os.environ.get(env_map.get(provider, ""), "").strip()


class MeliAdapter:
    """MercadoLibre official API adapter (OAuth2 bearer)."""

    def __init__(self, site_id: str = "MLA") -> None:
        self.site_id = site_id

    def is_available(self) -> bool:
        return bool(_vault_token("mercadolibre"))

    def status(self) -> dict[str, Any]:
        token = _vault_token("mercadolibre")
        if not token:
            return {
                "available": False,
                "reason": "MELI_ACCESS_TOKEN ausente en vault/env. "
                "Configurar OAuth en developers.mercadolibre.com → IdentityVault.",
                "site_id": self.site_id,
            }
        return {"available": True, "site_id": self.site_id}

    async def get_me(self) -> dict[str, Any]:
        token = _vault_token("mercadolibre")
        if not token:
            return {"success": False, "error": "not_configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"{MELI_API_BASE}/users/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"http_{resp.status_code}"}
                data = resp.json()
                return {"success": True, "user_id": data.get("id"), "nickname": data.get("nickname")}
        except Exception as exc:
            logger.warning("Meli get_me failed: %s", exc)
            return {"success": False, "error": "connection_failed"}

    async def list_orders_recent(self, seller_id: str = "", limit: int = 20) -> dict[str, Any]:
        token = _vault_token("mercadolibre")
        if not token:
            return {"success": False, "error": "not_configured", "orders": []}
        try:
            me = await self.get_me()
            sid = seller_id or str(me.get("user_id", ""))
            if not sid:
                return {"success": False, "error": "no_seller_id", "orders": []}
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"{MELI_API_BASE}/orders/search",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"seller": sid, "sort": "date_desc", "limit": max(1, min(limit, 50))},
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"http_{resp.status_code}", "orders": []}
                items = (resp.json() or {}).get("results", [])
                return {"success": True, "orders": items}
        except Exception as exc:
            logger.warning("Meli list_orders failed: %s", exc)
            return {"success": False, "error": "connection_failed", "orders": []}

    async def publish_item(self, listing: MarketplaceListing) -> dict[str, Any]:
        token = _vault_token("mercadolibre")
        if not token:
            return {"success": False, "error": "not_configured"}
        # Human Gate: publishing is external action. This method only PREPARES
        # the payload; real POST requires explicit approval via API layer.
        payload = {
            "title": listing.title[:60],
            "category_id": listing.category_id or "MLA1430",
            "price": float(listing.price_local or listing.price_usd),
            "currency_id": "ARS" if listing.currency == "ARS" else "USD",
            "available_quantity": max(listing.quantity, 1),
            "buying_mode": "buy_it_now",
            "listing_type_id": "gold_special",
            "condition": "new",
            "description": {"plain_text": (listing.description or "")[:4000]},
            "pictures": [{"source": url} for url in (listing.images or [])[:6]],
        }
        return {
            "success": True,
            "prepared": True,
            "payload": payload,
            "note": "Requiere aprobación humana para POST real.",
        }


class IGWAAdapter:
    """Instagram + WhatsApp via Meta Graph API (single token, two surfaces)."""

    def is_available(self) -> bool:
        return bool(_vault_token("meta"))

    def status(self) -> dict[str, Any]:
        if not self.is_available():
            return {
                "available": False,
                "reason": "META_ACCESS_TOKEN ausente. "
                "Crear app en developers.facebook.com → IG Graph + WhatsApp Business → IdentityVault.",
                "surfaces": ["instagram", "whatsapp"],
            }
        return {"available": True, "surfaces": ["instagram", "whatsapp"]}

    async def ig_publish_caption(self, ig_user_id: str, image_url: str, caption: str) -> dict[str, Any]:
        token = _vault_token("meta")
        if not token:
            return {"success": False, "error": "not_configured"}
        if not ig_user_id or not image_url:
            return {"success": False, "error": "missing_params"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                # Step 1: create media container (honest 2-step flow, no auto-publish without approval)
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{ig_user_id}/media",
                    data={"image_url": image_url, "caption": caption[:2200], "access_token": token},
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"http_{resp.status_code}"}
                container_id = (resp.json() or {}).get("id", "")
                return {
                    "success": True,
                    "prepared": True,
                    "container_id": container_id,
                    "note": "Container creado. Publicar requiere POST /media_publish con aprobación humana.",
                }
        except Exception as exc:
            logger.warning("IG publish failed: %s", exc)
            return {"success": False, "error": "connection_failed"}

    async def wa_send_template(
        self, phone_number_id: str, to_phone: str, template: str, lang: str = "es_AR"
    ) -> dict[str, Any]:
        token = _vault_token("meta")
        if not token:
            return {"success": False, "error": "not_configured"}
        if not phone_number_id or not to_phone or not template:
            return {"success": False, "error": "missing_params"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": to_phone,
                        "type": "template",
                        "template": {"name": template, "language": {"code": lang}},
                    },
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"http_{resp.status_code}"}
                return {"success": True, "message_id": (resp.json() or {}).get("messages", [{}])[0].get("id", "")}
        except Exception as exc:
            logger.warning("WA send failed: %s", exc)
            return {"success": False, "error": "connection_failed"}


_meli: MeliAdapter | None = None
_igwa: IGWAAdapter | None = None


def get_meli_adapter() -> MeliAdapter:
    global _meli
    if _meli is None:
        _meli = MeliAdapter()
    return _meli


def get_ig_wa_adapter() -> IGWAAdapter:
    global _igwa
    if _igwa is None:
        _igwa = IGWAAdapter()
    return _igwa


def adapter_health() -> dict[str, Any]:
    return {
        Marketplace.MERCADOLIBRE.value: get_meli_adapter().status(),
        "instagram_whatsapp": get_ig_wa_adapter().status(),
    }
