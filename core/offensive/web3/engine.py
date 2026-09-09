from __future__ import annotations

import logging
from typing import Any

from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis
from core.offensive.web3.reasoners import (
    AccessControlReasoner,
    ERC20Reasoner,
    FlashLoanAttackReasoner,
    OracleManipulationReasoner,
    ReentrancyReasoner,
)

logger = logging.getLogger("orion.core.offensive.web3")


class Web3OffensiveEngine:
    def __init__(self) -> None:
        self._reasoners = [
            ReentrancyReasoner(),
            ERC20Reasoner(),
            AccessControlReasoner(),
            OracleManipulationReasoner(),
            FlashLoanAttackReasoner(),
        ]

    @property
    def reasoners(self) -> list[Any]:
        return list(self._reasoners)

    def list_reasoners(self) -> list[dict[str, Any]]:
        return [
            {
                "vulnerability_type": r.vulnerability_type,
                "supported_chains": r.supported_chains(),
            }
            for r in self._reasoners
        ]

    def analyze_contract(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        all_hypotheses: list[Web3Hypothesis] = []
        for reasoner in self._reasoners:
            try:
                if contract.chain not in reasoner.supported_chains():
                    continue
                hypotheses = reasoner.analyze(contract)
                all_hypotheses.extend(hypotheses)
                logger.info(
                    "Web3 reasoner %s generated %d hypotheses for %s",
                    reasoner.vulnerability_type,
                    len(hypotheses),
                    contract.address,
                )
            except Exception:
                logger.exception("Web3 reasoner %s failed for %s", reasoner.vulnerability_type, contract.address)
        return all_hypotheses

    def analyze_batch(self, contracts: list[SmartContractInfo]) -> dict[str, list[Web3Hypothesis]]:
        results: dict[str, list[Web3Hypothesis]] = {}
        for contract in contracts:
            results[contract.address] = self.analyze_contract(contract)
        return results

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_reasoners": len(self._reasoners),
            "vulnerability_types": [r.vulnerability_type for r in self._reasoners],
            "supported_chains": list(set(c for r in self._reasoners for c in r.supported_chains())),
        }
