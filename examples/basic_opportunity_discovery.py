#!/usr/bin/env python3
"""
Example: Basic Opportunity Discovery with OWNEX

This example demonstrates how to use the OWNEX opportunity engine
to discover and evaluate revenue opportunities.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.opportunity import OpportunityCategory, get_opportunity_engine


async def main():
    """Run basic opportunity discovery."""

    print("🚀 OWNEX Opportunity Discovery Example")
    print("=" * 50)

    # Get the opportunity engine
    engine = get_opportunity_engine()

    # Discover opportunities
    print("\n🔍 Discovering opportunities...")
    opportunities = await engine.discover(
        categories=[OpportunityCategory.BUG_BOUNTY, OpportunityCategory.FREELANCE, OpportunityCategory.GRANTS],
        min_score=60,
        limit=10,
    )

    print(f"\n✅ Found {len(opportunities)} opportunities:")
    print("-" * 50)

    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp.title}")
        print(f"   Category: {opp.category.value}")
        print(f"   Source: {opp.source.value}")
        print(f"   Score: {opp.score.total}/100")
        print(f"   Estimated Value: ${opp.estimated_value:,.2f}")
        print(f"   Confidence: {opp.confidence * 100:.0f}%")
        if opp.tags:
            print(f"   Tags: {', '.join(opp.tags)}")

    # Show scoring breakdown for top opportunity
    if opportunities:
        print("\n" + "=" * 50)
        print("📊 Detailed Scoring (Top Opportunity):")
        print("=" * 50)
        top = opportunities[0]
        breakdown = top.score.breakdown
        print(f"  Market Demand:      {breakdown.market_demand}/25")
        print(f"  Technical Feasibility: {breakdown.technical_feasibility}/25")
        print(f"  Time to Revenue:    {breakdown.time_to_revenue}/20")
        print(f"  Competition:        {breakdown.competition}/15")
        print(f"  Skill Match:        {breakdown.skill_match}/15")
        print("  ──────────────────────────────")
        print(f"  TOTAL:              {top.score.total}/100")
        print(f"  TIER:               {top.score.tier.value}")

    print("\n✨ Example complete!")


if __name__ == "__main__":
    asyncio.run(main())
