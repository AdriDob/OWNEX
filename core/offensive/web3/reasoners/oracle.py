from __future__ import annotations

from core.offensive.web3.base import BaseWeb3Reasoner
from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis

ORACLE_SIGNAL_FUNCTIONS = {
    "getPrice",
    "getLatestPrice",
    "getReserve",
    "getReserves",
    "getAmountsOut",
    "getAmountsIn",
    "spotPrice",
    "getSpotPrice",
    "slot0",
    "observe",
    "currentPrice",
    "getPriceUSD",
    "peek",
    "read",
    "latestAnswer",
    "latestRoundData",
}


class OracleManipulationReasoner(BaseWeb3Reasoner):
    @property
    def vulnerability_type(self) -> str:
        return "oracle_manipulation"

    def _detect_oracle_functions(self, contract: SmartContractInfo) -> list[str]:
        found: list[str] = []
        for fn in contract.functions or []:
            name = fn.split("(")[0]
            if name in ORACLE_SIGNAL_FUNCTIONS:
                found.append(name)
        return found

    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        slither_results = self._analyze_with_slither(contract)
        if slither_results:
            return slither_results

        hypotheses: list[Web3Hypothesis] = []
        oracle_fns = self._detect_oracle_functions(contract)
        uses_twap = contract.has_function("observe") or contract.has_function_prefix("twap")

        signals: list[str] = []
        if oracle_fns:
            signals.append(f"Oracle price functions: {', '.join(oracle_fns)}")
        if contract.has_function_prefix("getReserve") and not uses_twap:
            signals.append("Spot reserve price without TWAP — manipulable via flash loan")
        if contract.has_function("slot0") and not uses_twap:
            signals.append("Uniswap V3 slot0 price (single-pool, manipulable)")
        if contract.has_function_prefix("flashLoan") and oracle_fns:
            signals.append("Flash loan + oracle combo — TWAP bypass risk")
        if contract.has_function_prefix("swap") and oracle_fns:
            signals.append("Swap function using oracle price — sandwich attack vector")

        if signals:
            severity = "critical" if (contract.has_function_prefix("flashLoan") and oracle_fns) else "high"
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=min(0.4 + len(signals) * 0.1, 0.9),
                    severity=severity,
                    summary="Oracle manipulation vulnerability",
                    description=f"{contract.name or contract.address} uses on-chain price data that may be manipulable. "
                    f"{len(signals)} signals detected. "
                    f"{'TWAP oracle detected — lower manipulation risk.' if uses_twap else 'No TWAP detected — spot price can be manipulated via flash loans.'}",
                    signals=signals,
                    test_instructions=[
                        f"Check if {contract.name or 'contract'} uses spot price from a single DEX pool",
                        "Simulate flash loan + swap to move price and call oracle-dependent function",
                        "Verify if TWAP is used for price reads",
                        "Check number of blocks TWAP samples (larger = safer)",
                    ],
                    remediation="Use manipulation-resistant oracles (Chainlink, MakerDAO). Implement TWAP with adequate sample size. Add price deviation checks.",
                )
            )

        return hypotheses
