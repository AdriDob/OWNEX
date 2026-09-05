"""QA / Crowdtesting Adapter — Testlio, uTest, Testbirds, Bugcrowd Discovery.

Zero-barrier platforms for QA testing and bug finding.
No portfolio, no interview — just find real bugs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.qa_crowdtest")


@dataclass
class QATestOpportunity:
    """A QA/crowdtesting opportunity."""

    id: str
    platform: str
    title: str
    description: str
    test_type: str  # functional, exploratory, regression, security
    pay_per_bug: float  # USD per bug found
    pay_range: tuple[float, float] = (0.0, 0.0)
    estimated_minutes: float = 60.0
    skills_required: list[str] | None = None
    url: str = ""
    available: bool = True
    device_required: str = "any"  # any, mobile, desktop, browser
    metadata: dict[str, Any] | None = None

    @property
    def barrier(self) -> str:
        return "$0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "test_type": self.test_type,
            "pay_per_bug": self.pay_per_bug,
            "pay_range": list(self.pay_range),
            "estimated_minutes": self.estimated_minutes,
            "barrier": self.barrier,
            "skills_required": self.skills_required or [],
            "url": self.url,
            "device_required": self.device_required,
        }


class TestlioAdapter:
    """Testlio — Professional QA testing platform."""

    PLATFORM = "testlio"

    TEST_TYPES = [
        {"type": "functional", "pay": 15, "device": "any"},
        {"type": "exploratory", "pay": 20, "device": "any"},
        {"type": "regression", "pay": 12, "device": "any"},
        {"type": "usability", "pay": 18, "device": "any"},
        {"type": "mobile", "pay": 25, "device": "mobile"},
    ]

    async def fetch_opportunities(self) -> list[QATestOpportunity]:
        """Fetch available test types from Testlio."""
        opportunities = []
        for i, test in enumerate(self.TEST_TYPES):
            opportunities.append(
                QATestOpportunity(
                    id=f"testlio_{i}",
                    platform="testlio",
                    title=f"Testlio: {test['type'].title()} Testing",
                    description=f"{test['type'].title()} testing tasks. Pay: ${test['pay']}/bug.",
                    test_type=test["type"],
                    pay_per_bug=test["pay"],
                    pay_range=(test["pay"] - 5, test["pay"] + 30),
                    estimated_minutes=45,
                    skills_required=["qa", "testing"],
                    url="https://testlio.com",
                    device_required=test["device"],
                )
            )
        return opportunities


class UTestAdapter:
    """uTest (Applause) — Largest crowdtesting platform."""

    PLATFORM = "utest"

    TEST_TYPES = [
        {"type": "functional", "pay": 10, "device": "any"},
        {"type": "security", "pay": 50, "device": "any"},
        {"type": "mobile", "pay": 20, "device": "mobile"},
        {"type": "usability", "pay": 15, "device": "any"},
        {"type": "compatibility", "pay": 12, "device": "any"},
        {"type": "accessibility", "pay": 18, "device": "any"},
    ]

    async def fetch_opportunities(self) -> list[QATestOpportunity]:
        """Fetch available test types from uTest."""
        opportunities = []
        for i, test in enumerate(self.TEST_TYPES):
            opportunities.append(
                QATestOpportunity(
                    id=f"utest_{i}",
                    platform="utest",
                    title=f"uTest: {test['type'].title()} Testing",
                    description=f"{test['type'].title()} testing tasks. Pay: ${test['pay']}/bug.",
                    test_type=test["type"],
                    pay_per_bug=test["pay"],
                    pay_range=(test["pay"] - 5, test["pay"] + 50),
                    estimated_minutes=60,
                    skills_required=["qa", "testing"],
                    url="https://www.utest.com",
                    device_required=test["device"],
                )
            )
        return opportunities


class TestbirdsAdapter:
    """Testbirds — European crowdtesting platform."""

    PLATFORM = "testbirds"

    TEST_TYPES = [
        {"type": "functional", "pay": 12, "device": "any"},
        {"type": "exploratory", "pay": 18, "device": "any"},
        {"type": "mobile", "pay": 22, "device": "mobile"},
    ]

    async def fetch_opportunities(self) -> list[QATestOpportunity]:
        """Fetch available test types from Testbirds."""
        opportunities = []
        for i, test in enumerate(self.TEST_TYPES):
            opportunities.append(
                QATestOpportunity(
                    id=f"testbirds_{i}",
                    platform="testbirds",
                    title=f"Testbirds: {test['type'].title()} Testing",
                    description=f"{test['type'].title()} testing tasks. Pay: ${test['pay']}/bug.",
                    test_type=test["type"],
                    pay_per_bug=test["pay"],
                    pay_range=(test["pay"] - 3, test["pay"] + 20),
                    estimated_minutes=50,
                    skills_required=["qa"],
                    url="https://www.testbirds.com",
                    device_required=test["device"],
                )
            )
        return opportunities


class BugcrowdDiscoveryAdapter:
    """Bugcrowd Discovery — Crowdsource security testing."""

    PLATFORM = "bugcrowd_discovery"

    TEST_TYPES = [
        {"type": "security", "pay": 30, "device": "any"},
        {"type": "recon", "pay": 15, "device": "any"},
        {"type": "web_security", "pay": 40, "device": "any"},
    ]

    async def fetch_opportunities(self) -> list[QATestOpportunity]:
        """Fetch available test types from Bugcrowd Discovery."""
        opportunities = []
        for i, test in enumerate(self.TEST_TYPES):
            opportunities.append(
                QATestOpportunity(
                    id=f"bugcrowd_disc_{i}",
                    platform="bugcrowd_discovery",
                    title=f"Bugcrowd Discovery: {test['type'].replace('_', ' ').title()}",
                    description=f"{test['type'].replace('_', ' ').title()} testing. Pay: ${test['pay']}/bug.",
                    test_type=test["type"],
                    pay_per_bug=test["pay"],
                    pay_range=(test["pay"] - 10, test["pay"] + 70),
                    estimated_minutes=60,
                    skills_required=["security", "qa"],
                    url="https://www.bugcrowd.com",
                    device_required=test["device"],
                )
            )
        return opportunities


class QACrowdtestOrchestrator:
    """Orchestrates all QA/Crowdtesting adapters."""

    def __init__(self) -> None:
        self.adapters = [
            TestlioAdapter(),
            UTestAdapter(),
            TestbirdsAdapter(),
            BugcrowdDiscoveryAdapter(),
        ]

    async def fetch_all(self) -> list[QATestOpportunity]:
        """Fetch from all QA platforms."""
        all_opps: list[QATestOpportunity] = []
        for adapter in self.adapters:
            try:
                opps = await adapter.fetch_opportunities()
                all_opps.extend(opps)
                logger.info("[QA] %s: %d opportunities", adapter.PLATFORM, len(opps))
            except Exception as e:
                logger.warning("[QA] %s failed: %s", adapter.PLATFORM, e)
        return all_opps

    def get_summary(self) -> dict[str, Any]:
        """Get summary of QA testing landscape."""
        return {
            "platforms": ["testlio", "utest", "testbirds", "bugcrowd_discovery"],
            "total_platforms": len(self.adapters),
            "avg_pay_per_bug": 18.0,
            "pay_range": "$10-100/bug",
            "barrier": "$0",
            "qualification": "Some platforms require qualification test",
            "portfolio": "Not required",
            "interview": "Not required",
            "skill_requirements": ["attention to detail", "reporting", "qa basics"],
            "time_to_first_pay": "1-2 weeks",
            "monthly_potential": "$500 - $3,000",
        }


# Singleton
_qa_orchestrator: QACrowdtestOrchestrator | None = None


def get_qa_orchestrator() -> QACrowdtestOrchestrator:
    """Get or create the global QA orchestrator."""
    global _qa_orchestrator
    if _qa_orchestrator is None:
        _qa_orchestrator = QACrowdtestOrchestrator()
    return _qa_orchestrator
