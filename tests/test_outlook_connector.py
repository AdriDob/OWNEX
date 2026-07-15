"""Tests for Outlook Graph API connector."""

from __future__ import annotations

from cores.integrations.outlook.connector import (
    OutlookCalendarEvent,
    OutlookConnector,
    OutlookContact,
    OutlookEmail,
    get_outlook_connector,
    reset_outlook_connector,
)


def test_outlook_email_dataclass() -> None:
    email = OutlookEmail(
        id="msg1",
        subject="Test",
        from_address="a@b.com",
        to_addresses=["c@d.com"],
        body_preview="Hello",
        received_at="2026-01-01T00:00:00Z",
        is_read=False,
        has_attachments=True,
        importance="high",
    )
    assert email.id == "msg1"
    assert email.subject == "Test"
    assert email.is_read is False
    assert email.has_attachments is True


def test_outlook_calendar_event_dataclass() -> None:
    event = OutlookCalendarEvent(
        id="evt1",
        subject="Meeting",
        start_time="2026-01-01T10:00:00Z",
        end_time="2026-01-01T11:00:00Z",
        location="Office",
        organizer="boss@corp.com",
        is_online=True,
    )
    assert event.subject == "Meeting"
    assert event.is_online is True
    assert event.organizer == "boss@corp.com"


def test_outlook_contact_dataclass() -> None:
    contact = OutlookContact(
        id="c1",
        display_name="John Doe",
        email="john@example.com",
        phone="+123456789",
        company="Acme Inc",
        job_title="Engineer",
    )
    assert contact.display_name == "John Doe"
    assert contact.company == "Acme Inc"


def test_connector_initialization() -> None:
    connector = OutlookConnector()
    assert connector.is_connected() is False


def test_connector_not_connected_by_default() -> None:
    connector = OutlookConnector()
    # Without credentials, connect should fail
    import asyncio

    result = asyncio.run(connector.connect())
    assert result is False


def test_connector_health_when_not_connected() -> None:
    connector = OutlookConnector()
    import asyncio

    health = asyncio.run(connector.health())
    assert health.get("connected") is False


def test_connector_list_emails_when_not_connected() -> None:
    connector = OutlookConnector()
    import asyncio

    emails = asyncio.run(connector.list_emails())
    assert emails == []


def test_connector_send_email_when_not_connected() -> None:
    connector = OutlookConnector()
    import asyncio

    result = asyncio.run(
        connector.send_email(
            to=["test@test.com"],
            subject="Test",
            body="<p>Test</p>",
        )
    )
    assert result is False


def test_connector_list_events_when_not_connected() -> None:
    connector = OutlookConnector()
    import asyncio

    events = asyncio.run(connector.list_calendar_events())
    assert events == []


def test_connector_list_contacts_when_not_connected() -> None:
    connector = OutlookConnector()
    import asyncio

    contacts = asyncio.run(connector.list_contacts())
    assert contacts == []


def test_get_outlook_connector_singleton() -> None:
    reset_outlook_connector()
    c1 = get_outlook_connector()
    c2 = get_outlook_connector()
    assert c1 is c2


def test_reset_outlook_connector_clears_singleton() -> None:
    reset_outlook_connector()
    c1 = get_outlook_connector()
    reset_outlook_connector()
    c2 = get_outlook_connector()
    assert c1 is not c2
