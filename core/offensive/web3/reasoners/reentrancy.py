from __future__ import annotations

from core.offensive.web3.base import BaseWeb3Reasoner
from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis


class ReentrancyReasoner(BaseWeb3Reasoner):
    """Detect reentrancy vulnerabilities (ETH, ERC20, cross-function)."""

    @property
    def vulnerability_type(self) -> str:
        return "reentrancy"

    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        slither_results = self._analyze_with_slither(contract)
        if slither_results:
            return slither_results

        hypotheses: list[Web3Hypothesis] = []
        signals: list[str] = []

        if contract.has_function_prefix("withdraw"):
            signals.append("Contract has withdraw function — classic reentrancy entry point")
        if contract.has_function_prefix("claim"):
            signals.append("Contract has claim function — potential reentrancy via external call")
        if contract.has_function("transfer") and contract.has_function_prefix("_transfer"):
            signals.append("External transfer function detected — CEI pattern may be violated")
        if contract.has_function_prefix("call"):
            signals.append("Low-level call detected — risk of unchecked external interaction")
        if contract.has_function_prefix("send"):
            signals.append("send() detected — reentrancy via fallback possible")
        if contract.has_function_prefix("delegatecall"):
            signals.append("delegatecall detected — high risk proxy reentrancy pattern")

        if signals:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=min(0.35 + len(signals) * 0.12, 0.85),
                    severity="high" if len(signals) >= 3 else "medium",
                    summary="Potential reentrancy vulnerability",
                    description=f"Contract {contract.name or contract.address} contains {len(signals)} reentrancy signals. "
                    f"Withdraw/claim functions combined with external calls suggest CEI pattern may be violated, "
                    f"enabling reentrancy attacks.",
                    signals=signals,
                    test_instructions=[
                        f"Deploy a malicious contract that calls back into {contract.name or 'the target'} before state updates complete",
                        "Monitor for ETH balance changes after single transaction",
                        "Check if state variables are updated before or after external calls",
                        f"Test with Foundry: cast call {contract.address} 'function()' --trace",
                    ],
                    remediation="Apply Checks-Effects-Interactions pattern. Use ReentrancyGuard from OpenZeppelin.",
                )
            )

        return hypotheses
