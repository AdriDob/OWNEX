from __future__ import annotations

from core.offensive.web3.base import BaseWeb3Reasoner
from core.offensive.web3.models import SmartContractInfo, Web3Hypothesis


class AccessControlReasoner(BaseWeb3Reasoner):
    @property
    def vulnerability_type(self) -> str:
        return "access_control"

    def analyze(self, contract: SmartContractInfo) -> list[Web3Hypothesis]:
        slither_results = self._analyze_with_slither(contract)
        if slither_results:
            return slither_results

        hypotheses: list[Web3Hypothesis] = []
        signals: list[str] = []
        functions = {fn.split("(")[0] for fn in (contract.functions or [])}

        if "initialize" in functions and "__Initializable_init" not in str(contract.functions):
            signals.append("initialize() without initializer guard — can be frontrun or re-initialized")
        if "upgradeTo" in functions or "upgradeToAndCall" in functions:
            signals.append("Upgrade function detected — risk of malicious proxy replacement")
        if "renounceOwnership" in functions:
            signals.append("renounceOwnership() available — can permanently lock contract")
        if "delegatecall" in functions:
            signals.append("delegatecall detected — storage collision risk")
        if "setImplementation" in functions:
            signals.append("Implementation can be swapped — arbitrary code execution risk")
        if "changeAdmin" in functions or "transferOwnership" in functions:
            signals.append("Admin/ownership transfer function — verify access control")

        if signals:
            hypotheses.append(
                Web3Hypothesis(
                    vulnerability_type=self.vulnerability_type,
                    contract_address=contract.address,
                    chain=contract.chain,
                    confidence=min(0.3 + len(signals) * 0.1, 0.8),
                    severity="critical" if ("upgradeToAndCall" in functions or "delegatecall" in functions) else "high",
                    summary="Access control weaknesses detected",
                    description=f"{contract.name or contract.address} has {len(signals)} access control signals: "
                    f"{'; '.join(signals)}. These patterns have historically led to critical exploits.",
                    signals=signals,
                    test_instructions=[
                        "Check who holds OWNER_ROLE or DEFAULT_ADMIN_ROLE",
                        "Verify initialize() can only be called once and by deployer",
                        "Test if upgradeTo() is protected by onlyOwner",
                        "Check if renounceOwnership has safety checks",
                        f"Verify {contract.address} proxy admin on Etherscan",
                    ],
                    remediation="Use Ownable2Step or OpenZeppelin AccessControl. Add timelock for upgrades. Verify proxy admin security.",
                )
            )

        return hypotheses
