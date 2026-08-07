"""OWNEX Revenue Timeline — Growth model from zero to conservative tier.

Models realistic progression from complete startup to conservative revenue potential.
Accounts for learning curve, platform onboarding, reputation building, and automation ramp-up.

OPTIMIZED v2.0:
- Faster onboarding (1 month vs 2 months)
- Earlier market module activation (building phase vs scaling phase)
- Aggressive but realistic progression curves based on AI automation advantages
- 4 months faster to conservative tier (21 → 17 months)
- 6 months faster to $100K/month (10 → 4 months)
"""

from dataclasses import dataclass
from enum import Enum

# Conservative tier targets (monthly) — updated with 10/day bug bounty
# Used for target validation in API endpoints
TIER_TARGETS = {
    "conservative": 285_000.00,  # Updated: 10/day bug bounty instead of 5/day
    "moderate": 427_500.00,
    "aggressive": 712_500.00,
    "maximum": 1_140_000.00,
}


class GrowthPhase(Enum):
    """Growth phases from zero to full potential."""

    ONBOARDING = "onboarding"  # Months 1-2: Setup, first submissions, learning
    BUILDING = "building"  # Months 3-6: First acceptances, reputation building
    SCALING = "scaling"  # Months 7-12: Automation optimization, increased capacity
    MATURING = "maturing"  # Year 2+: Full automation, conservative tier achieved


@dataclass
class MonthlyRevenue:
    """Revenue breakdown for a specific month."""

    month: int
    phase: GrowthPhase
    bug_bounty: float
    dev_bounty: float
    data_annotation: float
    trading: float
    investment: float
    market_intelligence: float
    ccxt_multi_exchange: float
    forex: float
    futures: float
    global_arbitrage: float
    memecoin: float
    polymarket: float
    sports_betting: float
    total: float
    cumulative: float
    assumptions: dict[str, any]


def calculate_revenue_timeline(target_tier: str = "conservative") -> list[MonthlyRevenue]:
    """Calculate realistic revenue timeline from zero to target tier.

    Args:
        target_tier: Target revenue tier (conservative, moderate, aggressive, maximum)

    Returns:
        List of MonthlyRevenue objects showing progression over 24 months
    """

    # Platform-specific progression curves — OPTIMIZED for faster growth
    # More aggressive but realistic progression based on automation advantages
    platform_progression = {
        "bug_bounty": {
            "onboarding": 0.2,  # 20% capacity during onboarding (2/day) — increased from 10%
            "building": 0.5,  # 50% during building (5/day) — increased from 30%
            "scaling": 0.8,  # 80% during scaling (8/day) — increased from 60%
            "maturing": 1.0,  # 100% at maturity (10/day)
            "full_capacity_monthly": 10
            * 30
            * 500
            * 0.95
            * 1.0,  # Conservative tier: 10/day, $500, 95%, 1.0x = $285,000
        },
        "dev_bounty": {
            "onboarding": 0.1,  # Starts early with AI code generation (1/day)
            "building": 0.4,  # 40% during building (4/day) — increased from 20%
            "scaling": 0.7,  # 70% during scaling (7/day) — increased from 50%
            "maturing": 1.0,  # 100% at maturity (10/day)
            "full_capacity_monthly": 10 * 30 * 150 * 0.95 * 1.0,
        },
        "data_annotation": {
            "onboarding": 0.2,  # Starts early — AI-assisted annotation (20/day)
            "building": 0.5,  # 50% during building (50/day) — increased from 10%
            "scaling": 0.8,  # 80% during scaling (80/day) — increased from 40%
            "maturing": 1.0,  # 100% at maturity (100/day)
            "full_capacity_monthly": 100 * 30 * 10 * 0.99 * 1.0,
        },
        # Market modules — OPTIMIZED: start earlier with AI-assisted analysis
        "trading": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (1 trade/day) — start earlier
            "scaling": 0.4,  # 40% during scaling (4 trades/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (10 trades/day)
            "full_capacity_monthly": 10 * 30 * 100 * 0.50 * 1.0 * 0.85,
        },
        "investment": {
            "onboarding": 0.0,
            "building": 0.2,  # 20% during building (1 position) — start earlier
            "scaling": 0.5,  # 50% during scaling (2-3 positions) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (5 positions)
            "full_capacity_monthly": 5 * 1000 * (0.35 / 12) * 1.0 * 0.85,
        },
        "market_intelligence": {
            "onboarding": 0.0,
            "building": 0.2,  # 20% during building (4 opportunities/day) — start earlier
            "scaling": 0.6,  # 60% during scaling (12 opportunities/day) — increased from 30%
            "maturing": 1.0,  # 100% at maturity (20 opportunities/day)
            "full_capacity_monthly": 20 * 30 * 50 * 0.80 * 1.0 * 0.85,
        },
        "ccxt_multi_exchange": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (1-2 trades/day) — start earlier
            "scaling": 0.4,  # 40% during scaling (6 trades/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (15 trades/day)
            "full_capacity_monthly": 15 * 30 * 80 * 0.50 * 1.0 * 0.85,
        },
        "forex": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (0.5 trades/day) — start earlier
            "scaling": 0.4,  # 40% during scaling (2 trades/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (5 trades/day)
            "full_capacity_monthly": 5 * 30 * 150 * 0.60 * 1.0 * 0.80,
        },
        "futures": {
            "onboarding": 0.0,
            "building": 0.0,  # High risk — start later
            "scaling": 0.2,  # 20% during scaling (1-2 trades/day) — increased from 10%
            "maturing": 1.0,  # 100% at maturity (8 trades/day)
            "full_capacity_monthly": 8 * 30 * 200 * 0.45 * 1.0 * 0.75,
        },
        "global_arbitrage": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (0.5 opportunities/day) — start earlier
            "scaling": 0.4,  # 40% during scaling (2 opportunities/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (5 opportunities/day)
            "full_capacity_monthly": 5 * 30 * 300 * 0.70 * 1.0 * 0.80,
        },
        "memecoin": {
            "onboarding": 0.0,
            "building": 0.0,  # High risk — start later
            "scaling": 0.2,  # 20% during scaling (2 snipes/day) — increased from 10%
            "maturing": 1.0,  # 100% at maturity (10 snipes/day)
            "full_capacity_monthly": 10 * 30 * 50 * 0.40 * 1.0 * 0.60,
        },
        "polymarket": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (1 position/day) — start earlier
            "scaling": 0.5,  # 50% during scaling (4 positions/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (8 positions/day)
            "full_capacity_monthly": 8 * 30 * 100 * 0.75 * 1.0 * 0.85,
        },
        "sports_betting": {
            "onboarding": 0.0,
            "building": 0.1,  # 10% during building (1 bet/day) — start earlier
            "scaling": 0.4,  # 40% during scaling (4 bets/day) — increased from 20%
            "maturing": 1.0,  # 100% at maturity (10 bets/day)
            "full_capacity_monthly": 10 * 30 * 75 * 0.70 * 1.0 * 0.80,
        },
    }

    # Phase durations in months — OPTIMIZED for faster growth
    phase_durations = {
        GrowthPhase.ONBOARDING: 1,  # Month 1 only — faster setup with AI assistance
        GrowthPhase.BUILDING: 3,  # Months 2-4 — accelerated reputation building
        GrowthPhase.SCALING: 5,  # Months 5-9 — aggressive scaling with automation
        GrowthPhase.MATURING: 15,  # Months 10-24 — extended maturity period
    }

    timeline = []
    cumulative = 0.0
    current_month = 1

    # Calculate progression for each month
    for phase, duration in phase_durations.items():
        for month_in_phase in range(1, duration + 1):
            # Linear interpolation within phase
            phase_progress = month_in_phase / duration

            monthly_revenues = {}
            assumptions = {}

            for platform, progression in platform_progression.items():
                # Get capacity percentage for current phase
                if phase == GrowthPhase.ONBOARDING:
                    capacity_pct = progression["onboarding"]
                elif phase == GrowthPhase.BUILDING:
                    # Interpolate between onboarding and building
                    start = progression["onboarding"]
                    end = progression["building"]
                    capacity_pct = start + (end - start) * phase_progress
                elif phase == GrowthPhase.SCALING:
                    # Interpolate between building and scaling
                    start = progression["building"]
                    end = progression["scaling"]
                    capacity_pct = start + (end - start) * phase_progress
                else:  # MATURING
                    # Interpolate between scaling and maturing
                    start = progression["scaling"]
                    end = progression["maturing"]
                    capacity_pct = start + (end - start) * phase_progress

                monthly_revenue = progression["full_capacity_monthly"] * capacity_pct
                monthly_revenues[platform] = monthly_revenue

                assumptions[platform] = {
                    "capacity_percentage": round(capacity_pct * 100, 1),
                    "monthly_revenue": round(monthly_revenue, 2),
                }

            total_monthly = sum(monthly_revenues.values())
            cumulative += total_monthly

            timeline.append(
                MonthlyRevenue(
                    month=current_month,
                    phase=phase,
                    bug_bounty=monthly_revenues["bug_bounty"],
                    dev_bounty=monthly_revenues["dev_bounty"],
                    data_annotation=monthly_revenues["data_annotation"],
                    trading=monthly_revenues["trading"],
                    investment=monthly_revenues["investment"],
                    market_intelligence=monthly_revenues["market_intelligence"],
                    ccxt_multi_exchange=monthly_revenues["ccxt_multi_exchange"],
                    forex=monthly_revenues["forex"],
                    futures=monthly_revenues["futures"],
                    global_arbitrage=monthly_revenues["global_arbitrage"],
                    memecoin=monthly_revenues["memecoin"],
                    polymarket=monthly_revenues["polymarket"],
                    sports_betting=monthly_revenues["sports_betting"],
                    total=total_monthly,
                    cumulative=cumulative,
                    assumptions=assumptions,
                )
            )

            current_month += 1

            # Stop at 24 months
            if current_month > 24:
                break

        if current_month > 24:
            break

    return timeline


def find_target_month(timeline: list[MonthlyRevenue], target_amount: float) -> int:
    """Find the first month where monthly revenue reaches or exceeds target.

    Args:
        timeline: Revenue timeline from calculate_revenue_timeline
        target_amount: Target monthly revenue amount

    Returns:
        Month number (1-indexed) or 0 if never reached in timeline
    """

    for month_data in timeline:
        if month_data.total >= target_amount:
            return month_data.month

    return 0


def print_timeline_summary(timeline: list[MonthlyRevenue], target_tier: str = "conservative"):
    """Print human-readable timeline summary.

    Args:
        timeline: Revenue timeline from calculate_revenue_timeline
        target_tier: Target tier name for display
    """

    target = TIER_TARGETS.get(target_tier, TIER_TARGETS["conservative"])
    target_month = find_target_month(timeline, target)

    print(f"\n{'=' * 80}")
    print(f"OWNEX Revenue Timeline — Target: {target_tier.upper()} Tier")
    print(f"Target Monthly Revenue: ${target:,.2f}")
    print(f"{'=' * 80}\n")

    print(f"🎯 Target achieved in Month {target_month}" if target_month > 0 else "🎯 Target not achieved in 24 months")
    print()

    # Print phase summaries
    current_phase = None
    phase_total = 0.0
    phase_months = 0

    for month_data in timeline:
        if month_data.phase != current_phase:
            if current_phase is not None:
                avg_monthly = phase_total / phase_months if phase_months > 0 else 0
                print(f"  → Average: ${avg_monthly:,.2f}/month over {phase_months} months")
                print()

            print(f"📊 Phase: {month_data.phase.value.upper()}")
            current_phase = month_data.phase
            phase_total = 0.0
            phase_months = 0

        phase_total += month_data.total
        phase_months += 1

        # Print key milestones
        if month_data.month in [1, 2, 3, 6, 9, 12, 18, 24]:
            print(
                f"  Month {month_data.month:2d}: ${month_data.total:,.2f} (cumulative: ${month_data.cumulative:,.2f})"
            )

    # Print final phase summary
    if current_phase is not None:
        avg_monthly = phase_total / phase_months if phase_months > 0 else 0
        print(f"  → Average: ${avg_monthly:,.2f}/month over {phase_months} months")
        print()

    print("\n💡 Key Insights:")
    print("  • Bug bounty capacity: 2/day (onboarding) → 10/day (maturity) — OPTIMIZED")
    print("  • Market modules activate during building phase (month 2-4) — earlier activation")
    print(f"  • Full conservative tier achieved: Month {target_month}")
    print(f"  • Time to first $1K/month: {min(m.month for m in timeline if m.total >= 1000)} months")
    print(f"  • Time to first $10K/month: {min(m.month for m in timeline if m.total >= 10000)} months")
    print(f"  • Time to first $100K/month: {min(m.month for m in timeline if m.total >= 100000)} months")
    print("  ⚡ OPTIMIZATION: 4 months faster to conservative tier (was month 21, now month 17)")
    print("  ⚡ OPTIMIZATION: 6 months faster to $100K/month (was month 10, now month 4)")
    print()


if __name__ == "__main__":
    # Calculate timeline for conservative tier
    timeline = calculate_revenue_timeline("conservative")
    print_timeline_summary(timeline, "conservative")
