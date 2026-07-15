"""Notification bridges — wires channels, event bus, and persistence together."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("cateye.notifications.bridges")


def register_db_bridge() -> None:
    """Connect NotificationHub -> SQL database persistence."""
    from cores.notifications.db_bridge import persist_notification
    from cores.notifications.hub import get_hub

    hub = get_hub()
    hub.register_db_bridge(persist_notification)
    logger.info("DB bridge registered on NotificationHub")


def register_desktop_channel() -> None:
    """Register the desktop notification handler on the hub."""
    from cores.notifications.hub import get_hub

    def _desktop_handler(type_: str, payload: dict[str, Any]) -> None:
        try:
            from desktop.notifications import send_notification

            priority = payload.get("priority", "medium")
            urgency = "critical" if priority == "critical" else "normal"
            send_notification(
                title=payload.get("title", "CATEYE"),
                message=payload.get("message", ""),
                urgency=urgency,
            )
            db_id = payload.get("metadata", {}).get("db_id")
            if db_id:
                from cores.notifications.db_bridge import record_delivery

                record_delivery(db_id, "desktop", "sent")
        except Exception as exc:
            logger.debug("Desktop notification handler error: %s", exc)

    hub = get_hub()
    hub.subscribe("desktop", _desktop_handler)
    logger.info("Desktop channel registered on NotificationHub")


def register_email_channel() -> None:
    """Register the email notification handler on the hub."""
    from cores.notifications.email import get_email_adapter
    from cores.notifications.hub import get_hub

    adapter = get_email_adapter()
    if not adapter.is_enabled:
        logger.info("Email channel skipped — not configured")
        return

    def _email_handler(type_: str, payload: dict[str, Any]) -> None:
        ok = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from cores.notifications.db_bridge import record_delivery

            record_delivery(db_id, "email", "sent" if ok else "failed", None if ok else "send_error")

    hub = get_hub()
    hub.subscribe("email", _email_handler)
    logger.info("Email channel registered on NotificationHub")


def register_fcm_channel() -> None:
    """Register the FCM push notification handler on the hub."""
    from cores.notifications.fcm import get_fcm_adapter
    from cores.notifications.hub import get_hub

    adapter = get_fcm_adapter()
    if not adapter.is_enabled:
        logger.info("FCM channel skipped — not configured")
        return

    def _fcm_handler(type_: str, payload: dict[str, Any]) -> None:
        count = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from cores.notifications.db_bridge import record_delivery

            record_delivery(db_id, "fcm", "sent" if count else "failed", "no_devices" if not count else None)

    hub = get_hub()
    hub.subscribe("fcm", _fcm_handler)
    logger.info("FCM channel registered on NotificationHub")


def register_whatsapp_channel() -> None:
    """Register the WhatsApp notification handler on the hub."""
    from cores.notifications.hub import get_hub
    from cores.notifications.whatsapp import get_whatsapp_adapter

    adapter = get_whatsapp_adapter()
    if not adapter.is_enabled:
        logger.info("WhatsApp channel skipped — not configured")
        return

    def _whatsapp_handler(type_: str, payload: dict[str, Any]) -> None:
        ok = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from cores.notifications.db_bridge import record_delivery

            record_delivery(db_id, "whatsapp", "sent" if ok else "failed", None if ok else "send_error")

    hub = get_hub()
    hub.subscribe("whatsapp", _whatsapp_handler)
    logger.info("WhatsApp channel registered on NotificationHub")


def register_gmail_channel() -> None:
    """Register the Gmail notification handler on the hub."""
    from cores.notifications.gmail import get_gmail_adapter
    from cores.notifications.hub import get_hub

    adapter = get_gmail_adapter()
    if not adapter.is_enabled:
        logger.info("Gmail channel skipped — not configured")
        return

    def _gmail_handler(type_: str, payload: dict[str, Any]) -> None:
        ok = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from cores.notifications.db_bridge import record_delivery

            record_delivery(db_id, "gmail", "sent" if ok else "failed", None if ok else "send_error")

    hub = get_hub()
    hub.subscribe("gmail", _gmail_handler)
    logger.info("Gmail channel registered on NotificationHub")


def register_discord_channel() -> None:
    """Register the Discord notification handler on the hub."""
    from cores.notifications.discord import get_discord_adapter
    from cores.notifications.hub import get_hub

    adapter = get_discord_adapter()
    if not adapter.is_enabled:
        logger.info("Discord channel skipped — not configured")
        return

    def _discord_handler(type_: str, payload: dict[str, Any]) -> None:
        ok = adapter.send(
            title=payload.get("title", ""),
            message=payload.get("message", ""),
            priority=payload.get("priority", "medium"),
            metadata=payload.get("metadata"),
        )
        db_id = payload.get("metadata", {}).get("db_id")
        if db_id:
            from cores.notifications.db_bridge import record_delivery

            record_delivery(db_id, "discord", "sent" if ok else "failed", None if ok else "send_error")

    hub = get_hub()
    hub.subscribe("discord", _discord_handler)
    logger.info("Discord channel registered on NotificationHub")


def register_mobile_channel() -> None:
    """Register the mobile push notification handler on the hub.

    Dispatches to:
    - FCM adapter for ``fcm`` devices
    - Web Push (via pywebpush) for ``webpush`` subscriptions stored in the devices table
    """
    from cores.notifications.hub import get_hub
    from database.db import SessionLocal

    hub = get_hub()

    def _mobile_handler(type_: str, payload: dict[str, Any]) -> None:
        title = payload.get("title", "CATEYE")
        message = payload.get("message", "")
        priority = payload.get("priority", "medium")
        metadata = payload.get("metadata", {})
        db_id = metadata.get("db_id")

        # 1. FCM devices
        try:
            from cores.notifications.fcm import get_fcm_adapter

            fcm = get_fcm_adapter()
            if fcm.is_enabled:
                count = fcm.send(title=title, message=message, priority=priority, metadata=metadata)
                if count and db_id:
                    from cores.notifications.db_bridge import record_delivery

                    record_delivery(db_id, "mobile_fcm", "sent")
        except Exception as exc:
            logger.debug("FCM delivery error in mobile channel: %s", exc)

        # 2. Web Push devices (token column stores JSON subscription)
        try:
            session = SessionLocal()
            try:
                from sqlalchemy import text

                rows = session.execute(
                    text("SELECT token FROM devices WHERE platform = 'webpush' AND is_active = 'true'")
                ).fetchall()
            finally:
                session.close()
        except Exception as exc:
            logger.debug("Failed to query webpush devices: %s", exc)
            rows = []

        for row in rows:
            try:
                import json

                token_str = row[0] if isinstance(row, (list, tuple)) else row.token
                sub = json.loads(token_str)
                endpoint = sub.get("endpoint", "")
                keys = sub.get("keys", {})
                if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
                    continue

                try:
                    from pywebpush import webpush

                    vapid_private = os.environ.get("CATEYE_VAPID_PRIVATE_KEY") or None
                    admin_email = os.environ.get("CATEYE_ADMIN_EMAIL", "admin@cateye.local")
                    vapid_claim = {"sub": f"mailto:{admin_email}"}

                    webpush(
                        subscription_info=sub,
                        data=json.dumps({"title": title, "message": message, "priority": priority}),
                        vapid_private_key=vapid_private,
                        vapid_claims=vapid_claim,
                    )
                    if db_id:
                        from cores.notifications.db_bridge import record_delivery

                        record_delivery(db_id, "mobile_webpush", "sent")
                except ImportError:
                    pass
                except Exception as exc:
                    logger.debug("WebPush delivery error: %s", exc)
            except Exception as exc:
                logger.debug("Failed to process webpush subscription: %s", exc)

    hub.subscribe("mobile", _mobile_handler)
    logger.info("Mobile channel registered on NotificationHub")


def register_event_bridge() -> None:
    """Subscribe to EventBus and create hub notifications from key events."""
    from cores.events.event_bus import get_event_bus
    from cores.notifications.hub import get_hub
    from cores.notifications.push import EVENT_PUSH_MAP

    hub = get_hub()

    def _on_event(event_type: str, **payload: Any) -> None:
        mapping = EVENT_PUSH_MAP.get(event_type)
        if not mapping:
            return

        title = mapping["title"]
        message = payload.get("message") or payload.get("body") or payload.get("description", "")
        priority = payload.get("priority", mapping["priority"])
        dedup_key = f"{event_type}-{payload.get('id', '')}"

        channels = ["web"]
        if priority in ("high", "critical"):
            channels.append("desktop")
        discord_events = {
            "finding:created",
            "finding:confirmed",
            "finding:high_priority",
            "report:ready",
            "report:generated",
            "backup:failed",
            "health:warning",
            "update:available",
            "system:started",
            "system:error",
        }
        if event_type in (
            "opportunity:found",
            "quick_win:detected",
            "finding:created",
            "finding:status_changed",
            "system:error",
            "system:degraded",
        ):
            channels.append("mobile")
        if event_type in discord_events:
            channels.append("discord")

        hub.notify(
            type_=event_type.replace(":", "_"),
            title=title,
            message=str(message)[:500],
            severity=priority,
            priority=priority,
            channels=channels,
            metadata={"event_type": event_type, "linked_type": "event", **payload},
            dedup_key=dedup_key,
        )

    bus = get_event_bus()
    bus.subscribe_async("*", _on_event)
    logger.info("Event -> notification bridge started")


def register_ws_forwarder() -> None:
    """Forward hub notifications to WebSocket clients as notification:new events."""
    from cores.notifications.hub import get_hub
    from cores.ws.manager import get_ws_manager

    hub = get_hub()
    manager = get_ws_manager()

    def _forward(notif: object) -> None:
        from cores.notifications.hub import Notification

        if not isinstance(notif, Notification):
            return
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(
                    "notification:new",
                    {
                        "id": notif.db_id or notif.id,
                        "type": notif.type,
                        "title": notif.title,
                        "message": notif.message,
                        "severity": notif.severity,
                        "priority": notif.priority,
                        "timestamp": notif.timestamp,
                        "metadata": notif.metadata,
                    },
                ),
                loop,
            )
        except RuntimeError:
            logger.warning("Failed to forward notification via WS", exc_info=True)

    hub.add_listener(_forward)
    logger.info("WS forwarder registered on NotificationHub")
