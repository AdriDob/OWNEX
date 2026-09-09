from __future__ import annotations

from core.offensive.web3.base import BaseWeb3Reasoner
from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis

ERC20_STANDARD = {
    "name",
    "symbol",
    "decimals",
    "totalSupply",
    "balanceOf",
    "transfer",
    "transferFrom",
    "approve",
    "allowance",
}


class ERC20Reasoner(BaseWeb3Reasoner):
    """Analyze ERC20 tokens for honeypot, tax, blacklist, and approval abuse."""

    @property
    def vulnerability_type(self) -> str:
        return "erc20"

    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        slither_results = self._analyze_with_slither(contract)
        if slither_results:
            return slither_results

        hypotheses: list[Web3Hypothesis] = []
        functions = {fn.split("(")[0] for fn in (contract.functions or [])}

        missing_standard = ERC20_STANDARD - functions
        has_tax = (
            contract.has_function_prefix("_tax") or contract.has_function("tax") or contract.has_function_prefix("fee")
        )
        has_blacklist = contract.has_function_prefix("blacklist") or contract.has_function("isBlacklisted")
        has_exclude = contract.has_function_prefix("exclude") or contract.has_function_prefix("include")
        has_pause = contract.has_function_prefix("pause")

        if has_tax:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=0.5,
                    severity="medium",
                    summary="Buy/sell tax or fee mechanism detected",
                    description=f"{contract.name or contract.address} implements fee-on-transfer logic. "
                    f"Dynamic tax rates can be abused to rug-pull or block sells.",
                    signals=["Fee/tax functions present in ABI", "Potential dynamic fee mechanism"],
                    test_instructions=[
                        "Check if tax rate is modifiable by owner",
                        "Simulate buy and sell with different amounts to detect variable tax",
                        "Verify tax is collected on every transfer, not just swaps",
                    ],
                    remediation="Ensure tax rate is capped and cannot be set to 100%. Use timelock for tax changes.",
                )
            )

        if has_blacklist or has_exclude:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=0.55,
                    severity="high",
                    summary="Blacklist/exclude mechanism — risk of blocked transfers",
                    description=f"{contract.name or contract.address} has blacklist functionality. "
                    f"Owner can freeze specific addresses, preventing them from selling.",
                    signals=["Blacklist or exclusion functions found"],
                    test_instructions=[
                        "Check who can add/remove addresses from blacklist",
                        "Verify if blacklist is permanent or reversible",
                        "Test if blacklisted address can still receive tokens",
                    ],
                    remediation="Add timelock for blacklist operations. Document blacklist policy transparently.",
                )
            )

        if has_pause:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=0.45,
                    severity="medium",
                    summary="Pausable token — owner can halt all transfers",
                    description=f"{contract.name or contract.address} is pausable. Owner can freeze all token transfers at will.",
                    signals=["Pause/unpause functions detected"],
                    test_instructions=[
                        "Check who can trigger pause (owner, role, multisig)",
                        "Verify if paused state prevents all transfers or just specific ones",
                    ],
                    remediation="Use multisig for pause control. Implement pause delay or timelock.",
                )
            )

        if missing_standard and len(missing_standard) > 2:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=0.3,
                    severity="low",
                    summary="Non-standard ERC20 implementation",
                    description=f"Missing {len(missing_standard)} standard ERC20 functions: {', '.join(sorted(missing_standard))}. "
                    f"May cause compatibility issues with DEXes and wallets.",
                    signals=[f"Missing ERC20 functions: {', '.join(sorted(missing_standard))}"],
                    test_instructions=[
                        "Check if missing functions have non-standard equivalents",
                        "Test token transfer on Uniswap",
                    ],
                    remediation="Ensure ERC20 interface compliance for broad compatibility.",
                )
            )

        return hypotheses
