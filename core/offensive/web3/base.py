from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis
from cores.tools.slither import SlitherTool

logger = logging.getLogger("orion.offensive.web3")

SLITHER_CHECK_TO_VULN: dict[str, str] = {
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-unlimited-gas": "reentrancy",
    "unused-return": "unused_return",
    "tx-origin": "access_control",
    "timestamp": "timestamp_dependency",
    "block-timestamp": "timestamp_dependency",
    "controlled-delegatecall": "access_control",
    "suicidal": "access_control",
    "incorrect-equality": "precision_loss",
    "locked-ether": "locked_funds",
    "arbitrary-send": "access_control",
    "low-level-calls": "low_level_call",
    "controlled-array-length": "access_control",
    "delegatecall-loop": "access_control",
    "uninitialized-state": "initialization",
    "uninitialized-storage": "initialization",
    "assembly": "low_level_call",
    "divide-before-multiply": "precision_loss",
}


class BaseWeb3Reasoner(ABC):
    def __init__(self) -> None:
        self._slither = SlitherTool()

    @property
    @abstractmethod
    def vulnerability_type(self) -> str: ...

    @abstractmethod
    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]: ...

    def supported_chains(self) -> list[str]:
        return ["ethereum", "polygon", "bsc", "arbitrum", "optimism"]

    def _analyze_with_slither(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        if not contract.source_code or not self._slither.is_available():
            return []
        raw_results = self._slither.scan_source_code(contract.source_code)
        if not raw_results:
            return []
        hypotheses: list[Web3Hypothesis] = []
        for r in raw_results:
            check_name = r.tags[-1] if r.tags else ""
            if SLITHER_CHECK_TO_VULN.get(check_name) != self.vulnerability_type:
                continue
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=r.confidence,
                    severity=r.severity,
                    summary=r.name[:200],
                    description=r.description[:500] if r.description else "",
                    signals=[f"Slither detector: {check_name}", f"Target: {r.target}"],
                    test_instructions=[
                        f"Review the flagged code at {r.target}",
                        "Verify the vulnerability manually with Foundry/Hardhat tests",
                        "Check if the condition is exploitable in the contract's context",
                    ],
                    remediation="Review flagged code and apply standard security patterns",
                )
            )
        return hypotheses
