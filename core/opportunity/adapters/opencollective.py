from __future__ import annotations

from typing import Any

import httpx

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class OpenCollectiveAdapter(OpportunityAdapter):
    """Adapter for Open Collective platform."""

    platform = "opencollective"
    cycle = "forge"

    GRAPHQL_ENDPOINT = "https://api.opencollective.com/graphql/v2"

    # GraphQL query for collectives with funding opportunities
    SEARCH_COLLECTIVES_QUERY = """
    query SearchCollectives($slug: String, $limit: Int) {
        collectives(slug: $slug, limit: $limit) {
            nodes {
                id
                slug
                name
                description
                image
                currency
                totalAmountReceived {
                    value
                    currency
                }
                tiers(limit: 10) {
                    nodes {
                        id
                        name
                        description
                        amount {
                            value
                            currency
                        }
                        type
                    }
                }
                members(roles: ["BACKER", "CONTRIBUTOR"], limit: 5) {
                    nodes {
                        id
                        name
                        role
                    }
                }
            }
        }
    }
    """

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch collectives that accept contributions/funding."""
        if not self.is_enabled():
            return []

        config = self.get_config("opencollective", {})
        collectives_slugs = config.get(
            "collectives",
            [
                "webpack",
                "babel",
                "eslint",
                "vuejs",
                "react",
                "nodejs",
                "rust-lang",
                "python",
                "django",
                "rails",
                "laravel",
                "opensource",
                "maintainers",
                "contributors",
            ],
        )

        raw_opps = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for slug in collectives_slugs[:10]:  # Limit to avoid rate limits
                try:
                    variables = {"slug": slug, "limit": 1}
                    response = await client.post(
                        self.GRAPHQL_ENDPOINT,
                        json={"query": self.SEARCH_COLLECTIVES_QUERY, "variables": variables},
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code != 200:
                        continue

                    data = response.json()
                    collectives = data.get("data", {}).get("collectives", {}).get("nodes", [])

                    for collective in collectives:
                        # Create opportunities from tiers (contribution levels)
                        for tier in collective.get("tiers", {}).get("nodes", []):
                            if tier.get("type") in ["CONTRIBUTION", "BACKER"]:
                                amount = tier.get("amount", {}).get("value", 0)
                                currency = tier.get("amount", {}).get("currency", "USD")

                                # Convert to USD estimate
                                reward_usd = float(amount) if currency == "USD" else float(amount) * 1.0

                                if reward_usd > 0:
                                    raw_opps.append(
                                        RawOpportunity(
                                            id=f"oc_{collective['slug']}_{tier['id']}",
                                            name=f"Contribute to {collective['name']}: {tier['name']}",
                                            description=(
                                                f"{collective.get('description', '')[:200]} "
                                                f"Tier: {tier.get('description', '')[:100]}"
                                            ),
                                            platform="opencollective",
                                            url=f"https://opencollective.com/{collective['slug']}/contribute/{tier['id']}",
                                            reward=reward_usd,
                                            effort_hours=2.0,  # Estimate for contribution
                                            tags=["opensource", "contribution", "funding", collective["slug"]],
                                            cycle="forge",
                                            source_type="dev_bounty",
                                            source_name="opencollective",
                                            metadata={
                                                "original": {"collective": collective, "tier": tier},
                                                "collective_slug": collective["slug"],
                                                "collective_name": collective["name"],
                                                "tier_name": tier["name"],
                                                "currency": currency,
                                            },
                                        )
                                    )

                except Exception:
                    continue
        return raw_opps[:20]  # Limit results


class OpenCollectiveProjectsAdapter(OpportunityAdapter):
    """Adapter for Open Collective projects seeking maintainers/contributors."""

    platform = "opencollective_projects"
    cycle = "forge"

    GRAPHQL_ENDPOINT = "https://api.opencollective.com/graphql/v2"

    SEARCH_PROJECTS_QUERY = """
    query SearchProjects($search: String, $limit: Int) {
        collectives(search: $search, limit: $limit, type: COLLECTIVE) {
            nodes {
                id
                slug
                name
                description
                image
                website
                twitterHandle
                githubHandle
                currency
                isActive
                tiers(limit: 5) {
                    nodes {
                        id
                        name
                        description
                        amount { value currency }
                        type
                    }
                }
            }
        }
    }
    """

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Search for collectives looking for contributors."""
        if not self.is_enabled():
            return []

        search_terms = self.get_config(
            "search_terms",
            [
                "javascript",
                "typescript",
                "python",
                "rust",
                "go",
                "react",
                "vue",
                "django",
                "flask",
                "fastapi",
                "kubernetes",
                "devops",
            ],
        )

        raw_opps = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for term in search_terms[:8]:
                try:
                    variables = {"search": term, "limit": 5}
                    response = await client.post(
                        self.GRAPHQL_ENDPOINT,
                        json={"query": self.SEARCH_PROJECTS_QUERY, "variables": variables},
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code != 200:
                        continue

                    data = response.json()
                    collectives = data.get("data", {}).get("collectives", {}).get("nodes", [])

                    for collective in collectives:
                        if not collective.get("isActive"):
                            continue

                        # Look for CONTRIBUTOR tiers or general funding
                        for tier in collective.get("tiers", {}).get("nodes", []):
                            amount = tier.get("amount", {}).get("value", 0)
                            currency = tier.get("amount", {}).get("currency", "USD")
                            reward_usd = float(amount) if currency == "USD" else float(amount)

                            if reward_usd >= 10:  # Minimum threshold
                                raw_opps.append(
                                    RawOpportunity(
                                        id=f"oc_proj_{collective['slug']}_{tier['id']}",
                                        name=f"Open Source: {collective['name']} - {tier['name']}",
                                        description=(
                                            f"{collective.get('description', '')[:300]} "
                                            f"Tier: {tier.get('description', '')[:150]}"
                                        ),
                                        platform="opencollective",
                                        url=f"https://opencollective.com/{collective['slug']}",
                                        reward=reward_usd,
                                        effort_hours=5.0,
                                        tags=["opensource", "maintainer", "contribution", term, collective["slug"]],
                                        cycle="forge",
                                        source_type="dev_bounty",
                                        source_name="opencollective_projects",
                                        metadata={
                                            "original": collective,
                                            "collective_slug": collective["slug"],
                                            "collective_name": collective["name"],
                                            "tier_name": tier["name"],
                                            "search_term": term,
                                            "currency": currency,
                                        },
                                    )
                                )

                except Exception:
                    continue
        return raw_opps[:30]
