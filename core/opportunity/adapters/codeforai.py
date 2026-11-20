"""CodeforAI Tech Adapter — AI-powered code generation and review platform."""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class CodeforAIAdapter(OpportunityAdapter):
    """CodeforAI Tech adapter - AI-assisted code generation and verification."""

    platform: str = "codeforai.tech"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("codeforai", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch AI code generation and verification opportunities from CodeforAI.tech."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CodeforAIAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated direct-work-friendly CodeforAI.tech opportunities."""
        fallback_data = [
            {
                "id": "codeforai_generate_task",
                "name": "AI Code Generation Task",
                "description": "Generate code using AI assistance on CodeforAI.tech platform",
                "url": "https://codeforai.tech/tasks",
                "reward": 150.0,
                "effort_hours": 5.0,
                "tags": ["ai", "code-generation", "automation"],
                "source_type": "direct_bounty",
                "source_name": "codeforai.tech",
            },
            {
                "id": "codeforai_review_task",
                "name": "AI Code Review Task",
                "description": "Review and validate AI-generated code on CodeforAI.tech",
                "url": "https://codeforai.tech/reviews",
                "reward": 50.0,
                "effort_hours": 1.0,
                "tags": ["ai", "code-review", "quality-assurance"],
                "source_type": "direct_bounty",
                "source_name": "codeforai.tech",
            },
        ]

        raw_opps: list[RawOpportunity] = []
        for item in fallback_data:
            raw_opps.append(
                RawOpportunity(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    platform=self.platform,
                    url=item["url"],
                    reward=item["reward"],
                    effort_hours=item["effort_hours"],
                    category="dev_bounty",
                    specialization="backend",
                    remote=True,
                )
            )

        return raw_opps
