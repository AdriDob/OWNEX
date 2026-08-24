"""FASE 5 — legacy adapters must use curated barrier flags, not flatten.

Audit finding: every LegacyOpportunityDweAdapter conversion hardcoded
interview/portfolio/technical_test=False for ALL platforms, silently
understating entry barriers. Flags now come from the curated global
catalog when the platform is known; unknown platforms keep defaults
explicitly (no invented barriers).
"""

from __future__ import annotations

from typing import Any

from cores.direct_work_engine.models import (
    EmploymentType,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)


class _FakeLegacy:
    async def fetch_opportunities(self) -> list[Any]:
        class _Raw:
            id = "r1"
            name = "Fix login bug"
            url = "https://example.com/task/r1"
            description = "d"
            reward = 120
            effort_hours = 2
            tags = ["python"]

        return [_Raw()]


def test_curated_flags_known_platform() -> None:
    from api.adapters.legacy import _curated_barrier_flags

    result = _curated_barrier_flags("freelancer")
    assert result is not None
    assert all(isinstance(v, bool) for v in result)


def test_curated_flags_unknown_platform_is_none() -> None:
    from api.adapters.legacy import _curated_barrier_flags

    assert _curated_barrier_flags("definitely_not_a_platform") is None


def test_conversion_uses_curated_values() -> None:
    """Converted opportunity reflects catalog flags instead of hardcoded False."""
    from api.adapters.legacy import LegacyOpportunityDweAdapter, _curated_barrier_flags

    adapter = LegacyOpportunityDweAdapter(
        legacy=_FakeLegacy(),
        name="Freelancer",
        platform=WorkPlatform.FREELANCER,
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.FREELANCE,
        payment_method=PaymentMethod.BANK_WIRE,
    )
    opp = adapter._convert(
        _FakeLegacy().__dict__
        and type(
            "R",
            (),
            {
                "id": "r2",
                "name": "Task",
                "url": "",
                "description": "",
                "reward": 80,
                "effort_hours": 3,
                "tags": [],
            },
        )()
    )

    expected = _curated_barrier_flags("freelancer")
    assert expected is not None
    assert opp.portfolio_required == expected[0]
    assert opp.interview_required == expected[1]
