from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from core.revenue_multiplier.config import RevenueMultiplierConfig
from core.revenue_multiplier.models import RevenueCategory, RevenueEvent, RevenueReport

logger = logging.getLogger("orion.revenue.publisher")


class RevenuePublisher:
    def __init__(self, config: RevenueMultiplierConfig) -> None:
        self._config = config
        self._events: list[RevenueEvent] = []
        self._data_dir = Path(config.data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def publish_event(self, event: RevenueEvent) -> None:
        self._events.append(event)
        self._persist_event(event)
        if self._config.event_bus_enabled:
            self._publish_to_eventbus(event)
        logger.info("Revenue event: [%s] %s — $%.2f", event.category.value, event.description, event.amount)

    def _persist_event(self, event: RevenueEvent) -> None:
        path = self._data_dir / "revenue_events.jsonl"
        try:
            with open(path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "source": event.source,
                            "category": event.category.value,
                            "amount": str(event.amount),
                            "currency": event.currency,
                            "description": event.description,
                            "timestamp": event.timestamp.isoformat(),
                            "metadata": event.metadata,
                        }
                    )
                    + "\n"
                )
        except Exception as e:
            logger.error("Failed to persist revenue event: %s", e)

    def _publish_to_eventbus(self, event: RevenueEvent) -> None:
        try:
            from cores.events.event_bus import get_core_event_bus

            bus = get_core_event_bus()
            bus.publish(
                f"revenue:{event.category.value}",
                amount=str(event.amount),
                currency=event.currency,
                description=event.description,
                category=event.category.value,
                source=event.source,
            )
        except Exception as e:
            logger.debug("EventBus unavailable: %s", e)

    def generate_report(self, findings_count: int = 0, trades_count: int = 0) -> RevenueReport:
        monthly = Decimal("0")
        weekly = Decimal("0")
        daily = Decimal("0")
        bounty_total = Decimal("0")
        trading_total = Decimal("0")
        defi_total = Decimal("0")
        now = datetime.now(timezone.utc)

        for ev in self._events:
            if ev.category == RevenueCategory.BUG_BOUNTY:
                bounty_total += ev.amount
            elif ev.category == RevenueCategory.CRYPTO_TRADING:
                trading_total += ev.amount
            elif ev.category == RevenueCategory.DEFI_YIELD:
                defi_total += ev.amount
            if ev.timestamp.date() == now.date():
                daily += ev.amount
            if (now - ev.timestamp).days < 7:
                weekly += ev.amount
            if (now - ev.timestamp).days < 30:
                monthly += ev.amount

        total = bounty_total + trading_total + defi_total
        report = RevenueReport(
            daily_revenue=daily,
            weekly_revenue=weekly,
            monthly_revenue=monthly,
            total_revenue=total,
            bounty_revenue=bounty_total,
            trading_revenue=trading_total,
            defi_revenue=defi_total,
            total_findings=findings_count,
            total_trades=trades_count,
            estimated_yearly=monthly * Decimal("12"),
            generated_at=now,
        )
        self._save_report(report)
        return report

    def _save_report(self, report: RevenueReport) -> None:
        path = self._data_dir / "latest_report.json"
        try:
            import json as j
            from dataclasses import asdict

            path.write_text(j.dumps(asdict(report), default=str, indent=2))
        except Exception as e:
            logger.error("Failed to save report: %s", e)

    def get_recent_events(self, limit: int = 20) -> list[RevenueEvent]:
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def load_history(self) -> list[RevenueEvent]:
        path = self._data_dir / "revenue_events.jsonl"
        if not path.exists():
            return []
        events: list[RevenueEvent] = []
        try:
            for line in path.read_text().strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                events.append(
                    RevenueEvent(
                        source=data.get("source", ""),
                        category=RevenueCategory(data.get("category", "bug_bounty")),
                        amount=Decimal(str(data.get("amount", "0"))),
                        currency=data.get("currency", "USD"),
                        description=data.get("description", ""),
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
                        metadata=data.get("metadata", {}),
                    )
                )
        except Exception as e:
            logger.error("Failed to load revenue history: %s", e)
        return events
