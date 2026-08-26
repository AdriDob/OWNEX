"""Capital Timeline — auditable chronological timeline of all capital events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.capital.timeline")


class TimelineEventType(StrEnum):
    # Capital events
    CAPITAL_DEPOSIT = "capital_deposit"
    CAPITAL_WITHDRAWAL = "capital_withdrawal"
    CAPITAL_TRANSFER = "capital_transfer"

    # Income events
    INCOME_RECEIVED = "income_received"
    INCOME_EXPECTED = "income_expected"
    INCOME_VERIFIED = "income_verified"
    INCOME_LOST = "income_lost"

    # Payout events
    PAYOUT_RECEIVED = "payout_received"
    PAYOUT_PENDING = "payout_pending"
    PAYOUT_DELAYED = "payout_delayed"
    PAYOUT_FAILED = "payout_failed"

    # Investment events
    INVESTMENT_MADE = "investment_made"
    INVESTMENT_SOLD = "investment_sold"
    INVESTMENT_DIVIDEND = "investment_dividend"
    INVESTMENT_LOSS = "investment_loss"
    INVESTMENT_GAIN = "investment_gain"

    # Risk events
    RISK_THRESHOLD_BREACHED = "risk_threshold_breached"
    RISK_IMPROVED = "risk_improved"

    # Runway events
    RUNWAY_CRITICAL = "runway_critical"
    RUNWAY_WARNING = "runway_warning"
    RUNWAY_EXTENDED = "runway_extended"

    # Allocation events
    ALLOCATION_MADE = "allocation_made"
    ALLOCATION_CHANGED = "allocation_changed"
    ALLOCATION_RECOMMENDED = "allocation_recommended"

    # Goal events
    GOAL_SET = "goal_set"
    GOAL_PROGRESS = "goal_progress"
    GOAL_ACHIEVED = "goal_achieved"
    GOAL_MISSED = "goal_missed"

    # Diversification events
    DIVERSIFICATION_IMPROVED = "diversification_improved"
    DIVERSIFICATION_WORSENED = "diversification_worsened"

    # Alert events
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_DISMISSED = "alert_dismissed"

    # System events
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"


class TimelineSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TimelineEvent:
    """A single event in the capital timeline."""

    id: str
    event_type: TimelineEventType
    severity: TimelineSeverity
    title: str
    description: str
    amount: float | None = None
    currency: str = "USD"
    platform: str | None = None
    source: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class TimelineFilter:
    """Filter for querying timeline events."""

    def __init__(
        self,
        event_types: list[TimelineEventType] | None = None,
        severity: list[TimelineSeverity] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        platforms: list[str] | None = None,
        tags: list[str] | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        has_evidence: bool | None = None,
        search_query: str | None = None,
    ):
        self.event_types = event_types
        self.severity = severity
        self.start_date = start_date
        self.end_date = end_date
        self.platforms = platforms
        self.tags = tags
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.has_evidence = has_evidence
        self.search_query = search_query


class CapitalTimeline:
    """Manages the auditable capital timeline."""

    def __init__(self) -> None:
        self._events: dict[str, TimelineEvent] = {}
        self._index_by_type: dict[TimelineEventType, list[str]] = {}
        self._index_by_platform: dict[str, list[str]] = {}
        self._index_by_date: list[str] = []  # sorted event IDs by timestamp
        self._index_by_tag: dict[str, list[str]] = {}

    def add_event(self, event: TimelineEvent) -> str:
        """Add an event to the timeline."""
        if event.id in self._events:
            return event.id

        self._events[event.id] = event
        self._index_by_type.setdefault(event.event_type, []).append(event.id)
        if event.platform:
            self._index_by_platform.setdefault(event.platform, []).append(event.id)
        self._index_by_date.append(event.id)
        self._index_by_date.sort(key=lambda eid: self._events[eid].timestamp, reverse=True)
        for tag in event.tags:
            self._index_by_tag.setdefault(tag, []).append(event.id)
        return event.id

    def add_event_from_ledger(self, ledger_entry: dict[str, Any] | Any) -> str | None:
        """Create timeline event from ledger entry."""
        try:
            from core.execution_queue.models import LedgerEntryData

            if isinstance(ledger_entry, LedgerEntryData):
                entry_dict = {
                    "event": ledger_entry.event.value
                    if hasattr(ledger_entry.event, "value")
                    else str(ledger_entry.event),
                    "amount": ledger_entry.amount,
                    "currency": ledger_entry.currency,
                    "platform": ledger_entry.platform,
                    "source": ledger_entry.source,
                    "source_id": ledger_entry.source_id,
                    "description": ledger_entry.description,
                    "metadata": ledger_entry.metadata,
                    "entry_id": ledger_entry.entry_id,
                    "timestamp": ledger_entry.timestamp,
                }
            else:
                entry_dict = dict(ledger_entry) if hasattr(ledger_entry, "__iter__") else {}
        except Exception:
            entry_dict = dict(ledger_entry) if hasattr(ledger_entry, "__iter__") else {}

        try:
            event_type_str = self._map_ledger_event(entry_dict.get("event", ""))
            if not event_type_str:
                return None
            event_type = TimelineEventType(event_type_str)

            severity_str = self._get_severity_for_event(entry_dict)
            severity = TimelineSeverity(severity_str)

            timestamp = entry_dict.get("timestamp") or datetime.now(UTC).isoformat()

            event = TimelineEvent(
                id=f"tl_{entry_dict.get('entry_id', '')}",
                event_type=event_type,
                severity=severity,
                title=self._generate_title(entry_dict),
                description=self._generate_description(entry_dict),
                amount=entry_dict.get("amount"),
                currency=entry_dict.get("currency", "USD"),
                platform=entry_dict.get("platform"),
                source="ledger",
                source_id=entry_dict.get("entry_id"),
                metadata={
                    "event": entry_dict.get("event"),
                    "source": entry_dict.get("source"),
                    "description": entry_dict.get("description"),
                    "metadata": entry_dict.get("metadata"),
                },
                evidence_urls=self._get_evidence_urls(entry_dict),
                tags=self._generate_tags(entry_dict),
                timestamp=timestamp,
            )
            return self.add_event(event)
        except Exception as e:
            logger.warning(f"Failed to create timeline event from ledger: {e}")
            return None

    def _map_ledger_event(self, event: str) -> str | None:
        """Map ledger event to timeline event type."""
        mapping = {
            "bounty_created": "INCOME_EXPECTED",
            "bounty_pending": "INCOME_EXPECTED",
            "bounty_approved": "INCOME_VERIFIED",
            "bounty_rejected": "INCOME_LOST",
            "payout_received": "PAYOUT_RECEIVED",
            "withdrawal_requested": "CAPITAL_WITHDRAWAL",
            "withdrawal_processing": "CAPITAL_WITHDRAWAL",
            "withdrawal_completed": "CAPITAL_WITHDRAWAL",
            "withdrawal_failed": "INCOME_LOST",
            "adjustment_manual": "CAPITAL_DEPOSIT",
            "fee_deducted": "CAPITAL_WITHDRAWAL",
            "currency_converted": "CAPITAL_TRANSFER",
            "crypto_deposit": "CAPITAL_DEPOSIT",
            "crypto_withdrawal": "CAPITAL_WITHDRAWAL",
            "crypto_staking_reward": "INVESTMENT_DIVIDEND",
            "crypto_defi_yield": "INVESTMENT_DIVIDEND",
            "crypto_swap": "CAPITAL_TRANSFER",
            "crypto_gas_fee": "CAPITAL_WITHDRAWAL",
            "crypto_airdrop": "INCOME_RECEIVED",
            "exchange_trade": "INVESTMENT_MADE",
            "exchange_fee": "CAPITAL_WITHDRAWAL",
        }
        return mapping.get(event)

    def _get_severity_for_event(self, entry: dict[str, Any]) -> str:
        event = entry.get("event", "")
        amount = abs(entry.get("amount", 0))
        if event in ("payout_received", "crypto_deposit", "crypto_staking_reward", "crypto_airdrop"):
            return "high" if amount > 1000 else "medium"
        if event in ("withdrawal_completed", "crypto_withdrawal", "fee_deducted", "crypto_gas_fee"):
            return "medium"
        if event in ("withdrawal_failed", "bounty_rejected", "crypto_swap"):
            return "high"
        if event in ("crypto_staking_reward", "crypto_defi_yield", "crypto_airdrop"):
            return "medium"
        return "info"

    def _generate_title(self, entry: dict[str, Any]) -> str:
        event = entry.get("event", "")
        amount = entry.get("amount", 0)
        currency = entry.get("currency", "USD")
        platform = entry.get("platform", "")

        titles = {
            "bounty_created": f"Bounty creado: {platform}",
            "bounty_pending": f"Bounty pendiente: {platform}",
            "bounty_approved": f"Bounty aprobado: {platform} - {currency} {amount:,.2f}",
            "bounty_rejected": f"Bounty rechazado: {platform}",
            "payout_received": f"Payout recibido: {currency} {amount:,.2f} de {platform}",
            "withdrawal_requested": f"Retiro solicitado: {currency} {amount:,.2f}",
            "withdrawal_completed": f"Retiro completado: {currency} {amount:,.2f}",
            "withdrawal_failed": f"Retiro fallido: {platform}",
            "adjustment_manual": f"Ajuste manual: {currency} {amount:,.2f}",
            "crypto_deposit": f"Depósito crypto: {currency} {amount:,.2f}",
            "crypto_withdrawal": f"Retiro crypto: {currency} {amount:,.2f}",
            "crypto_staking_reward": f"Staking reward: {currency} {amount:,.2f}",
            "crypto_airdrop": f"Airdrop: {currency} {amount:,.2f}",
        }
        return titles.get(event, f"Evento: {event}")

    def _generate_description(self, entry: dict[str, Any]) -> str:
        desc = entry.get("description", "")
        if desc:
            return desc
        event = entry.get("event", "")
        platform = entry.get("platform", "")
        return f"Evento {event} en {platform}" if platform else f"Evento {event}"

    def _get_evidence_urls(self, entry: dict[str, Any]) -> list[str]:
        urls = []
        metadata = entry.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json

                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if isinstance(metadata, dict):
            for key in ("url", "evidence_url", "report_url", "submission_url", "external_url"):
                if metadata.get(key):
                    urls.append(metadata[key])
        return urls

    def _generate_tags(self, entry: dict[str, Any]) -> list[str]:
        tags = []
        event = entry.get("event", "")
        platform = entry.get("platform", "")
        if platform:
            tags.append(platform.lower())
        if "payout" in event:
            tags.append("payout")
        if "withdrawal" in event:
            tags.append("withdrawal")
        if "crypto" in event:
            tags.append("crypto")
        if "bounty" in event:
            tags.append("bounty")
        if "investment" in event:
            tags.append("investment")
        return tags

    # Query methods
    def get_events(
        self,
        filter: TimelineFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TimelineEvent]:
        """Get events with optional filtering and pagination."""
        events = list(self._events.values())

        if filter:
            if filter.event_types:
                events = [e for e in events if e.event_type in filter.event_types]
            if filter.severity:
                events = [e for e in events if e.severity in filter.severity]
            if filter.start_date:
                events = [
                    e for e in events if datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")) >= filter.start_date
                ]
            if filter.end_date:
                events = [
                    e for e in events if datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")) <= filter.end_date
                ]
            if filter.platforms:
                events = [
                    e for e in events if e.platform and e.platform.lower() in [p.lower() for p in filter.platforms]
                ]
            if filter.tags:
                events = [e for e in events if any(t in e.tags for t in filter.tags)]
            if filter.min_amount is not None:
                events = [e for e in events if e.amount is not None and e.amount >= filter.min_amount]
            if filter.max_amount is not None:
                events = [e for e in events if e.amount is not None and e.amount <= filter.max_amount]
            if filter.has_evidence is not None:
                events = [e for e in events if (bool(e.evidence_urls) == filter.has_evidence)]
            if filter.search_query:
                q = filter.search_query.lower()
                events = [e for e in events if q in e.title.lower() or q in e.description.lower()]

        # Sort by timestamp descending
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[offset : offset + limit]

    def get_event(self, event_id: str) -> TimelineEvent | None:
        return self._events.get(event_id)

    def get_events_by_type(self, event_type: TimelineEventType, limit: int = 50) -> list[TimelineEvent]:
        ids = self._index_by_type.get(event_type, [])
        events = [self._events[eid] for eid in ids if eid in self._events]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_events_by_platform(self, platform: str, limit: int = 50) -> list[TimelineEvent]:
        ids = self._index_by_platform.get(platform.lower(), [])
        events = [self._events[eid] for eid in ids if eid in self._events]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_events_by_tag(self, tag: str, limit: int = 50) -> list[TimelineEvent]:
        ids = self._index_by_tag.get(tag.lower(), [])
        events = [self._events[eid] for eid in ids if eid in self._events]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_recent(self, limit: int = 20) -> list[TimelineEvent]:
        events = [self._events[eid] for eid in self._index_by_date[:limit] if eid in self._events]
        return events

    def get_summary(self, days: int = 30) -> dict[str, Any]:
        """Get timeline summary for last N days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        recent = [
            e for e in self._events.values() if datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")) >= cutoff
        ]

        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        total_amount = 0.0
        income_amount = 0.0
        expense_amount = 0.0

        for e in recent:
            by_type[e.event_type.value] = by_type.get(e.event_type.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
            if e.amount:
                total_amount += e.amount
                if e.event_type in (
                    "INCOME_RECEIVED",
                    "INCOME_VERIFIED",
                    "PAYOUT_RECEIVED",
                    "INCOME_RECEIVED",
                    "INVESTMENT_DIVIDEND",
                    "INVESTMENT_GAIN",
                    "CRYPTO_AIRDROP",
                    "CAPITAL_DEPOSIT",
                ):
                    income_amount += e.amount
                else:
                    expense_amount += e.amount

        return {
            "period_days": days,
            "total_events": len(recent),
            "by_type": by_type,
            "by_severity": by_severity,
            "total_amount": round(total_amount, 2),
            "income_amount": round(income_amount, 2),
            "expense_amount": round(expense_amount, 2),
            "net_flow": round(income_amount - expense_amount, 2),
        }

    def rebuild_from_ledger(self) -> int:
        """Rebuild entire timeline from ledger."""
        try:
            from cores.ledger import _all_entries

            entries = _all_entries()
            self._events.clear()
            self._index_by_type.clear()
            self._index_by_platform.clear()
            self._index_by_date.clear()
            self._index_by_tag.clear()

            count = 0
            for entry in entries:
                if self.add_event_from_ledger(entry):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Failed to rebuild timeline: {e}")
            return 0


_timeline: CapitalTimeline | None = None


def get_timeline() -> CapitalTimeline:
    global _timeline
    if _timeline is None:
        _timeline = CapitalTimeline()
    return _timeline
