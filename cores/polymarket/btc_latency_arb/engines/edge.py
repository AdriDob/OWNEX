"""Edge Computation & Decision Engine."""

from __future__ import annotations

from dataclasses import dataclass

from core.polymarket.btc_latency_arb.indicators.rsi import clamp


@dataclass(slots=True)
class EdgeResult:
    """Edge computation result."""

    market_up: float | None
    market_down: float | None
    edge_up: float | None
    edge_down: float | None


@dataclass(slots=True)
class Decision:
    """Trading decision."""

    action: str  # "ENTER", "NO_TRADE"
    side: str | None  # "UP", "DOWN"
    phase: str  # "EARLY", "MID", "LATE"
    strength: str | None = None  # "STRONG", "GOOD", "OPTIONAL"
    edge: float | None = None
    reason: str | None = None


def compute_edge(
    model_up: float | None, model_down: float | None, market_yes: float | None, market_no: float | None
) -> EdgeResult:
    """Compute edge = model_prob - market_implied_prob."""
    if market_yes is None or market_no is None:
        return EdgeResult(
            market_up=None,
            market_down=None,
            edge_up=None,
            edge_down=None,
        )

    total = market_yes + market_no
    if total <= 0:
        return EdgeResult(
            market_up=None,
            market_down=None,
            edge_up=None,
            edge_down=None,
        )

    market_up = market_yes / total
    market_down = market_no / total

    edge_up = model_up - market_up if model_up is not None else None
    edge_down = model_down - market_down if model_down is not None else None

    return EdgeResult(
        market_up=clamp(market_up, 0.0, 1.0),
        market_down=clamp(market_down, 0.0, 1.0),
        edge_up=edge_up,
        edge_down=edge_down,
    )


def decide(
    remaining_minutes: float,
    edge_up: float | None,
    edge_down: float | None,
    model_up: float | None = None,
    model_down: float | None = None,
) -> Decision:
    """Make trading decision based on edge and time remaining."""
    # Determine phase
    if remaining_minutes > 10:
        phase = "EARLY"
    elif remaining_minutes > 5:
        phase = "MID"
    else:
        phase = "LATE"

    # Phase-based thresholds
    if phase == "EARLY":
        threshold = 0.05
        min_prob = 0.55
    elif phase == "MID":
        threshold = 0.10
        min_prob = 0.60
    else:  # LATE
        threshold = 0.20
        min_prob = 0.65

    if edge_up is None or edge_down is None:
        return Decision(
            action="NO_TRADE",
            side=None,
            phase=phase,
            reason="missing_market_data",
        )

    # Choose best side
    best_side = "UP" if edge_up > edge_down else "DOWN"
    best_edge = edge_up if best_side == "UP" else edge_down
    best_model = model_up if best_side == "UP" else model_down

    if best_edge < threshold:
        return Decision(
            action="NO_TRADE",
            side=None,
            phase=phase,
            reason=f"edge_below_{threshold}",
        )

    if best_model is not None and best_model < min_prob:
        return Decision(
            action="NO_TRADE",
            side=None,
            phase=phase,
            reason=f"prob_below_{min_prob}",
        )

    # Determine strength
    if best_edge >= 0.20:
        strength = "STRONG"
    elif best_edge >= 0.10:
        strength = "GOOD"
    else:
        strength = "OPTIONAL"

    return Decision(
        action="ENTER",
        side=best_side,
        phase=phase,
        strength=strength,
        edge=best_edge,
    )
