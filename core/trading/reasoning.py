"""Trading reasoning — OWNEX learns its own winning logic.

StrategyDNA is distilled from the decision journal (data_snapshot with
strategy_id + params). The correlator aggregates outcomes per strategy,
the optimizer proposes parameter adjustments with reasoning, and every
approval is itself logged back to the journal (closed loop).
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from core.trading.store import TradingStore

logger = logging.getLogger("catseye.trading.reasoning")

MIN_SAMPLE_FOR_DNA = 5
MIN_SAMPLE_FOR_OPTIMIZATION = 20
TRADING_ACTIONS = {"trading:copy_executed", "trading:param_change", "trading:strategy_start", "trading:strategy_stop"}


@dataclass
class StrategyDNA:
    """Distilled winning/losing logic for one strategy."""

    strategy_id: str
    regime: str
    winning_params: dict[str, Any]
    losing_params: dict[str, Any]
    confidence: float
    sample_size: int
    win_rate: float
    profit_factor: float
    max_dd_pct: float
    sharpe: float
    last_updated: str


@dataclass
class ParamAdjustment:
    """Proposed parameter change, awaiting approval."""

    proposal_id: str
    strategy_id: str
    param: str
    current_value: Any
    proposed_value: Any
    reason: str
    confidence: float
    status: str = "pending"  # pending | approved | rejected
    created_at: str = ""


class DecisionCorrelator:
    """Aggregate decision journal entries into per-strategy DNA."""

    def __init__(self, store: TradingStore | None = None) -> None:
        self._store = store or TradingStore()

    @staticmethod
    def _parse_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
        raw = entry.get("data_snapshot") or {}
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (ValueError, TypeError):
                return {}
        return dict(raw) if isinstance(raw, dict) else {}

    def correlate(self, entries: list[dict[str, Any]] | None = None, limit: int = 500) -> list[StrategyDNA]:
        if entries is None:
            try:
                from core.decision_journal.journal import get_decisions

                entries = get_decisions(app_id="trading", limit=limit)
            except Exception:
                logger.debug("journal unavailable — no DNA computed")
                return []
        groups: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            if entry.get("app_id") != "trading" and not str(entry.get("action", "")).startswith("trading:"):
                continue
            snapshot = self._parse_snapshot(entry)
            strategy_id = str(snapshot.get("strategy_id") or entry.get("action") or "unknown")
            groups.setdefault(strategy_id, []).append(entry)

        dna_list: list[StrategyDNA] = []
        for strategy_id, group in groups.items():
            if len(group) < MIN_SAMPLE_FOR_DNA:
                continue
            sample_size = len(group)
            wins = sum(1 for e in group if e.get("outcome") == "success")
            losses = sum(1 for e in group if e.get("outcome") == "failure")
            rewards = [float(e.get("reward") or 0.0) for e in group if (e.get("reward") or 0) > 0]
            gross_win = sum(rewards) if rewards else float(wins)
            gross_loss = float(losses) if losses > 0 else 1.0
            win_rate = wins / sample_size * 100.0
            profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 0.0
            winning_params: dict[str, Any] = {}
            losing_params: dict[str, Any] = {}
            for e in group:
                snap = self._parse_snapshot(e)
                params = snap.get("params") or {}
                if not isinstance(params, dict):
                    continue
                if e.get("outcome") == "success" and not winning_params:
                    winning_params = dict(params)
                elif e.get("outcome") == "failure" and not losing_params:
                    losing_params = dict(params)
            confidence = round(min(0.95, max(0.2, sample_size / 200.0)), 2)
            regime = str(group[0].get("data_snapshot_regime") or "unknown")
            dna_list.append(
                StrategyDNA(
                    strategy_id=strategy_id,
                    regime=regime,
                    winning_params=winning_params,
                    losing_params=losing_params,
                    confidence=confidence,
                    sample_size=sample_size,
                    win_rate=round(win_rate, 1),
                    profit_factor=round(profit_factor, 2),
                    max_dd_pct=0.0,
                    sharpe=0.0,
                    last_updated=self._store.now_iso(),
                )
            )
        dna_list.sort(key=lambda d: (d.confidence, d.win_rate), reverse=True)
        return dna_list

    def persist_dna(self, dna_list: list[StrategyDNA]) -> None:
        self._store.set("dna", [asdict(d) for d in dna_list])


class AutoParamOptimizer:
    """Propose parameter adjustments from DNA. Only with sufficient evidence."""

    def __init__(self, store: TradingStore | None = None) -> None:
        self._store = store or TradingStore()

    def propose(self, dna: StrategyDNA) -> list[ParamAdjustment]:
        if dna.sample_size < MIN_SAMPLE_FOR_OPTIMIZATION:
            return []
        proposals: list[ParamAdjustment] = []
        if dna.win_rate < 50:
            proposals.append(
                ParamAdjustment(
                    proposal_id=uuid.uuid4().hex[:12],
                    strategy_id=dna.strategy_id,
                    param="tp_pct",
                    current_value=dna.winning_params.get("tp_pct", 3.0),
                    proposed_value=round(float(dna.winning_params.get("tp_pct", 3.0)) * 0.8, 2),
                    reason=f"win rate {dna.win_rate:.0f}% < 50% — take profit más cercano",
                    confidence=dna.confidence,
                    created_at=self._store.now_iso(),
                )
            )
        if dna.profit_factor < 1.5 and dna.win_rate < 55:
            proposals.append(
                ParamAdjustment(
                    proposal_id=uuid.uuid4().hex[:12],
                    strategy_id=dna.strategy_id,
                    param="size_pct",
                    current_value=dna.winning_params.get("size_pct", 5.0),
                    proposed_value=round(float(dna.winning_params.get("size_pct", 5.0)) * 0.75, 2),
                    reason=f"profit factor {dna.profit_factor:.2f} — reducir tamaño de posición",
                    confidence=dna.confidence,
                    created_at=self._store.now_iso(),
                )
            )
        if dna.win_rate >= 60 and dna.profit_factor >= 1.5:
            proposals.append(
                ParamAdjustment(
                    proposal_id=uuid.uuid4().hex[:12],
                    strategy_id=dna.strategy_id,
                    param="size_pct",
                    current_value=dna.winning_params.get("size_pct", 5.0),
                    proposed_value=round(float(dna.winning_params.get("size_pct", 5.0)) * 1.2, 2),
                    reason=f"lógica ganadora confirmada (win rate {dna.win_rate:.0f}%, PF {dna.profit_factor:.2f}) — escalar tamaño",
                    confidence=dna.confidence,
                    created_at=self._store.now_iso(),
                )
            )
        return proposals

    def propose_all(self, dna_list: list[StrategyDNA]) -> list[ParamAdjustment]:
        proposals: list[ParamAdjustment] = []
        for dna in dna_list:
            proposals.extend(self.propose(dna))
        return proposals

    def approve(self, proposal_id: str) -> dict[str, Any]:
        proposals = [ParamAdjustment(**p) for p in self._store.get("proposals") or []]
        for proposal in proposals:
            if proposal.proposal_id != proposal_id:
                continue
            if proposal.status != "pending":
                return {"success": False, "reason": f"proposal already {proposal.status}"}
            proposal.status = "approved"
            self._store.upsert_item("proposals", asdict(proposal), id_key="proposal_id")
            self._log_decision(proposal, applied=True)
            return {"success": True, "proposal": asdict(proposal)}
        return {"success": False, "reason": "proposal not found"}

    def reject(self, proposal_id: str) -> dict[str, Any]:
        proposals = [ParamAdjustment(**p) for p in self._store.get("proposals") or []]
        for proposal in proposals:
            if proposal.proposal_id != proposal_id:
                continue
            if proposal.status != "pending":
                return {"success": False, "reason": f"proposal already {proposal.status}"}
            proposal.status = "rejected"
            self._store.upsert_item("proposals", asdict(proposal), id_key="proposal_id")
            self._log_decision(proposal, applied=False)
            return {"success": True, "proposal": asdict(proposal)}
        return {"success": False, "reason": "proposal not found"}

    @staticmethod
    def _log_decision(proposal: ParamAdjustment, applied: bool) -> None:
        try:
            from core.decision_journal.journal import log_decision

            log_decision(
                app_id="trading",
                agent_id="auto_optimizer",
                action="trading:param_change" if applied else "trading:param_rejected",
                reason=f"{proposal.param}: {proposal.current_value} → {proposal.proposed_value} ({proposal.reason})",
                data_snapshot={
                    "strategy_id": proposal.strategy_id,
                    "params": {proposal.param: proposal.proposed_value},
                },
                confidence=proposal.confidence,
                risk_score=0.3,
            )
        except Exception:
            logger.debug("decision log skipped (journal unavailable)")


def run_dna_update(limit: int = 500) -> dict[str, Any]:
    """Scheduler handler: correlate journal → DNA + proposals, persist."""
    store = TradingStore()
    correlator = DecisionCorrelator(store)
    optimizer = AutoParamOptimizer(store)
    dna_list = correlator.correlate(limit=limit)
    correlator.persist_dna(dna_list)
    proposals = optimizer.propose_all(dna_list)
    existing = store.get("proposals") or []
    store.set("proposals", existing + [asdict(p) for p in proposals])
    return {"dna_count": len(dna_list), "proposals": len(proposals), "last_updated": store.now_iso()}
