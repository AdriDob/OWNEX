"""Tests for Web3 Offensive Intelligence — Smart Contract Reasoners."""

from __future__ import annotations

from core.offensive.web3.engine import Web3OffensiveEngine
from core.offensive.web3.models import SmartContractInfo

# ── Reentrancy Reasoner ──


class TestReentrancyReasoner:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def test_withdraw_signals_reentrancy(self):
        contract = SmartContractInfo(
            address="0x1234",
            chain="ethereum",
            name="Vault",
            functions=["withdraw(uint256)", "deposit()", "balanceOf(address)"],
        )
        hypotheses = self.engine.analyze_contract(contract)
        reentrancy = [h for h in hypotheses if h.vulnerability_type == "reentrancy"]
        assert len(reentrancy) >= 1
        assert any("withdraw" in s for s in reentrancy[0].signals)

    def test_simple_contract_no_reentrancy_signal(self):
        contract = SmartContractInfo(
            address="0xdead",
            chain="ethereum",
            name="SimpleToken",
            functions=["transfer(address,uint256)", "balanceOf(address)"],
        )
        hypotheses = self.engine.analyze_contract(contract)
        reentrancy = [h for h in hypotheses if h.vulnerability_type == "reentrancy"]
        assert len(reentrancy) == 0

    def test_delegatecall_signals_high_severity(self):
        contract = SmartContractInfo(
            address="0xbeef",
            chain="ethereum",
            name="Proxy",
            functions=["delegatecall(bytes)", "withdraw(uint256)", "claim()", "call(address,bytes)"],
        )
        hypotheses = self.engine.analyze_contract(contract)
        reentrancy = [h for h in hypotheses if h.vulnerability_type == "reentrancy"]
        assert len(reentrancy) == 1
        assert reentrancy[0].severity == "high"


# ── ERC20 Reasoner ──


class TestERC20Reasoner:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def _make_contract(self, name: str, functions: list[str]) -> SmartContractInfo:
        return SmartContractInfo(address="0x1234", chain="ethereum", name=name, functions=functions)

    def test_basic_token_no_hypotheses(self):
        c = self._make_contract(
            "Standard",
            [
                "name",
                "symbol",
                "decimals",
                "totalSupply",
                "balanceOf",
                "transfer",
                "transferFrom",
                "approve",
                "allowance",
            ],
        )
        h = self.engine.analyze_contract(c)
        erc20 = [x for x in h if x.vulnerability_type == "erc20"]
        assert len(erc20) == 0

    def test_tax_token_detected(self):
        c = self._make_contract("TaxToken", ["transfer", "balanceOf", "_tax", "approve"])
        h = self.engine.analyze_contract(c)
        erc20 = [x for x in h if x.vulnerability_type == "erc20"]
        assert any("tax" in x.summary.lower() for x in erc20)

    def test_blacklist_detected(self):
        c = self._make_contract("BlacklistToken", ["transfer", "balanceOf", "blacklist", "isBlacklisted", "approve"])
        h = self.engine.analyze_contract(c)
        erc20 = [x for x in h if x.vulnerability_type == "erc20"]
        assert any("blacklist" in x.summary.lower() for x in erc20)

    def test_pausable_detected(self):
        c = self._make_contract("PausableToken", ["transfer", "balanceOf", "pause", "unpause", "approve"])
        h = self.engine.analyze_contract(c)
        erc20 = [x for x in h if x.vulnerability_type == "erc20"]
        assert any("pausable" in x.summary.lower() for x in erc20)

    def test_non_standard_detected(self):
        c = self._make_contract("Weird", ["transfer", "balanceOf"])
        h = self.engine.analyze_contract(c)
        erc20 = [x for x in h if x.vulnerability_type == "erc20"]
        assert any("non-standard" in x.summary.lower() for x in erc20)


# ── Access Control Reasoner ──


class TestAccessControlReasoner:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def test_initialize_without_guard(self):
        c = SmartContractInfo(
            address="0x1234",
            chain="ethereum",
            name="Upgradable",
            functions=["initialize(address)", "upgradeTo(address)"],
        )
        h = self.engine.analyze_contract(c)
        ac = [x for x in h if x.vulnerability_type == "access_control"]
        assert len(ac) >= 1
        assert any("initialize" in s.lower() for s in ac[0].signals)

    def test_no_access_control_signals(self):
        c = SmartContractInfo(address="0x1234", chain="ethereum", name="Simple", functions=["transfer", "balanceOf"])
        h = self.engine.analyze_contract(c)
        ac = [x for x in h if x.vulnerability_type == "access_control"]
        assert len(ac) == 0

    def test_critical_severity_for_upgrade_and_delegatecall(self):
        c = SmartContractInfo(
            address="0xbeef",
            chain="ethereum",
            name="DangerProxy",
            functions=["initialize(address)", "upgradeToAndCall(address,bytes)", "delegatecall(bytes)"],
        )
        h = self.engine.analyze_contract(c)
        ac = [x for x in h if x.vulnerability_type == "access_control"]
        assert len(ac) == 1
        assert ac[0].severity == "critical"


# ── Oracle Manipulation Reasoner ──


class TestOracleManipulationReasoner:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def test_oracle_functions_detected(self):
        c = SmartContractInfo(
            address="0x1234",
            chain="ethereum",
            name="PriceFeed",
            functions=["getPrice()", "getReserves()", "swap(address,uint256)"],
        )
        h = self.engine.analyze_contract(c)
        oracle = [x for x in h if x.vulnerability_type == "oracle_manipulation"]
        assert len(oracle) == 1
        assert "getReserve" in oracle[0].signals[0] or "getPrice" in oracle[0].signals[0]

    def test_no_oracle_signals(self):
        c = SmartContractInfo(address="0x1234", chain="ethereum", name="SimpleVault", functions=["deposit", "withdraw"])
        h = self.engine.analyze_contract(c)
        oracle = [x for x in h if x.vulnerability_type == "oracle_manipulation"]
        assert len(oracle) == 0

    def test_flash_loan_and_oracle_critical_severity(self):
        c = SmartContractInfo(
            address="0xbeef",
            chain="ethereum",
            name="DeFi",
            functions=["getPrice()", "flashLoan(address,uint256)", "swap(address,uint256)"],
        )
        h = self.engine.analyze_contract(c)
        oracle = [x for x in h if x.vulnerability_type == "oracle_manipulation"]
        assert len(oracle) == 1
        assert oracle[0].severity == "critical"


# ── Flash Loan Attack Reasoner ──


class TestFlashLoanAttackReasoner:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def test_callback_detected(self):
        c = SmartContractInfo(
            address="0x1234",
            chain="ethereum",
            name="FlashBorrower",
            functions=["executeOperation(address,uint256,uint256,bytes)"],
        )
        h = self.engine.analyze_contract(c)
        fl = [x for x in h if x.vulnerability_type == "flash_loan_attack"]
        assert len(fl) == 1
        assert "executeOperation" in fl[0].signals[0]

    def test_no_callback_no_hypothesis(self):
        c = SmartContractInfo(address="0x1234", chain="ethereum", name="SimpleVault", functions=["deposit", "withdraw"])
        h = self.engine.analyze_contract(c)
        fl = [x for x in h if x.vulnerability_type == "flash_loan_attack"]
        assert len(fl) == 0

    def test_oracle_and_swap_triggers_critical(self):
        c = SmartContractInfo(
            address="0xbeef",
            chain="ethereum",
            name="DeFiStrategy",
            functions=[
                "executeOperation(address,uint256,uint256,bytes)",
                "getPrice()",
                "swap(address,uint256)",
                "receive()",
            ],
        )
        h = self.engine.analyze_contract(c)
        fl = [x for x in h if x.vulnerability_type == "flash_loan_attack"]
        assert len(fl) == 1
        assert fl[0].severity == "critical"


# ── Engine ──


class TestWeb3OffensiveEngine:
    def setup_method(self):
        self.engine = Web3OffensiveEngine()

    def test_list_reasoners(self):
        reasoners = self.engine.list_reasoners()
        types = {r["vulnerability_type"] for r in reasoners}
        assert types == {"reentrancy", "erc20", "access_control", "oracle_manipulation", "flash_loan_attack"}

    def test_get_stats(self):
        stats = self.engine.get_stats()
        assert stats["total_reasoners"] == 5
        assert len(stats["vulnerability_types"]) == 5

    def test_unsupported_chain_skipped(self):
        contract = SmartContractInfo(
            address="0x1234",
            chain="solana",
            name="SolanaProj",
            functions=["withdraw(uint256)"],
        )
        h = self.engine.analyze_contract(contract)
        assert len(h) == 0

    def test_analyze_batch(self):
        contracts = [
            SmartContractInfo(address="0x1", chain="ethereum", name="A", functions=["balanceOf"]),
            SmartContractInfo(address="0x2", chain="ethereum", name="B", functions=["withdraw", "delegatecall"]),
        ]
        results = self.engine.analyze_batch(contracts)
        assert "0x1" in results
        assert "0x2" in results
        assert len(results["0x2"]) > len(results["0x1"])  # more signals on B

    def test_contract_has_function(self):
        c = SmartContractInfo(address="0x1", chain="ethereum", name="T", functions=["withdraw(uint256)", "deposit()"])
        assert c.has_function("withdraw")
        assert not c.has_function("nope")

    def test_contract_has_function_prefix(self):
        c = SmartContractInfo(
            address="0x1", chain="ethereum", name="T", functions=["withdraw(uint256)", "_withdrawFee()"]
        )
        assert c.has_function_prefix("withdraw")
        assert c.has_function_prefix("_withdraw")
        assert not c.has_function_prefix("nope")
