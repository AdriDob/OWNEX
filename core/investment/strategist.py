from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from core.investment.models import RiskLevel

logger = logging.getLogger("orion.investment.strategist")


@dataclass
class StrategyProposal:
    proposal_id: str = field(default_factory=lambda: str(uuid4()))
    asset: str = ""
    action: str = "BUY"  # BUY, SELL, HEDGE
    amount_usd: float = 0.0
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    expected_roi_pct: float = 0.0
    risk_level: RiskLevel = RiskLevel.CONSERVATIVE
    justification: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXECUTED, FAILED


class InvestmentStrategist:
    """
    Autonomous engine that analyzes market conditions and capital to propose
    investment strategies.
    """

    def __init__(self, manager):
        self.manager = manager

    async def analyze_and_propose(self) -> list[StrategyProposal]:
        """
        Main loop: check available capital -> check market -> generate proposals.
        """
        proposals = []
        snap = self.manager.snapshot()
        available = snap.available

        if available <= 0:
            logger.info("No available capital for new strategies.")
            return []

        # TODO: Integrate with actual market data from adapters
        # For now, we implement the "Logic Skeleton" for autonomous proposal

        # Example: Propose a basic conservative allocation if capital is idling
        if available > 100:
            proposal = StrategyProposal(
                asset="BTC",
                amount_usd=available * 0.1,  # 10% of available
                expected_roi_pct=5.0,
                risk_level=RiskLevel.CONSERVATIVE,
                justification="Idle capital detection: Diversifying into BTC to maintain liquidity and growth.",
            )
            proposals.append(proposal)

        return proposals

    def validate_proposal(self, proposal: StrategyProposal) -> bool:
        """
        Internal check before sending to user for authorization.
        """
        # Ensure it doesn't violate global risk limits (25% rule)
        exposure = self.manager._allocation.get_high_risk_exposure()
        if proposal.risk_level not in (RiskLevel.AGGRESSIVE, RiskLevel.SPECULATIVE):
            return True
        return exposure["within_limit"]

    async def submit_to_queue(self, proposal: StrategyProposal) -> str:
        """
        Push the proposal into the ExecutionQueue as a QUALIFIED item.
        """
        from core.execution_queue import ExecutionQueueStore
        from core.execution_queue.models import ExecState

        queue = ExecutionQueueStore()

        # Map StrategyProposal to ExecutionQueueItem
        # We use a synthetic task_id or the proposal_id
        item_id = f"inv_{proposal.proposal_id}"

        item_data = {
            "id": item_id,
            "type": "investment",
            "state": ExecState.QUALIFIED,
            "payload": proposal.__dict__,
            "priority": 10 if proposal.risk_level == RiskLevel.CONSERVATIVE else 5,
            "created_at": proposal.created_at,
            "updated_at": proposal.created_at,
        }

        queue.upsert_item(item_id, item_data)
        return item_id
