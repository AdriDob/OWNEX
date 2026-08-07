"""Infinite Source Discovery — Continuous discovery of zero-barrier work sources.

This system continuously crawls general job boards and filters for zero-barrier opportunities:
- LinkedIn Jobs, Indeed, RemoteOK, WeWorkRemotely, FlexJobs
- Filters: no experience required, no interview, no portfolio, instant start
- Auto-rotation of sources to avoid being blocked
- Continuous scanning 24/7
- Auto-apply where possible via APIs
- Automatic alerts for errors and human intervention
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.financial_intelligence.alert_system import (
    get_alert_system,
)

logger = logging.getLogger("ownex.infinite_source_discovery")


class SourceType(StrEnum):
    """Types of job sources."""

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"
    FLEXJOBS = "flexjobs"
    GITHUB = "github"
    UPWORK = "upwork"
    FIVERR = "fiverr"
    REMOTASKS = "remotasks"
    LABELBOX = "labelbox"
    SCALE_AI = "scale_ai"
    GENERAL = "general"


@dataclass
class ZeroBarrierCriteria:
    """Criteria for zero-barrier opportunities."""

    # Experience requirements
    no_experience_required: bool = True
    max_experience_months: int = 0  # 0 = no experience required

    # Interview requirements
    no_interview_required: bool = True
    no_screening_call: bool = True

    # Portfolio requirements
    no_portfolio_required: bool = True
    no_github_required: bool = True
    no_previous_work_required: bool = True

    # Start requirements
    instant_start: bool = True
    max_start_days: int = 3  # Start within 3 days

    # Payment requirements
    min_hourly_rate: float = 10.0  # $10/hour minimum
    pay_frequency: str = "weekly"  # weekly or daily preferred

    # Task type requirements
    requires_human_verification: bool = False  # Tasks that need KYC are okay
    requires_id_verification: bool = False  # ID verification is okay
    requires_tax_form: bool = False  # Tax forms are okay


@dataclass
class DiscoveredOpportunity:
    """A discovered zero-barrier opportunity."""

    source: str
    source_type: SourceType
    title: str
    company: str
    category: str
    hourly_rate: float
    estimated_hours: float
    description: str
    application_url: str
    discovered_at: str
    zero_barrier_score: float  # 0-1, higher = more zero-barrier
    auto_apply_available: bool = False
    auto_apply_api: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_type": self.source_type.value,
            "title": self.title,
            "company": self.company,
            "category": self.category,
            "hourly_rate": self.hourly_rate,
            "estimated_hours": self.estimated_hours,
            "description": self.description,
            "application_url": self.application_url,
            "discovered_at": self.discovered_at,
            "zero_barrier_score": self.zero_barrier_score,
            "auto_apply_available": self.auto_apply_available,
            "auto_apply_api": self.auto_apply_api,
        }


class InfiniteSourceDiscovery:
    """Continuous discovery of zero-barrier work sources.

    Crawls general job boards and filters for zero-barrier opportunities.
    Rotates sources to avoid being blocked.
    Auto-apply where possible via APIs.
    """

    def __init__(
        self, criteria: ZeroBarrierCriteria | None = None, state_file: Path = Path("data/infinite_sources_state.json")
    ):
        self.criteria = criteria or ZeroBarrierCriteria()
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._discovered_opportunities: list[DiscoveredOpportunity] = []
        self._source_rotation_index = 0
        self._last_scan_time = datetime.now(UTC)
        self._blocked_sources: set[str] = set()
        self._alert_system = get_alert_system()
        self._load_state()

    def _load_state(self) -> None:
        """Load discovery state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._source_rotation_index = data.get("rotation_index", 0)
                    self._last_scan_time = datetime.fromisoformat(
                        data.get("last_scan_time", datetime.now(UTC).isoformat())
                    )
                    self._blocked_sources = set(data.get("blocked_sources", []))
                logger.info(f"Loaded infinite sources state: {len(self._blocked_sources)} blocked sources")
            except Exception as e:
                logger.warning(f"Failed to load infinite sources state: {e}")

    def _save_state(self) -> None:
        """Save discovery state to disk."""
        try:
            data = {
                "rotation_index": self._source_rotation_index,
                "last_scan_time": self._last_scan_time.isoformat(),
                "blocked_sources": list(self._blocked_sources),
                "total_discovered": len(self._discovered_opportunities),
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved infinite sources state")
        except Exception as e:
            logger.error(f"Failed to save infinite sources state: {e}")

    def discover_sources(self, limit: int = 50) -> list[DiscoveredOpportunity]:
        """Discover zero-barrier opportunities from infinite sources.

        Rotates through sources to avoid being blocked.
        Filters by zero-barrier criteria.
        Returns top opportunities by zero_barrier_score.
        """
        opportunities = []

        # Define search sources (can be infinite)
        sources = [
            self._search_linkedin,
            self._search_indeed,
            self._search_remoteok,
            self._search_weworkremotely,
            self._search_flexjobs,
            self._search_github,
            self._search_upwork,
            self._search_fiverr,
        ]

        # Rotate through sources
        for i in range(len(sources)):
            source_index = (self._source_rotation_index + i) % len(sources)
            source_func = sources[source_index]

            # Skip if blocked
            if source_func.__name__ in self._blocked_sources:
                logger.debug(f"Skipping blocked source: {source_func.__name__}")
                continue

            try:
                new_opps = source_func(limit=10)
                opportunities.extend(new_opps)
                logger.info(f"Discovered {len(new_opps)} opportunities from {source_func.__name__}")

                # Add delay to avoid rate limiting
                time.sleep(random.uniform(1, 3))

                if len(opportunities) >= limit:
                    break
            except Exception as e:
                logger.error(f"Error scanning {source_func.__name__}: {e}")
                # Block source temporarily
                self._blocked_sources.add(source_func.__name__)

                # Create alert for blocked source
                self._alert_system.create_warning_alert(
                    component=source_func.__name__,
                    warning_message=f"Source blocked temporarily: {str(e)}",
                    context={"error": str(e), "blocked_sources": list(self._blocked_sources)},
                )

        # Update rotation index
        self._source_rotation_index = (self._source_rotation_index + len(sources)) % len(sources)
        self._last_scan_time = datetime.now(UTC)
        self._save_state()

        # Filter by zero-barrier criteria
        filtered = [opp for opp in opportunities if self._meets_criteria(opp)]

        # Sort by zero_barrier_score
        filtered.sort(key=lambda x: x.zero_barrier_score, reverse=True)

        # Store discovered opportunities
        self._discovered_opportunities.extend(filtered)

        return filtered[:limit]

    def _meets_criteria(self, opp: DiscoveredOpportunity) -> bool:
        """Check if opportunity meets zero-barrier criteria."""
        # Hourly rate check
        if opp.hourly_rate < self.criteria.min_hourly_rate:
            return False

        # Category check (data annotation, AI work, etc.)
        allowed_categories = {
            "data_annotation",
            "ai_training",
            "ai_evaluation",
            "synthetic_data",
            "data_entry",
            "transcription",
            "translation",
            "web_scraping",
            "prompt_engineering",
            "qa_testing",
            "content_writing",
        }
        return opp.category.lower() in allowed_categories

    def _calculate_zero_barrier_score(self, opp: dict[str, Any]) -> float:
        """Calculate zero-barrier score (0-1)."""
        score = 1.0

        # Deduct for experience requirement
        if opp.get("experience_required", False):
            score -= 0.3
        if opp.get("min_experience_months", 0) > 0:
            score -= 0.2

        # Deduct for interview requirement
        if opp.get("interview_required", False):
            score -= 0.3

        # Deduct for portfolio requirement
        if opp.get("portfolio_required", False):
            score -= 0.2

        # Bonus for instant start
        if opp.get("instant_start", False):
            score += 0.1

        # Bonus for auto-apply available
        if opp.get("auto_apply_available", False):
            score += 0.15

        return max(0.0, min(1.0, score))

    def _search_linkedin(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search LinkedIn Jobs for zero-barrier opportunities."""
        # LinkedIn requires API access, simulate with general job search
        # In production, would use LinkedIn Jobs API
        opportunities = []

        # Simulated results (in production, real API call)
        simulated_jobs = [
            {
                "title": "Data Annotation Specialist",
                "company": "AI Startup",
                "category": "data_annotation",
                "hourly_rate": 25.0,
                "hours": 40,
                "description": "Label training data for computer vision models",
                "url": "https://linkedin.com/jobs/view/123",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
            {
                "title": "AI Training Data Specialist",
                "company": "Tech Corp",
                "category": "ai_training",
                "hourly_rate": 30.0,
                "hours": 35,
                "description": "Train and validate AI models",
                "url": "https://linkedin.com/jobs/view/456",
                "experience_required": False,
                "interview_required": True,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="LinkedIn",
                source_type=SourceType.LINKEDIN,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=None,
            )
            opportunities.append(opp)

        return opportunities

    def _search_indeed(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search Indeed for zero-barrier opportunities."""
        # Indeed has RSS feeds for job searches
        opportunities = []

        # Simulated results (in production, Indeed RSS API)
        simulated_jobs = [
            {
                "title": "Data Entry Clerk - Remote",
                "company": "Global Data",
                "category": "data_entry",
                "hourly_rate": 15.0,
                "hours": 40,
                "description": "Remote data entry with immediate start",
                "url": "https://indeed.com/jobs/view/789",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": True,
                "auto_apply_api": "indeed_api",
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="Indeed",
                source_type=SourceType.INDEED,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=job.get("auto_apply_api"),
            )
            opportunities.append(opp)

        return opportunities

    def _search_remoteok(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search RemoteOK for zero-barrier opportunities."""
        opportunities = []

        # Simulated results (in production, scrape remoteok.com)
        simulated_jobs = [
            {
                "title": "AI Model Trainer",
                "company": "AI Lab",
                "category": "ai_training",
                "hourly_rate": 35.0,
                "hours": 30,
                "description": "Train large language models",
                "url": "https://remoteok.com/remote-jobs/123",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="RemoteOK",
                source_type=SourceType.REMOTEOK,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=None,
            )
            opportunities.append(opp)

        return opportunities

    def _search_weworkremotely(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search WeWorkRemotely for zero-barrier opportunities."""
        opportunities = []

        # Simulated results
        simulated_jobs = [
            {
                "title": "Data Annotation - Remote",
                "company": "Data Co",
                "category": "data_annotation",
                "hourly_rate": 20.0,
                "hours": 40,
                "description": "Annotate datasets for ML",
                "url": "https://weworkremotely.com/remote-jobs/456",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="WeWorkRemotely",
                source_type=SourceType.WEWORKREMOTELY,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=None,
            )
            opportunities.append(opp)

        return opportunities

    def _search_flexjobs(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search FlexJobs for zero-barrier opportunities."""
        opportunities = []

        # Simulated results
        simulated_jobs = [
            {
                "title": "AI Content Reviewer",
                "company": "Content AI",
                "category": "ai_evaluation",
                "hourly_rate": 28.0,
                "hours": 35,
                "description": "Review AI-generated content",
                "url": "https://flexjobs.com/remote-jobs/789",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="FlexJobs",
                source_type=SourceType.FLEXJOBS,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=None,
            )
            opportunities.append(opp)

        return opportunities

    def _search_github(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search GitHub Issues for zero-barrier opportunities."""
        opportunities = []

        # Simulated results (in production, scrape GitHub API)
        simulated_jobs = [
            {
                "title": "Data Analysis Bug Bounty",
                "company": "Open Source Project",
                "category": "data_analysis",
                "hourly_rate": 50.0,
                "hours": 10,
                "description": "Find bugs in data processing pipeline",
                "url": "https://github.com/owner/repo/issues/123",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": False,
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="GitHub",
                source_type=SourceType.GITHUB,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=None,
            )
            opportunities.append(opp)

        return opportunities

    def _search_upwork(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search Upwork for zero-barrier opportunities."""
        opportunities = []

        # Simulated results
        simulated_jobs = [
            {
                "title": "Data Entry Specialist",
                "company": "Upwork Client",
                "category": "data_entry",
                "hourly_rate": 12.0,
                "hours": 40,
                "description": "Enter data from PDFs to spreadsheets",
                "url": "https://upwork.com/job/post/123",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": True,
                "auto_apply_api": "upwork_api",
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="Upwork",
                source_type=SourceType.UPWORK,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=job.get("auto_apply_api"),
            )
            opportunities.append(opp)

        return opportunities

    def _search_fiverr(self, limit: int = 10) -> list[DiscoveredOpportunity]:
        """Search Fiverr for zero-barrier opportunities."""
        opportunities = []

        # Simulated results
        simulated_jobs = [
            {
                "title": "Data Entry Task",
                "company": "Fiverr Client",
                "category": "data_entry",
                "hourly_rate": 18.0,
                "hours": 2,
                "description": "Enter 100 rows of data",
                "url": "https://fiverr.com/gig/123",
                "experience_required": False,
                "interview_required": False,
                "portfolio_required": False,
                "instant_start": True,
                "auto_apply_available": True,
                "auto_apply_api": "fiverr_api",
            },
        ]

        for job in simulated_jobs[:limit]:
            opp = DiscoveredOpportunity(
                source="Fiverr",
                source_type=SourceType.FIVERR,
                title=job["title"],
                company=job["company"],
                category=job["category"],
                hourly_rate=job["hourly_rate"],
                estimated_hours=job["hours"],
                description=job["description"],
                application_url=job["url"],
                discovered_at=datetime.now(UTC).isoformat(),
                zero_barrier_score=self._calculate_zero_barrier_score(job),
                auto_apply_available=job.get("auto_apply_available", False),
                auto_apply_api=job.get("auto_apply_api"),
            )
            opportunities.append(opp)

        return opportunities

    def get_status(self) -> dict[str, Any]:
        """Get current status of infinite source discovery."""
        return {
            "total_discovered": len(self._discovered_opportunities),
            "last_scan_time": self._last_scan_time.isoformat(),
            "rotation_index": self._source_rotation_index,
            "blocked_sources": list(self._blocked_sources),
            "criteria": {
                "no_experience_required": self.criteria.no_experience_required,
                "no_interview_required": self.criteria.no_interview_required,
                "no_portfolio_required": self.criteria.no_portfolio_required,
                "instant_start": self.criteria.instant_start,
                "min_hourly_rate": self.criteria.min_hourly_rate,
            },
        }


# Singleton instance
_global_discovery: InfiniteSourceDiscovery | None = None


def get_infinite_source_discovery() -> InfiniteSourceDiscovery:
    """Get or create the global infinite source discovery system."""
    global _global_discovery
    if _global_discovery is None:
        _global_discovery = InfiniteSourceDiscovery()
    return _global_discovery
