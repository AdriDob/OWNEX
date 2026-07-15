"""OutlookConnector — Microsoft Graph API integration for email, calendar, and contacts.

Authentication:
  OAuth2 via Microsoft Entra ID (Azure AD).
  Requires CATEYE_OUTLOOK_CLIENT_ID, CATEYE_OUTLOOK_CLIENT_SECRET, CATEYE_OUTLOOK_TENANT_ID in env or IdentityVault.

Usage:
    connector = get_outlook_connector()
    await connector.connect()
    emails = await connector.list_emails(max_results=10)
    event = await connector.create_calendar_event(subject="Review report", ...)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from core.capabilities.registry import get_capability_registry
from core.events.correlation import get_or_create_correlation_id
from core.events.types import Events

logger = logging.getLogger("orion.integrations.outlook")

MICROSOFT_AUTHORITY = "https://login.microsoftonline.com"
MICROSOFT_GRAPH = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT = 15.0


@dataclass
class OutlookEmail:
    id: str
    subject: str
    from_address: str
    to_addresses: list[str]
    body_preview: str
    received_at: str
    is_read: bool
    has_attachments: bool
    importance: str = "normal"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutlookCalendarEvent:
    id: str
    subject: str
    start_time: str
    end_time: str
    location: str = ""
    organizer: str = ""
    is_online: bool = False
    body_preview: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutlookContact:
    id: str
    display_name: str
    email: str
    phone: str = ""
    company: str = ""
    job_title: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class OutlookConnector:
    """Microsoft Graph API connector — email, calendar, contacts."""

    def __init__(self) -> None:
        self._client_id: str = ""
        self._client_secret: str = ""
        self._tenant_id: str = ""
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._connected: bool = False
        self._register_capabilities()

    # ── Auth ─────────────────────────────────────────

    async def connect(self) -> bool:
        """Authenticate via OAuth2 client credentials flow."""
        if self._load_credentials():
            return await self._acquire_token()
        return False

    async def disconnect(self) -> None:
        self._access_token = ""
        self._token_expires_at = 0.0
        self._connected = False

    async def health(self) -> dict[str, Any]:
        """Check connectivity by fetching user info from Graph API."""
        try:
            if not self._connected or time.time() >= self._token_expires_at:
                return {"connected": False, "error": "Not authenticated"}
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me",
                    headers=self._auth_headers(),
                )
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "connected": True,
                        "user": data.get("displayName", data.get("userPrincipalName", "unknown")),
                    }
                return {"connected": False, "error": f"HTTP {r.status_code}"}
        except Exception as exc:
            return {"connected": False, "error": str(exc)}

    def is_connected(self) -> bool:
        return self._connected and time.time() < self._token_expires_at

    # ── Email ────────────────────────────────────────

    async def list_emails(
        self,
        max_results: int = 20,
        folder: str = "inbox",
        unread_only: bool = False,
    ) -> list[OutlookEmail]:
        """Fetch recent emails from a folder."""
        if not self.is_connected():
            return []
        params: dict[str, Any] = {
            "$top": max_results,
            "$orderby": "receivedDateTime DESC",
            "$select": "id,subject,from,toRecipients,bodyPreview,receivedDateTime,isRead,hasAttachments,importance",
        }
        if unread_only:
            params["$filter"] = "isRead eq false"
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me/mailFolders/{folder}/messages",
                    headers=self._auth_headers(),
                    params=params,
                )
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Failed to list emails: HTTP %d", r.status_code)
                    return []
                data = r.json()
                return [self._parse_email(item) for item in data.get("value", [])]
        except Exception as exc:
            logger.warning("[OUTLOOK] list_emails error: %s", exc)
            return []

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        importance: str = "normal",
    ) -> bool:
        """Send an email via Outlook."""
        if not self.is_connected():
            return False
        message: dict[str, Any] = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
                "importance": importance,
            },
        }
        if cc:
            message["message"]["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(
                    f"{MICROSOFT_GRAPH}/me/sendMail",
                    headers=self._auth_headers(),
                    json=message,
                )
                if r.status_code in (202, 200):
                    logger.info("[OUTLOOK] Email sent: '%s' to %s", subject, to)
                    self._publish(
                        Events.NOTIFICATION_SENT,
                        {
                            "channel": "outlook",
                            "subject": subject,
                            "to": to,
                            "success": True,
                        },
                    )
                    self._publish(
                        Events.EMAIL_SENT,
                        {
                            "subject": subject,
                            "to": to,
                            "success": True,
                        },
                    )
                    return True
                logger.warning("[OUTLOOK] Failed to send email: HTTP %d", r.status_code)
                self._publish(
                    Events.NOTIFICATION_SENT,
                    {
                        "channel": "outlook",
                        "subject": subject,
                        "to": to,
                        "success": False,
                        "error": f"HTTP {r.status_code}",
                    },
                )
                return False
        except Exception as exc:
            logger.warning("[OUTLOOK] send_email error: %s", exc)
            return False

    # ── Calendar ─────────────────────────────────────

    async def list_calendar_events(
        self,
        max_results: int = 20,
        days_ahead: int = 14,
    ) -> list[OutlookCalendarEvent]:
        """Fetch upcoming calendar events."""
        if not self.is_connected():
            return []
        params: dict[str, Any] = {
            "$top": max_results,
            "$orderby": "start/dateTime DESC",
            "$select": "id,subject,start,end,location,organizer,isOnlineMeeting,bodyPreview",
        }
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me/events",
                    headers=self._auth_headers(),
                    params=params,
                )
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Failed to list events: HTTP %d", r.status_code)
                    return []
                data = r.json()
                return [self._parse_event(item) for item in data.get("value", [])]
        except Exception as exc:
            logger.warning("[OUTLOOK] list_calendar_events error: %s", exc)
            return []

    async def create_calendar_event(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        body: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> OutlookCalendarEvent | None:
        """Create a calendar event."""
        if not self.is_connected():
            return None
        event: dict[str, Any] = {
            "subject": subject,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }
        if body:
            event["body"] = {"contentType": "HTML", "content": body}
        if location:
            event["location"] = {"displayName": location}
        if attendees:
            event["attendees"] = [{"emailAddress": {"address": a}, "type": "required"} for a in attendees]
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(
                    f"{MICROSOFT_GRAPH}/me/events",
                    headers=self._auth_headers(),
                    json=event,
                )
                if r.status_code == 201:
                    data = r.json()
                    logger.info("[OUTLOOK] Event created: '%s'", subject)
                    return self._parse_event(data)
                logger.warning("[OUTLOOK] Failed to create event: HTTP %d", r.status_code)
                return None
        except Exception as exc:
            logger.warning("[OUTLOOK] create_calendar_event error: %s", exc)
            return None

    # ── Contacts ─────────────────────────────────────

    async def list_contacts(self, max_results: int = 50) -> list[OutlookContact]:
        """Fetch contacts from the default contacts folder."""
        if not self.is_connected():
            return []
        params: dict[str, Any] = {
            "$top": max_results,
            "$orderby": "displayName ASC",
            "$select": "id,displayName,emailAddresses,businessPhones,companyName,jobTitle",
        }
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me/contacts",
                    headers=self._auth_headers(),
                    params=params,
                )
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Failed to list contacts: HTTP %d", r.status_code)
                    return []
                data = r.json()
                return [self._parse_contact(item) for item in data.get("value", [])]
        except Exception as exc:
            logger.warning("[OUTLOOK] list_contacts error: %s", exc)
            return []

    # ── Private ──────────────────────────────────────

    def _load_credentials(self) -> bool:
        """Load OAuth2 credentials from env vars."""
        import os

        self._client_id = os.environ.get("CATEYE_OUTLOOK_CLIENT_ID", "")
        self._client_secret = os.environ.get("CATEYE_OUTLOOK_CLIENT_SECRET", "")
        self._tenant_id = os.environ.get("CATEYE_OUTLOOK_TENANT_ID", "")
        if self._client_id and self._client_secret and self._tenant_id:
            return True
        # Fallback: try IdentityVault
        try:
            from cores.identity_vault import get_identity_vault

            vault = get_identity_vault()
            self._client_id = vault.get("outlook_client_id", "")
            self._client_secret = vault.get("outlook_client_secret", "")
            self._tenant_id = vault.get("outlook_tenant_id", "")
            return bool(self._client_id and self._client_secret and self._tenant_id)
        except Exception:
            logger.warning("[OUTLOOK] No credentials found in env or vault")
            return False

    async def _acquire_token(self) -> bool:
        """OAuth2 client credentials token acquisition."""
        url = f"{MICROSOFT_AUTHORITY}/{self._tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(url, data=data)
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Token acquisition failed: HTTP %d", r.status_code)
                    self._connected = False
                    return False
                token_data = r.json()
                self._access_token = token_data["access_token"]
                self._token_expires_at = time.time() + token_data.get("expires_in", 3600) - 60
                self._connected = True
                logger.info("[OUTLOOK] Connected — token expires in %ds", token_data.get("expires_in", 0))
                return True
        except Exception as exc:
            logger.warning("[OUTLOOK] Token acquisition error: %s", exc)
            self._connected = False
            return False

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _parse_email(item: dict[str, Any]) -> OutlookEmail:
        return OutlookEmail(
            id=item.get("id", ""),
            subject=item.get("subject", ""),
            from_address=item.get("from", {}).get("emailAddress", {}).get("address", ""),
            to_addresses=[r.get("emailAddress", {}).get("address", "") for r in item.get("toRecipients", [])],
            body_preview=item.get("bodyPreview", ""),
            received_at=item.get("receivedDateTime", ""),
            is_read=item.get("isRead", False),
            has_attachments=item.get("hasAttachments", False),
            importance=item.get("importance", "normal"),
            raw=item,
        )

    @staticmethod
    def _parse_event(item: dict[str, Any]) -> OutlookCalendarEvent:
        return OutlookCalendarEvent(
            id=item.get("id", ""),
            subject=item.get("subject", ""),
            start_time=item.get("start", {}).get("dateTime", ""),
            end_time=item.get("end", {}).get("dateTime", ""),
            location=item.get("location", {}).get("displayName", ""),
            organizer=item.get("organizer", {}).get("emailAddress", {}).get("address", ""),
            is_online=item.get("isOnlineMeeting", False),
            body_preview=item.get("bodyPreview", ""),
            raw=item,
        )

    @staticmethod
    def _parse_contact(item: dict[str, Any]) -> OutlookContact:
        emails = item.get("emailAddresses", [])
        phones = item.get("businessPhones", [])
        return OutlookContact(
            id=item.get("id", ""),
            display_name=item.get("displayName", ""),
            email=emails[0].get("address", "") if emails else "",
            phone=phones[0] if phones else "",
            company=item.get("companyName", ""),
            job_title=item.get("jobTitle", ""),
            raw=item,
        )

    # ── Events ─────────────────────────────────────────

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to the legacy EventBus."""
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            cid = get_or_create_correlation_id()
            bus.publish(event_type, correlation_id=cid, source="outlook", **payload)
        except Exception:
            logger.debug("EventBus not available for %s", event_type)

    def _register_capabilities(self) -> None:
        """Register Outlook's capabilities in the CapabilityRegistry."""
        try:
            reg = get_capability_registry()
            reg.register(
                "send_email",
                "outlook",
                {"auth": "oauth2", "provider": "microsoft_graph"},
                description="Send email via Microsoft Graph API",
            )
            reg.register(
                "list_emails", "outlook", {"max_results": 100}, description="Fetch recent emails from Outlook inbox"
            )
            reg.register(
                "create_calendar_event",
                "outlook",
                {"supports": ["online", "location", "attendees"]},
                description="Create calendar event in Outlook",
            )
            reg.register(
                "list_calendar_events", "outlook", {"max_days_ahead": 365}, description="Fetch upcoming calendar events"
            )
            reg.register("list_contacts", "outlook", {"max_results": 500}, description="Fetch contacts from Outlook")
        except Exception:
            logger.debug("CapabilityRegistry not available")


_OUTLOOK: OutlookConnector | None = None


def get_outlook_connector() -> OutlookConnector:
    global _OUTLOOK
    if _OUTLOOK is None:
        _OUTLOOK = OutlookConnector()
    return _OUTLOOK


def reset_outlook_connector() -> None:
    global _OUTLOOK
    _OUTLOOK = None
