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
from cores.events.correlation import get_or_create_correlation_id
from cores.events.types import Events

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


@dataclass
class OutlookTodoList:
    """Microsoft To Do list (backed by Outlook Tasks API)."""

    id: str
    display_name: str
    is_owner: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutlookTodoTask:
    """Microsoft To Do task item."""

    id: str
    title: str
    status: str = "notStarted"  # notStarted | inProgress | completed | waitingOnOthers | deferred
    importance: str = "normal"  # low | normal | high
    due_date: str = ""
    body_preview: str = ""
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

    async def update_calendar_event(
        self,
        event_id: str,
        subject: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        body: str | None = None,
        location: str | None = None,
    ) -> OutlookCalendarEvent | None:
        """Update an existing calendar event."""
        if not self.is_connected():
            return None
        patch: dict[str, Any] = {}
        if subject is not None:
            patch["subject"] = subject
        if start_time is not None:
            patch["start"] = {"dateTime": start_time, "timeZone": "UTC"}
        if end_time is not None:
            patch["end"] = {"dateTime": end_time, "timeZone": "UTC"}
        if body is not None:
            patch["body"] = {"contentType": "HTML", "content": body}
        if location is not None:
            patch["location"] = {"displayName": location}
        if not patch:
            return None
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.patch(
                    f"{MICROSOFT_GRAPH}/me/events/{event_id}",
                    headers=self._auth_headers(),
                    json=patch,
                )
                if r.status_code == 200:
                    data = r.json()
                    logger.info("[OUTLOOK] Event updated: '%s'", data.get("subject", event_id))
                    return self._parse_event(data)
                logger.warning("[OUTLOOK] Failed to update event: HTTP %d", r.status_code)
                return None
        except Exception as exc:
            logger.warning("[OUTLOOK] update_calendar_event error: %s", exc)
            return None

    async def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if not self.is_connected():
            return False
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.delete(
                    f"{MICROSOFT_GRAPH}/me/events/{event_id}",
                    headers=self._auth_headers(),
                )
                if r.status_code == 204:
                    logger.info("[OUTLOOK] Event deleted: %s", event_id)
                    return True
                logger.warning("[OUTLOOK] Failed to delete event: HTTP %d", r.status_code)
                return False
        except Exception as exc:
            logger.warning("[OUTLOOK] delete_calendar_event error: %s", exc)
            return False

    # ── Microsoft To Do ───────────────────────────────

    async def list_todo_lists(self, max_results: int = 50) -> list[OutlookTodoList]:
        """Fetch Microsoft To Do lists (Outlook Tasks API)."""
        if not self.is_connected():
            return []
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me/todo/lists",
                    headers=self._auth_headers(),
                    params={"$top": max_results, "$select": "id,displayName,wellknownListName,isOwner"},
                )
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Failed to list todo lists: HTTP %d", r.status_code)
                    return []
                data = r.json()
                return [self._parse_todo_list(item) for item in data.get("value", [])]
        except Exception as exc:
            logger.warning("[OUTLOOK] list_todo_lists error: %s", exc)
            return []

    async def get_or_create_todo_list(self, display_name: str = "OWNEX") -> OutlookTodoList | None:
        """Find a To Do list by name; create it if it doesn't exist."""
        for lst in await self.list_todo_lists():
            if lst.display_name.strip().lower() == display_name.strip().lower():
                return lst
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(
                    f"{MICROSOFT_GRAPH}/me/todo/lists",
                    headers=self._auth_headers(),
                    json={"displayName": display_name},
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    logger.info("[OUTLOOK] Created todo list: '%s'", display_name)
                    return self._parse_todo_list(data)
                logger.warning("[OUTLOOK] Failed to create todo list: HTTP %d", r.status_code)
                return None
        except Exception as exc:
            logger.warning("[OUTLOOK] get_or_create_todo_list error: %s", exc)
            return None

    async def list_todo_tasks(self, list_id: str, max_results: int = 50) -> list[OutlookTodoTask]:
        """Fetch tasks from a To Do list."""
        if not self.is_connected():
            return []
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.get(
                    f"{MICROSOFT_GRAPH}/me/todo/lists/{list_id}/tasks",
                    headers=self._auth_headers(),
                    params={
                        "$top": max_results,
                        "$select": "id,title,status,importance,dueDateTime,body,lastModifiedDateTime",
                    },
                )
                if r.status_code != 200:
                    logger.warning("[OUTLOOK] Failed to list todo tasks: HTTP %d", r.status_code)
                    return []
                data = r.json()
                return [self._parse_todo_task(item) for item in data.get("value", [])]
        except Exception as exc:
            logger.warning("[OUTLOOK] list_todo_tasks error: %s", exc)
            return []

    async def create_todo_task(
        self,
        list_id: str,
        title: str,
        due_date: str = "",
        importance: str = "normal",
        body: str = "",
    ) -> OutlookTodoTask | None:
        """Create a task in a To Do list."""
        if not self.is_connected():
            return None
        payload: dict[str, Any] = {"title": title, "importance": importance}
        if due_date:
            payload["dueDateTime"] = self._iso_datetime_payload(due_date)
        if body:
            payload["body"] = {"content": body, "contentType": "text"}
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(
                    f"{MICROSOFT_GRAPH}/me/todo/lists/{list_id}/tasks",
                    headers=self._auth_headers(),
                    json=payload,
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    logger.info("[OUTLOOK] Created todo task: '%s'", title)
                    return self._parse_todo_task(data)
                logger.warning("[OUTLOOK] Failed to create todo task: HTTP %d", r.status_code)
                return None
        except Exception as exc:
            logger.warning("[OUTLOOK] create_todo_task error: %s", exc)
            return None

    async def update_todo_task(
        self,
        list_id: str,
        task_id: str,
        title: str | None = None,
        due_date: str | None = None,
        status: str | None = None,
        importance: str | None = None,
    ) -> OutlookTodoTask | None:
        """Update an existing task in a To Do list."""
        if not self.is_connected():
            return None
        patch: dict[str, Any] = {}
        if title is not None:
            patch["title"] = title
        if due_date is not None:
            patch["dueDateTime"] = self._iso_datetime_payload(due_date)
        if status is not None:
            patch["status"] = status
        if importance is not None:
            patch["importance"] = importance
        if not patch:
            return None
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.patch(
                    f"{MICROSOFT_GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}",
                    headers=self._auth_headers(),
                    json=patch,
                )
                if r.status_code == 200:
                    data = r.json()
                    logger.info("[OUTLOOK] Updated todo task: %s", task_id)
                    return self._parse_todo_task(data)
                logger.warning("[OUTLOOK] Failed to update todo task: HTTP %d", r.status_code)
                return None
        except Exception as exc:
            logger.warning("[OUTLOOK] update_todo_task error: %s", exc)
            return None

    async def delete_todo_task(self, list_id: str, task_id: str) -> bool:
        """Delete a task from a To Do list."""
        if not self.is_connected():
            return False
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.delete(
                    f"{MICROSOFT_GRAPH}/me/todo/lists/{list_id}/tasks/{task_id}",
                    headers=self._auth_headers(),
                )
                if r.status_code == 204:
                    logger.info("[OUTLOOK] Deleted todo task: %s", task_id)
                    return True
                logger.warning("[OUTLOOK] Failed to delete todo task: HTTP %d", r.status_code)
                return False
        except Exception as exc:
            logger.warning("[OUTLOOK] delete_todo_task error: %s", exc)
            return False

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

    @staticmethod
    def _parse_todo_list(item: dict[str, Any]) -> OutlookTodoList:
        return OutlookTodoList(
            id=item.get("id", ""),
            display_name=item.get("displayName", ""),
            is_owner=item.get("isOwner", True),
            raw=item,
        )

    @staticmethod
    def _parse_todo_task(item: dict[str, Any]) -> OutlookTodoTask:
        due = item.get("dueDateTime", {}) or {}
        body = item.get("body", {}) or {}
        return OutlookTodoTask(
            id=item.get("id", ""),
            title=item.get("title", ""),
            status=item.get("status", "notStarted"),
            importance=item.get("importance", "normal"),
            due_date=due.get("dateTime", ""),
            body_preview=body.get("content", "")[:200] if body.get("content") else "",
            raw=item,
        )

    @staticmethod
    def _iso_datetime_payload(value: str) -> dict[str, str]:
        """Normalize an ISO datetime into Graph's dueDateTime payload."""
        dt = value
        if dt.endswith("Z"):
            dt = dt.replace("Z", "")
        elif dt.endswith("+00:00"):
            dt = dt.replace("+00:00", "")
        return {"dateTime": dt, "timeZone": "UTC"}

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
            reg.register(
                "update_calendar_event",
                "outlook",
                {"supports": ["subject", "start", "end", "body", "location"]},
                description="Update a calendar event in Outlook",
            )
            reg.register(
                "delete_calendar_event",
                "outlook",
                {},
                description="Delete a calendar event from Outlook",
            )
            reg.register(
                "list_todo_lists",
                "outlook",
                {"provider": "microsoft_to_do"},
                description="List Microsoft To Do lists",
            )
            reg.register(
                "create_todo_task",
                "outlook",
                {"supports": ["due_date", "importance", "body"]},
                description="Create a task in Microsoft To Do",
            )
            reg.register(
                "update_todo_task",
                "outlook",
                {"supports": ["title", "due_date", "status", "importance"]},
                description="Update a task in Microsoft To Do",
            )
            reg.register(
                "delete_todo_task",
                "outlook",
                {},
                description="Delete a task from Microsoft To Do",
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
