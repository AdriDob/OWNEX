#!/usr/bin/env python3
"""
OWNEX Platform Connectors - Continuous Integration for All Platforms
Continuous operation: Y// monitoring 24/7, real-time rewards
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from cores.events.event_bus import get_event_bus
from cores.observability import timer

logger = logging.getLogger("ownex.platform_connectors")


class PlatformType(Enum):
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"
    CRYPTO = "crypto"
    SOCIAL = "social"


@dataclass
class PlatformConfig:
    name: str
    platform_type: PlatformType
    base_url: str
    api_key: str
    refresh_interval: int  # seconds
    enabled: bool = True
    rate_limit: int = 60
    last_refresh: datetime | None = None
    error_count: int = 0


@dataclass
class PlatformOpportunity:
    id: str
    platform: PlatformType
    title: str
    description: str
    reward: float
    currency: str
    difficulty: float
    estimated_time: int
    deadline: datetime | None
    platform_url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PlatformConnector:
    """Base class for all platform connectors"""

    def __init__(self, config: PlatformConfig):
        self.config = config
        self.opportunities: list[PlatformOpportunity] = []
        self.client = None  # Will be initialized by subclasses
        self.event_bus = get_event_bus()

    async def start_monitoring(self):
        """Start continuous monitoring for this platform"""
        logger.info(f"Starting continuous monitoring for {self.config.name}")

        # Trigger initial discovery
        await self._discover_opportunities()

        # Start continuous refresh loop
        while self.config.enabled:
            try:
                with timer(f"platform.{self.config.name}.refresh"):
                    await self._discover_opportunities()
                    self.config.last_refresh = datetime.now(UTC)

                    # Emit event for new opportunities discovered
                    await self._emit_opportunity_events()

                # Wait for next refresh based on interval
                await asyncio.sleep(self.config.refresh_interval)

            except Exception as e:
                logger.error(f"Error in platform {self.config.name}: {e}")
                self.config.error_count += 1
                # Exponential backoff on errors
                await asyncio.sleep(min(30, 2**self.config.error_count))

    async def _discover_opportunities(self):
        """Override in subclasses"""
        raise NotImplementedError()

    async def _emit_opportunity_events(self):
        """Emit EventBus events for new opportunities"""
        for opportunity in self.opportunities:
            event = {
                "platform": self.config.platform_type.value,
                "platform_name": self.config.name,
                "opportunity": {
                    "id": opportunity.id,
                    "title": opportunity.title,
                    "reward": opportunity.reward,
                    "currency": opportunity.currency,
                    "difficulty": opportunity.difficulty,
                    "deadline": opportunity.deadline,
                    "metadata": opportunity.metadata,
                },
                "timestamp": opportunity.discovered_at.isoformat(),
            }

            # Emit different events based on opportunity characteristics
            if opportunity.reward > 500:
                self.event_bus.publish("opportunity.high_value", event)
            if opportunity.deadline and opportunity.deadline < datetime.now(UTC) + timedelta(hours=24):
                self.event_bus.publish("opportunity.expiring_soon", event)

            self.event_bus.publish("opportunity.discovered", event)

    async def stop_monitoring(self):
        """Stop monitoring this platform"""
        self.config.enabled = False
        logger.info(f"Stopping monitoring for {self.config.name}")


class BugBountyConnector(PlatformConnector):
    """Connector for Bug Bounty platforms"""

    async def _discover_opportunities(self):
        """Discover bug bounty opportunities"""
        # Simulated bug bounty discovery
        # In real implementation, would call HackerOne, Bugcrowd, Intigriti APIs

        sample_opportunities = [
            PlatformOpportunity(
                id=f"bug_{datetime.now().timestamp()}_1",
                platform=PlatformType.BUG_BOUNTY,
                title="SQL Injection - Authentication Bypass",
                description="Find SQL injection in login endpoints",
                reward=2500.0,
                currency="USD",
                difficulty=8.5,
                estimated_time=4,
                deadline=datetime.now(UTC) + timedelta(days=7),
                platform_url="https://hackerone.com/programs/example",
                metadata={"severity": "critical", "category": "web"},
            ),
            PlatformOpportunity(
                id=f"bug_{datetime.now().timestamp()}_2",
                platform=PlatformType.BUG_BOUNTY,
                title="XSS in Product Search",
                description="Stored XSS in search functionality",
                reward=1500.0,
                currency="USD",
                difficulty=7.0,
                estimated_time=2,
                deadline=datetime.now(UTC) + timedelta(days=3),
                platform_url="https://bugcrowd.com/programs/example",
                metadata={"severity": "high", "category": "xss"},
            ),
        ]

        # Simulate some new opportunities
        for opp in sample_opportunities:
            if not any(o.id == opp.id for o in self.opportunities):
                self.opportunities.append(opp)
                logger.info(f"Discovered bug bounty opportunity: {opp.title} - ${opp.reward}")


class DevBountyConnector(PlatformConnector):
    """Connector for Development Bounty platforms"""

    async def _discover_opportunities(self):
        """Discover dev bounty opportunities"""
        sample_opportunities = [
            PlatformOpportunity(
                id=f"dev_{datetime.now().timestamp()}_1",
                platform=PlatformType.DEV_BOUNTY,
                title="Implement OAuth2 for API",
                description="Add OAuth2 authentication to web API",
                reward=800.0,
                currency="USD",
                difficulty=7.5,
                estimated_time=6,
                deadline=datetime.now(UTC) + timedelta(days=14),
                platform_url="https://github.com/owner/repo/issues/123",
                metadata={"language": "python", "type": "feature"},
            ),
            PlatformOpportunity(
                id=f"dev_{datetime.now().timestamp()}_2",
                platform=PlatformType.DEV_BOUNTY,
                title="Bug Bounty Platform Integration",
                description="Integrate bug bounty platform with reporting",
                reward=1200.0,
                currency="USD",
                difficulty=9.0,
                estimated_time=8,
                deadline=datetime.now(UTC) + timedelta(days=21),
                platform_url="https://bountysource.com/programs/example",
                metadata={"language": "typescript", "type": "integration"},
            ),
        ]

        for opp in sample_opportunities:
            if not any(o.id == opp.id for o in self.opportunities):
                self.opportunities.append(opp)
                logger.info(f"Discovered dev bounty opportunity: {opp.title} - ${opp.reward}")


class DataAnnotationConnector(PlatformConnector):
    """Connector for Data Annotation platforms"""

    async def _discover_opportunities(self):
        """Discover data annotation opportunities"""
        sample_opportunities = [
            PlatformOpportunity(
                id=f"data_{datetime.now().timestamp()}_1",
                platform=PlatformType.DATA_ANNOTATION,
                title="Image Classification Dataset",
                description="Classify 10k images into 5 categories",
                reward=150.0,
                currency="USD",
                difficulty=4.0,
                estimated_time=12,
                deadline=datetime.now(UTC) + timedelta(days=30),
                platform_url="https://labelbox.com/projects/example",
                metadata={"type": "computer_vision", "size": "10k_items"},
            ),
            PlatformOpportunity(
                id=f"data_{datetime.now().timestamp()}_2",
                platform=PlatformType.DATA_ANNOTATION,
                title="Text Sentiment Analysis",
                description="Analyze sentiment in 50k customer reviews",
                reward=200.0,
                currency="USD",
                difficulty=3.5,
                estimated_time=8,
                deadline=datetime.now(UTC) + timedelta(days=20),
                platform_url="https://scale.ai/projects/example",
                metadata={"type": "nlp", "size": "50k_items"},
            ),
        ]

        for opp in sample_opportunities:
            if not any(o.id == opp.id for o in self.opportunities):
                self.opportunities.append(opp)
                logger.info(f"Discovered data annotation opportunity: {opp.title} - ${opp.reward}")


class PlatformConnectorsManager:
    """Manages all platform connectors"""

    def __init__(self):
        self.connectors: dict[str, PlatformConnector] = {}
        self.event_bus = get_event_bus()

    def add_platform(self, config: PlatformConfig):
        """Add a new platform to monitor"""
        connector = self._create_connector(config)
        if connector:
            self.connectors[config.name] = connector
            logger.info(f"Added platform connector: {config.name}")

    def _create_connector(self, config: PlatformConfig) -> PlatformConnector | None:
        """Create appropriate connector based on platform type"""
        if config.platform_type == PlatformType.BUG_BOUNTY:
            return BugBountyConnector(config)
        elif config.platform_type == PlatformType.DEV_BOUNTY:
            return DevBountyConnector(config)
        elif config.platform_type == PlatformType.DATA_ANNOTATION:
            return DataAnnotationConnector(config)
        else:
            logger.warning(f"Unsupported platform type: {config.platform_type}")
            return None

    async def start_all_monitoring(self):
        """Start monitoring for all platforms"""
        logger.info("Starting monitoring for all platforms")

        # Start all platforms concurrently
        tasks = []
        for connector in self.connectors.values():
            task = asyncio.create_task(connector.start_monitoring())
            tasks.append(task)

        # Wait for all tasks (they run indefinitely)
        await asyncio.gather(*tasks)

    async def stop_all_monitoring(self):
        """Stop monitoring for all platforms"""
        logger.info("Stopping all platform monitoring")
        for connector in self.connectors.values():
            await connector.stop_monitoring()

    def get_all_opportunities(self) -> list[PlatformOpportunity]:
        """Get all opportunities from all platforms"""
        all_opps = []
        for connector in self.connectors.values():
            all_opps.extend(connector.opportunities)
        return all_opps


async def main_platform_connectors():
    """Main function for standalone execution"""
    logger.info("Starting OWNEX Platform Connectors")

    # Initialize EventBus
    event_bus = get_event_bus()

    # Setup sample platforms - in production, would read from config
    bug_bounty_config = PlatformConfig(
        name="hackerone",
        platform_type=PlatformType.BUG_BOUNTY,
        base_url="https://api.hackerone.com/v1",
        api_key="[REDACTED]",
        refresh_interval=300,  # 5 minutes
    )

    dev_bounty_config = PlatformConfig(
        name="bountysource",
        platform_type=PlatformType.DEV_BOUNTY,
        base_url="https://api.bountysource.com",
        api_key="[REDACTED]",
        refresh_interval=600,  # 10 minutes
    )

    data_annotation_config = PlatformConfig(
        name="labelbox",
        platform_type=PlatformType.DATA_ANNOTATION,
        base_url="https://api.labelbox.com/graphql",
        api_key="[REDACTED]",
        refresh_interval=900,  # 15 minutes
    )

    # Create manager and add platforms
    manager = PlatformConnectorsManager()
    manager.add_platform(bug_bounty_config)
    manager.add_platform(dev_bounty_config)
    manager.add_platform(data_annotation_config)

    # Start monitoring (this runs continuously)
    await manager.start_all_monitoring()


if __name__ == "__main__":
    # For testing purposes
    asyncio.run(main_platform_connectors())
