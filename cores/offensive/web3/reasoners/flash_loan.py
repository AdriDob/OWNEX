from __future__ import annotations

from core.offensive.web3.base import BaseWeb3Reasoner
from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis

CALLBACK_FUNCTIONS = {
    "executeOperation",
    "onFlashLoan",
    "tick",
    "beforeSwap",
    "afterSwap",
    "uniswapV2Call",
    "uniswapV3FlashCallback",
    "uniswapV3SwapCallback",
    "algebraFlashCallback",
    "pancakeCall",
    "balancerFlashLoanCallback",
    "dodoCall",
    "v2FlashLoanCallback",
}


class FlashLoanAttackReasoner(BaseWeb3Reasoner):
    @property
    def vulnerability_type(self) -> str:
        return "flash_loan_attack"

    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        slither_results = self._analyze_with_slither(contract)
        if slither_results:
            return slither_results

        hypotheses: list[Web3Hypothesis] = []
        functions = {fn.split("(")[0] for fn in (contract.functions or [])}

        callback_fns = [fn for fn in functions if fn in CALLBACK_FUNCTIONS]
        has_receive = contract.has_function("receive") or contract.has_function("fallback")
        has_oracle = contract.has_function_prefix("getPrice") or contract.has_function_prefix("getReserve")
        has_swap = contract.has_function_prefix("swap")
        has_balance_compare = contract.has_function_prefix("_checkBalance") or contract.has_function_prefix(
            "_verifyCollateral"
        )

        signals: list[str] = []
        if callback_fns:
            signals.append(f"Flash loan callback functions: {', '.join(callback_fns)}")
        if has_receive:
            signals.append("receive()/fallback() available — callback attack surface")
        if has_oracle and callback_fns:
            signals.append("Oracle usage inside flash loan callback — price manipulation risk")
        if has_swap and callback_fns:
            signals.append("Swap logic combined with flash callback — sandwich/arbitrage pattern")
        if has_balance_compare:
            signals.append("Balance comparison post-callback — may be bypassable")

        if callback_fns:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=min(0.4 + len(signals) * 0.08, 0.85),
                    severity="critical" if (has_oracle and has_swap) else "high",
                    summary="Flash loan attack surface detected",
                    description=f"{contract.name or contract.address} has {len(callback_fns)} flash loan callback(s). "
                    f"{'Combined with oracle/swap logic — this is a high-value attack vector.' if has_oracle else 'Standalone flash callback may be part of legitimate DeFi protocol.'} "
                    f"Total signals: {len(signals)}.",
                    signals=signals,
                    test_instructions=[
                        "Check if flash loan callbacks make state-altering external calls",
                        "Verify if callback can re-enter the same contract or manipulate shared state",
                        "Simulate flash loan + price manipulation scenario",
                        "Check if balance verification after callback is strict or can be bypassed",
                        "Review if callback is permissionless or restricted to known addresses",
                    ],
                    remediation="Implement reentrancy guards on all callback functions. Verify prices after callback using TWAP. Use strict access control for flash loan receivers.",
                )
            )

        return hypotheses
