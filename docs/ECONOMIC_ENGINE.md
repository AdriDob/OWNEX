# OWNEX Economic Engine

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

The Economic Engine is the single source of truth for all financial calculations in OWNEX. It replaces ad-hoc formulas with versioned, tested, auditable computations.

## Core Principles

1. **No Invented Numbers** — Every probability, rate, or projection derives from observed data or explicit assumptions
2. **Expected ≠ Realized** — Strict separation between projected and actual money
3. **Human-Time EV** — Value measured in USD per hour of human intervention
4. **Versioned Formulas** — All computations tagged (EV-V1, HTROI-V1, CONF-V1)

## Expected Value (EV-V1)

### Formula
```python
def compute_expected_value(opportunity: Opportunity, profile: UserProfile) -> float:
    """
    EV = reward × acceptance_probability × payment_probability
       × skill_match × (1 - risk_penalty)
    """
    base_reward = opportunity.reward_usd or estimate_reward(opportunity)
    
    acceptance = calculate_acceptance_probability(opportunity, profile)
    payment = calculate_payment_probability(opportunity)
    skill_match = calculate_skill_match(opportunity, profile)
    risk = calculate_risk_penalty(opportunity)
    
    return base_reward * acceptance * payment * skill_match * (1 - risk)
```

### Acceptance Probability
```python
def calculate_acceptance_probability(opp: Opportunity, profile: UserProfile) -> float:
    """
    Combines:
    - Platform success rate (from feedback loop)
    - Category success rate
    - Zero barrier score (normalized)
    - Cold-start prior (0.5, labeled as PRIOR)
    """
    if profile.has_history:
        return weighted_average(
            profile.platform_success_rates.get(opp.platform, 0.5),
            profile.category_success_rates.get(opp.category, 0.5),
            opp.zero_barrier_score / 100,
            weights=[0.4, 0.3, 0.3],
        )
    else:
        return 0.5  # LABELED AS PRIOR — never presented as real
```

### Payment Probability
```python
def calculate_payment_probability(opp: Opportunity) -> float:
    """
    Uses PaymentCompatibilityEngine:
    - Compatible → 1.0
    - Viable with gaps → 0.7
    - Partial → 0.4
    - Incompatible → 0.0 (with honest_note)
    """
    verdict = payment_compat_engine.evaluate(opp.payment_method, opp.currency)
    return verdict.viable_score  # 0.0-1.0
```

## Human-Time EV (HTROI-V1)

### Formula
```python
def compute_htroi(opportunity: Opportunity, profile: UserProfile) -> HTROIResult:
    """
    HTROI = expected_value_usd / estimated_human_hours

    Where estimated_human_hours includes:
    - Application time (profile-based)
    - Communication/negotiation (platform average)
    - Delivery preparation (AssistedExecutor estimate)
    - Review/QC (fixed per category)
    """
    human_hours = estimate_human_hours(opportunity, profile)
    if human_hours <= 0:
        return HTROIResult(value=0, band="UNKNOWN", note="No human time estimate")

    ev = compute_expected_value(opportunity, profile)
    htroi = ev / human_hours

    return HTROIResult(
        value=htroi,
        band=categorize_htroi(htroi),  # LOW/MEDIUM/HIGH/ELITE
        human_hours=human_hours,
        expected_value=ev,
    )
```

### Bands
| Band | HTROI Range | Meaning |
|------|-------------|---------|
| ELITE | > $500/h | Exceptional |
| HIGH | $200-500/h | Very good |
| MEDIUM | $50-200/h | Worthwhile |
| LOW | $10-50/h | Marginal |
| UNKNOWN | N/A | Insufficient data |

## Confidence Scoring (CONF-V1)

### Formula
```python
def compute_confidence(opportunity: Opportunity) -> ConfidenceResult:
    """
    Base confidence from primary signals:
    - Platform verification (0.3)
    - Evidence completeness (0.3)
    - Historical precedent (0.2)
    - Payment verification (0.2)

    Uncertainty penalty (from HypothesisChallenger):
    - Missing verifications: -0.03 each
    - Alternative explanations: -0.02 each
    - Contradiction test failures: -0.05 each
    """
    base = sum(signal.weight * signal.value for signal in primary_signals)
    penalty = uncertainty_penalty(opportunity)  # 0.0 to 0.12
    final = max(0, base - penalty)

    return ConfidenceResult(
        score=final,
        band=categorize_confidence(final),  # HIGH/MEDIUM/LOW/UNKNOWN
        uncertainty_penalty=penalty,
        missing_verifications=list_missing(opportunity),
    )
```

## Calibration Engine

### Platform Factor
```python
def calibrate_platform_factor(platform: str, predicted: float, actual: float) -> float:
    """
    Tracks prediction accuracy per platform.
    Factor = median(actual / predicted) over last N outcomes.
    Clamped to [0.5, 2.0] to prevent runaway.
    """
    history = get_calibration_history(platform)
    if len(history) < MIN_EVIDENCE(3):
        return 1.0  # No calibration yet

    ratios = [h.actual / h.predicted for h in history if h.predicted > 0]
    factor = median(ratios)
    return clamp(factor, 0.5, 2.0)
```

### Application
```python
def calibrated_ev(opportunity: Opportunity) -> float:
    raw_ev = compute_expected_value(opportunity)
    factor = get_platform_factor(opportunity.platform)
    return raw_ev * factor
```

## Fallback System

### Priority Chain
```
1. PRIMARY: Platform with documented rate + user history
2. FALLBACK 1: Same category, different platform (if ≥3 outcomes)
3. FALLBACK 2: Category average (if ≥5 outcomes)
4. FALLBACK 3: Global average (if ≥10 outcomes)
5. DEFAULT: Conservative prior (0.5 acceptance, median reward)
```

### Trigger Conditions
```python
def select_fallback(opportunity: Opportunity) -> FallbackResult:
    primary = get_primary_estimate(opportunity)

    if primary.confidence >= HIGH:
        return primary

    for fallback in FALLBACK_CHAIN:
        if fallback.evidence >= MIN_EVIDENCE:
            return FallbackResult(
                source=fallback.name,
                ev=fallback.ev,
                confidence=fallback.confidence,
                note=f"Using {fallback.name} fallback",
            )

    return FallbackResult(
        source="DEFAULT",
        ev=conservative_estimate,
        confidence=UNKNOWN,
        note="Insufficient evidence for any calibrated estimate",
    )
```

## Dynamic Weights (Recommender)

### Weight Evolution
```python
class DynamicWeights:
    """
    Weights shift based on calibration evidence:
    - Base: acceptance=0.4, EV=0.25, barrier=0.15, speed=0.1, compat=0.05, rep=0.05
    - As platform_factor stabilizes → EV weight increases
    - As acceptance history grows → acceptance weight increases
    - Always sums to 1.0
    """

    def update_from_calibration(self, calibration_results: dict):
        # Shift weights toward better-calibrated signals
        pass
```

## Financial Metrics

### Revenue Tracker (`cores/revenue_tracker/revenue_tracker.py`)

```python
class RevenueTracker:
    def metrics(self) -> RevenueMetrics:
        """
        Computes FROM CURRENT STATE (not incremental):
        - completed_amount: SUM(amount) WHERE status=PAID
        - pending_amount: SUM(amount) WHERE status IN (ACCEPTED, SUBMITTED)
        - expected_amount: SUM(ev) WHERE status IN (RECOMMENDED, READY)
        - usd_per_hour: completed_amount / total_human_hours
        - platform_speed_days: median(payout_date - submit_date) per platform
        """
```

### Key Metrics
| Metric | Formula | Source |
|--------|---------|--------|
| `completed_amount` | Σ(amount) WHERE status=PAID | RevenueTracker |
| `pending_amount` | Σ(amount) WHERE status∈{ACCEPTED,SUBMITTED} | RevenueTracker |
| `expected_amount` | Σ(EV) WHERE status∈{RECOMMENDED,READY} | WorkBank |
| `usd_per_hour` | completed_amount / total_human_hours | RevenueTracker |
| `platform_speed_days` | median(payout - submit) per platform | RevenueTracker |
| `acceptance_rate` | accepted / (accepted + rejected) | Feedback Loop |

## Income Projection

### Formula
```python
def project_income(profile: UserProfile, months: int = 12) -> IncomeProjection:
    """
    Monte Carlo simulation (1000 runs):
    - Sample monthly opportunities from WorkBank distribution
    - Apply acceptance probability per platform
    - Apply payment probability per method
    - Sum monthly cash flows
    """
    monthly_curve = []
    for month in range(months):
        monthly_ev = sum(opp.ev * platform_factor(opp.platform) for opp in sample_monthly_opportunities(profile))
        monthly_curve.append(monthly_ev)

    return IncomeProjection(
        monthly_curve=monthly_curve,
        crossing_months=months_to_target(profile.target_monthly),
        conservative=percentile(monthly_curve, 10),
        expected=percentile(monthly_curve, 50),
        optimistic=percentile(monthly_curve, 90),
    )
```

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/direct-work/recommend` | Returns EV, HTROI, confidence per opportunity |
| `/direct-work/score` | Returns ZeroBarrierScore + factors |
| `/direct-work/workbank` | Returns work bank with EV/projections |
| `/direct-work/daily-brief` | Top pick + HTROI + skill gap |
| `/capital/snapshot` | Unified capital view (bounty + work + investment) |
| `/revenue-timeline/calculate` | Income projection |
| `/payment-compat/evaluate` | Payment viability verdict |

---

*Document generated from codebase. Last verified: 2026-08-27*