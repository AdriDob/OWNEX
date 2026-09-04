"""Tests for Opportunity Genome — unified opportunity model."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from cores.opportunity_genome.mapper import (
    _category_to_work_stream,
    _score_to_barrier_level,
    map_dwe_opportunity_to_genome,
    map_finding_to_genome,
    map_legacy_opportunity_to_genome,
    map_work_item_to_genome,
)
from cores.opportunity_genome.models import (
    BarrierLevel,
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    ExperienceRequirement,
    GenomeSource,
    GenomeStatus,
    OpportunityCategory,
    OpportunityGenome,
    PaymentMethod,
    WorkPlatform,
    WorkStream,
    ZeroBarrierScore,
)


class MockDWEOpportunity:
    """Mock DWE Opportunity for testing."""

    def __init__(self, **kwargs):
        defaults = {
            "id": "dwe-123",
            "title": "Fix authentication bug",
            "name": "",
            "platform": WorkPlatform.HACKERONE,
            "category": OpportunityCategory.BUG_BOUNTY,
            "subcategory": "auth",
            "url": "https://hackerone.com/reports/123",
            "description": "Auth bypass in login flow",
            "payment": 500.0,
            "currency": "USD",
            "payment_method": PaymentMethod.PAYPAL,
            "time_to_payout_days": 14.0,
            "zero_barrier_score": None,
            "expected_value": 150.0,
            "acceptance_probability": 0.4,
            "risk": 0.3,
            "experience_required": ExperienceLevel.JUNIOR,
            "experience_requirement": ExperienceRequirement.OPTIONAL,
            "entry_mechanism": EntryMechanism.ASSESSMENT,
            "portfolio_required": False,
            "interview_required": False,
            "technical_test_required": False,
            "registration_required": True,
            "technology_tags": ["auth", "jwt", "python"],
            "language_required": "english",
            "estimated_time_hours": 8.0,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "employment_type": EmploymentType.BOUNTY,
            "company": "ExampleCorp",
            "country": "USA",
            "reputation": 0.8,
            "stability": 0.7,
            "compatibility": 0.6,
            "accepts_beginner": True,
            "accepts_freelancers": True,
            "accepts_individuals": True,
            "accepts_ai_tools": True,
            "asynchronous": True,
            "specialization": None,
            "hourly_rate_usd": 62.5,
            "time_to_first_work_hours": 2.0,
            "rate_source": "platform",
        }
        for k, v in {**defaults, **kwargs}.items():
            setattr(self, k, v)


class MockLegacyOpportunity:
    """Mock Legacy Intel Opportunity for testing."""

    def __init__(self, **kwargs):
        defaults = {
            "id": "legacy-456",
            "name": "SQL Injection in API",
            "platform": "bugcrowd",
            "category": "bug_bounty",
            "subcategory": "injection",
            "public_url": "https://bugcrowd.com/reports/456",
            "reward": 1000.0,
            "confidence": 0.7,
            "priority": "high",
            "source": MagicMock(type="platform", name="Bugcrowd"),
            "scope_summary": "API endpoints",
            "reward_info": "$500-$2000",
            "metadata": {},
            "technology_tags": ["sql", "api", "python"],
            "estimated_effort_hours": 12.0,
        }
        # Use provided kwargs to override defaults, including id
        for k, v in {**defaults, **kwargs}.items():
            setattr(self, k, v)


class MockFinding:
    """Mock database Finding for testing."""

    def __init__(self, **kwargs):
        class MockTarget:
            def __init__(self):
                self.id = 1
                self.name = "ExampleApp"
                self.domain = "example.com"

        class MockReport:
            def __init__(self):
                self.id = 10
                self.estimated_reward = 500.0
                self.confirmed_reward = 500.0
                self.currency = "USD"
                self.created_at = datetime.now(UTC)

        defaults = {
            "id": 789,
            "title": "IDOR in user profile",
            "description": "Can access other users' profiles",
            "vulnerability_type": "idor",
            "severity": "high",
            "status": "confirmed",
            "target": MockTarget(),
            "report": MockReport(),
            "created_at": datetime.now(UTC),
        }
        for k, v in {**defaults, **kwargs}.items():
            setattr(self, k, v)


class MockWorkItem:
    """Mock WorkBank WorkItem for testing."""

    def __init__(self, **kwargs):
        defaults = {
            "id": "wi-999",
            "title": "Submit report for IDOR",
            "description": "Prepare and submit IDOR report",
            "platform": WorkPlatform.HACKERONE,
            "category": OpportunityCategory.BUG_BOUNTY,
            "url": "https://hackerone.com/reports/789",
            "reward": 500.0,
            "state": "prepared",
            "deliverables": ["report.md", "poc.py"],
        }
        for k, v in {**defaults, **kwargs}.items():
            setattr(self, k, v)


class TestZeroBarrierScore:
    def test_creation(self):
        zb = ZeroBarrierScore(total=85.5, barrier_level=BarrierLevel.VERY_LOW)
        assert zb.total == 85.5
        assert zb.barrier_level == BarrierLevel.VERY_LOW
        assert zb.barrier_label == "very_low"

    def test_defaults(self):
        zb = ZeroBarrierScore()
        assert zb.total == 0.0
        assert zb.barrier_level == BarrierLevel.HIGH
        assert zb.factors == {}
        assert zb.weights == {}


class TestOpportunityGenome:
    def test_creation_minimal(self):
        genome = OpportunityGenome(
            id="test-1",
            external_id="ext-1",
            platform="hackerone",
            title="Test Opportunity",
            category="bug_bounty",
        )
        assert genome.id == "test-1"
        assert genome.external_id == "ext-1"
        assert genome.platform == "hackerone"
        assert genome.title == "Test Opportunity"
        assert genome.category == "bug_bounty"
        assert genome.source == GenomeSource.DIRECT_WORK
        assert genome.status == GenomeStatus.DISCOVERED

    def test_is_zero_experience(self):
        genome = OpportunityGenome(
            id="test-2",
            external_id="ext-2",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            experience_required=ExperienceLevel.NONE,
        )
        assert genome.is_zero_experience is True

        genome2 = OpportunityGenome(
            id="test-3",
            external_id="ext-3",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            experience_required=ExperienceLevel.SENIOR,
        )
        assert genome2.is_zero_experience is False

    def test_is_zero_barrier(self):
        genome = OpportunityGenome(
            id="test-4",
            external_id="ext-4",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            entry_mechanism=EntryMechanism.DIRECT,
            technical_test_required=False,
            interview_required=False,
            portfolio_required=False,
            experience_required=ExperienceLevel.NONE,
        )
        assert genome.is_zero_barrier is True

        genome2 = OpportunityGenome(
            id="test-5",
            external_id="ext-5",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            entry_mechanism=EntryMechanism.ASSESSMENT,
        )
        assert genome2.is_zero_barrier is False

    def test_international_payment(self):
        genome = OpportunityGenome(
            id="test-6",
            external_id="ext-6",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            payment_method=PaymentMethod.PAYPAL,
        )
        assert genome.international_payment is True

        genome2 = OpportunityGenome(
            id="test-7",
            external_id="ext-7",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            payment_method=PaymentMethod.GIFT_CARD,
        )
        assert genome2.international_payment is False

    def test_effective_experience_requirement(self):
        # Explicit experience_requirement takes precedence
        genome = OpportunityGenome(
            id="test-8",
            external_id="ext-8",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            experience_requirement=ExperienceRequirement.REQUIRED,
            experience_required=ExperienceLevel.NONE,
        )
        assert genome.effective_experience_requirement == ExperienceRequirement.REQUIRED

        # Fallback to experience_required mapping
        genome2 = OpportunityGenome(
            id="test-9",
            external_id="ext-9",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            experience_required=ExperienceLevel.JUNIOR,
        )
        assert genome2.effective_experience_requirement == ExperienceRequirement.OPTIONAL

    def test_serialization(self):
        genome = OpportunityGenome(
            id="test-10",
            external_id="ext-10",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            reward=500.0,
            zero_barrier_score=ZeroBarrierScore(total=75.0),
        )
        data = genome.to_dict()
        assert data["id"] == "test-10"
        assert data["external_id"] == "ext-10"
        assert data["title"] == "Test"
        assert data["reward"] == 500.0
        # zero_barrier_score now serializes as full dict
        assert isinstance(data["zero_barrier_score"], dict)
        assert data["zero_barrier_score"]["total"] == 75.0
        assert data["zero_barrier_score"]["barrier_level"] == "high"
        assert "discovered_at" in data
        assert "updated_at" in data

    def test_deserialization(self):
        original = OpportunityGenome(
            id="test-11",
            external_id="ext-11",
            platform="hackerone",
            title="Test",
            category="bug_bounty",
            reward=500.0,
            zero_barrier_score=ZeroBarrierScore(total=75.0),
        )
        data = original.to_dict()
        restored = OpportunityGenome.from_dict(data)
        assert restored.id == original.id
        assert restored.external_id == original.external_id
        assert restored.title == original.title
        assert restored.reward == original.reward
        assert restored.zero_barrier_score.total == 75.0


class TestMapDWEOpportunity:
    def test_basic_mapping(self):
        dwe_opp = MockDWEOpportunity()
        genome = map_dwe_opportunity_to_genome(dwe_opp)

        assert genome.id == "dwe-123"
        assert genome.external_id == "dwe-123"
        assert genome.source == GenomeSource.DIRECT_WORK
        assert genome.platform == "hackerone"
        assert genome.title == "Fix authentication bug"
        assert genome.category == "bug_bounty"
        assert genome.work_stream == WorkStream.BUG_BOUNTY
        assert genome.reward == 500.0
        assert genome.currency == "USD"
        assert genome.payment_method == "paypal"
        assert genome.time_to_payout_days == 14.0
        assert genome.expected_value == 150.0
        assert genome.acceptance_probability == 0.4
        assert genome.risk_score == 0.3
        assert genome.barrier_score == 0.0  # no zero_barrier_score provided
        assert genome.experience_required == "junior"
        assert genome.experience_requirement == "optional"
        assert genome.entry_mechanism == "assessment"
        assert genome.technology_tags == ["auth", "jwt", "python"]
        assert genome.estimated_time_hours == 8.0
        assert genome.difficulty == "intermediate"
        assert genome.status == GenomeStatus.DISCOVERED
        assert genome.employment_type == "bounty"

    def test_with_zero_barrier_score(self):
        dwe_opp = MockDWEOpportunity()
        dwe_opp.zero_barrier_score = MagicMock(
            total=85.0,
            factors={"remote": 0.9},
            weights={"remote": 1.0},
            barrier_level=BarrierLevel.VERY_LOW,
            reasoning=["Remote work"],
            enablers=["Remote"],
            blockers=[],
        )
        genome = map_dwe_opportunity_to_genome(dwe_opp)
        assert genome.zero_barrier_score is not None
        assert genome.zero_barrier_score.total == 85.0
        assert genome.zero_barrier_score.barrier_level == BarrierLevel.VERY_LOW
        assert genome.barrier_score == 85.0

    def test_category_to_work_stream(self):
        assert _category_to_work_stream("bug_bounty") == WorkStream.BUG_BOUNTY
        assert _category_to_work_stream("dev_bounty") == WorkStream.DEV_BOUNTY
        assert _category_to_work_stream("ai_evaluation") == WorkStream.AI_WORK
        assert _category_to_work_stream("game_development") == WorkStream.GAME_DEV
        assert _category_to_work_stream("open_source") == WorkStream.OPEN_SOURCE
        assert _category_to_work_stream("technical_writing") == WorkStream.TECH_CONTENT


class TestMapLegacyOpportunity:
    def test_basic_mapping(self):
        legacy = MockLegacyOpportunity()
        genome = map_legacy_opportunity_to_genome(legacy)

        assert genome.id == "legacy-456"
        assert genome.external_id == "legacy-456"
        assert genome.source == GenomeSource.LEGACY_INTEL
        assert genome.platform == "bugcrowd"
        assert genome.title == "SQL Injection in API"
        assert genome.category == "bug_bounty"
        assert genome.work_stream == WorkStream.BUG_BOUNTY
        assert genome.reward == 1000.0
        assert genome.technology_tags == ["sql", "api", "python"]
        assert genome.estimated_time_hours == 12.0

    def test_with_score(self):
        legacy = MockLegacyOpportunity()
        legacy.score = MagicMock(overall=0.8)
        genome = map_legacy_opportunity_to_genome(legacy)
        assert genome.zero_barrier_score is not None
        assert genome.zero_barrier_score.total == 80.0
        assert genome.barrier_score == 80.0


class TestMapFinding:
    def test_basic_mapping(self):
        finding = MockFinding()
        genome = map_finding_to_genome(finding)

        assert genome.source == GenomeSource.DATABASE
        assert genome.work_stream == WorkStream.BUG_BOUNTY
        assert genome.category == "bug_bounty"
        assert genome.reward == 500.0
        assert genome.currency == "USD"
        assert "idor" in genome.technology_tags
        assert genome.employment_type == "bounty"
        assert "db_finding_id" in genome.metadata
        assert genome.metadata["target_name"] == "ExampleApp"


class TestMapWorkItem:
    def test_with_opportunity(self):
        work_item = MockWorkItem()
        mock_opp = MockDWEOpportunity(id="wi-opp-1", title="Test OPP")
        work_item.opportunity = mock_opp
        genome = map_work_item_to_genome(work_item)
        assert genome.title == "Test OPP"
        assert genome.source == GenomeSource.DIRECT_WORK

    def test_without_opportunity(self):
        work_item = MockWorkItem(opportunity=None)
        genome = map_work_item_to_genome(work_item)
        assert genome.source == GenomeSource.DIRECT_WORK
        assert genome.title == "Submit report for IDOR"
        assert genome.metadata["work_item_id"] == "wi-999"
        assert genome.metadata["state"] == "prepared"


class TestHelpers:
    def test_score_to_barrier_level(self):

        assert _score_to_barrier_level(0.95) == BarrierLevel.ZERO
        assert _score_to_barrier_level(0.8) == BarrierLevel.VERY_LOW
        assert _score_to_barrier_level(0.6) == BarrierLevel.LOW
        assert _score_to_barrier_level(0.3) == BarrierLevel.MEDIUM
        assert _score_to_barrier_level(0.1) == BarrierLevel.HIGH

    def test_category_to_work_stream(self):
        assert _category_to_work_stream("bug_bounty") == WorkStream.BUG_BOUNTY
        assert _category_to_work_stream("dev_bounty") == WorkStream.DEV_BOUNTY
        assert _category_to_work_stream("ai_evaluation") == WorkStream.AI_WORK
        assert _category_to_work_stream("game_development") == WorkStream.GAME_DEV
        assert _category_to_work_stream("open_source") == WorkStream.OPEN_SOURCE
        assert _category_to_work_stream("technical_writing") == WorkStream.TECH_CONTENT
        assert _category_to_work_stream("unknown") == WorkStream.DEV_BOUNTY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
