"""Unit tests for crypto connectors.

Tests cover:
- Dataclass serialization (CryptoBalance, CryptoTransaction, etc.)
- EVM connector (RPC + explorer API)
- Exchange connector (REST API + HMAC signing)
- BTC connector (Blockstream API)
- Solana connector (Solana RPC)
- Tron connector (TronGrid API)
- CryptoSyncManager (discovery, sync, summary)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from cores.crypto.base import (
    ChainType,
    ConnectionStatus,
    CryptoBalance,
    CryptoTransaction,
    CryptoWithdrawalInfo,
    SyncSnapshot,
)
from cores.crypto.btc import BLOCKSTREAM_BASE, BTCConnector
from cores.crypto.evm import ERC20_TOKENS, EVMConnector
from cores.crypto.exchange import ExchangeConnector
from cores.crypto.solana import SolanaConnector
from cores.crypto.sync_manager import _SYNC_HISTORY, CryptoSyncManager
from cores.crypto.tron import TRC20_TOKENS, TronConnector

# ── Test addresses ──────────────────────────────────────────────────
TEST_ADDR = "0x1234567890abcdef1234567890abcdef12345678"
TEST_BTC_ADDR = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
TEST_SOL_ADDR = "DcE4Tw3qkfC9XTLe3Mpn6p5W3HsfmN36TzkNwnC3gXb"
TEST_TRON_ADDR = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_sync_history():
    """Clear the global sync history before each test."""
    _SYNC_HISTORY.clear()


@pytest.fixture
def mock_vault():
    """Mock IdentityVault so connectors never touch disk."""
    with patch("cores.crypto.evm.get_identity_vault") as evm_vault, \
         patch("cores.crypto.exchange.get_identity_vault") as ex_vault, \
         patch("cores.crypto.btc.get_identity_vault") as btc_vault, \
         patch("cores.crypto.solana.get_identity_vault") as sol_vault, \
         patch("cores.crypto.tron.get_identity_vault") as tron_vault, \
         patch("cores.crypto.sync_manager.get_identity_vault") as sync_vault:
        inst = MagicMock()
        inst.get_credentials.return_value = {}
        evm_vault.return_value = inst
        ex_vault.return_value = inst
        btc_vault.return_value = inst
        sol_vault.return_value = inst
        tron_vault.return_value = inst
        sync_vault.return_value = inst
        yield inst


# ====================================================================
#  TestCryptoBase  —  dataclass / data-type tests
# ====================================================================
class TestCryptoBase:
    """CryptoBalance, CryptoTransaction, CryptoWithdrawalInfo, SyncSnapshot."""

    def test_crypto_balance_to_dict(self):
        bal = CryptoBalance(
            asset="ETH",
            symbol="ETH",
            balance=1.5,
            usd_value=3000.0,
            decimals=18,
            chain="ethereum",
            contract_address="0xabc",
            last_updated="2024-01-01T00:00:00",
            confidence=0.95,
        )
        d = bal.to_dict()
        assert d["asset"] == "ETH"
        assert d["symbol"] == "ETH"
        assert d["balance"] == 1.5
        assert d["usd_value"] == 3000.0
        assert d["decimals"] == 18
        assert d["chain"] == "ethereum"
        assert d["contract_address"] == "0xabc"
        assert d["confidence"] == 0.95

    def test_crypto_balance_usd_rounding(self):
        bal = CryptoBalance(asset="X", symbol="X", balance=1.0, usd_value=1.23456)
        d = bal.to_dict()
        assert d["usd_value"] == 1.23

    def test_crypto_transaction_to_dict(self):
        tx = CryptoTransaction(
            tx_hash="0xabc123",
            chain="ethereum",
            block_number=12345,
            timestamp="2024-01-01T00:00:00",
            from_address="0xfrom",
            to_address="0xto",
            asset="ETH",
            amount=1.0,
            usd_value=2000.0,
            fee=0.01,
            fee_asset="ETH",
            status="confirmed",
            tx_type="send",
        )
        d = tx.to_dict()
        assert d["tx_hash"] == "0xabc123"
        assert d["chain"] == "ethereum"
        assert d["block_number"] == 12345
        assert d["timestamp"] == "2024-01-01T00:00:00"
        assert d["from"] == "0xfrom"
        assert d["to"] == "0xto"
        assert d["asset"] == "ETH"
        assert d["amount"] == 1.0
        assert d["usd_value"] == 2000.0
        assert d["fee"] == 0.01
        assert d["fee_asset"] == "ETH"
        assert d["status"] == "confirmed"
        assert d["tx_type"] == "send"
        assert "raw_payload" not in d  # excluded from serialization

    def test_crypto_withdrawal_info_to_dict(self):
        wd = CryptoWithdrawalInfo(
            tx_hash="0xabc",
            chain="ethereum",
            asset="ETH",
            amount=1.0,
            usd_value=2000.0,
            destination_address="0xdest",
            fee=0.01,
            status="confirmed",
            confirmations=15,
            confirmations_required=12,
            timestamp="2024-01-01T00:00:00",
        )
        d = wd.to_dict()
        assert d["tx_hash"] == "0xabc"
        assert d["chain"] == "ethereum"
        assert d["amount"] == 1.0
        assert d["destination"] == "0xdest"
        assert d["confirmations"] == 15
        assert d["confirmations_required"] == 12
        assert d["status"] == "confirmed"
        assert d["finalized"] is True

    def test_withdrawal_is_finalized(self):
        wd = CryptoWithdrawalInfo(
            tx_hash="0x1", chain="eth", asset="ETH", amount=1.0,
            confirmations=12, confirmations_required=12,
        )
        assert wd.is_finalized() is True
        wd.confirmations = 11
        assert wd.is_finalized() is False
        wd.confirmations = 0
        assert wd.is_finalized() is False

    def test_sync_snapshot_to_dict(self):
        snap = SyncSnapshot(
            wallet_id="test_wallet",
            chain=ChainType.EVM,
            address=TEST_ADDR,
            balances=[CryptoBalance(asset="ETH", symbol="ETH", balance=1.0)],
            total_usd=2000.0,
            connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:00",
        )
        d = snap.to_dict()
        assert d["wallet_id"] == "test_wallet"
        assert d["chain"] == "evm"
        assert d["address"] == TEST_ADDR
        assert d["connection"] == "connected"
        assert d["total_usd"] == 2000.0
        assert len(d["balances"]) == 1
        assert d["transactions"] == []
        assert d["withdrawals"] == []
        assert d["error"] == ""
        assert d["synced_at"] == "2024-01-01T00:00:00"

    def test_sync_snapshot_defaults(self):
        snap = SyncSnapshot(wallet_id="w", chain=ChainType.BITCOIN)
        assert snap.balances == []
        assert snap.transactions == []
        assert snap.withdrawals == []
        assert snap.total_usd == 0.0
        assert snap.connection == ConnectionStatus.UNCONFIGURED
        assert snap.error == ""
        assert snap.synced_at == ""


# ====================================================================
#  TestEVMConnector
# ====================================================================
class TestEVMConnector:
    """EVM RPC + explorer-API tests (all HTTP mocked)."""

    RPC_URL = "https://mock-rpc.example.com"

    @patch("cores.crypto.evm._rpc_call")
    def test_connect_success(self, mock_rpc):
        mock_rpc.return_value = {"jsonrpc": "2.0", "id": 1, "result": "0x1345c6e"}
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.CONNECTED
        assert conn._status == ConnectionStatus.CONNECTED
        mock_rpc.assert_called_once_with(self.RPC_URL, "eth_blockNumber", [])

    @patch("cores.crypto.evm._rpc_call")
    def test_connect_failure(self, mock_rpc):
        mock_rpc.return_value = None
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.ERROR

    def test_connect_no_rpc_url(self):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        conn._rpc_url = ""
        status = conn.connect()
        assert status == ConnectionStatus.UNCONFIGURED

    @patch("cores.crypto.evm._rpc_call")
    def test_get_balance_native(self, mock_rpc):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        conn._status = ConnectionStatus.CONNECTED

        def side_effect(url, method, params):
            if method == "eth_getBalance":
                return {"jsonrpc": "2.0", "id": 1, "result": "0xde0b6b3a7640000"}
            if method == "eth_call":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x0"}
            return None

        mock_rpc.side_effect = side_effect
        balances = conn.get_balance()
        assert len(balances) == 1
        assert balances[0].asset == "ETH"
        assert balances[0].symbol == "ETH"
        assert balances[0].balance == 1.0
        assert balances[0].decimals == 18
        assert balances[0].chain == "ethereum"

    @patch("cores.crypto.evm._rpc_call")
    def test_get_balance_erc20(self, mock_rpc):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        conn._status = ConnectionStatus.CONNECTED

        def side_effect(url, method, params):
            if method == "eth_getBalance":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x0"}
            if method == "eth_call":
                # Return non-zero for USDT, zero for others
                usdt_addr = ERC20_TOKENS["ethereum"]["USDT"]
                if params and isinstance(params, list) and len(params) > 0:
                    call_data = params[0] if isinstance(params[0], dict) else {}
                    if call_data.get("to", "").lower() == usdt_addr.lower():
                        # 100 * 10^18 = 0x56bc75e2d63100000 → balance=100 with 18 decimals
                        return {"jsonrpc": "2.0", "id": 1, "result": "0x56bc75e2d63100000"}
                return {"jsonrpc": "2.0", "id": 1, "result": "0x0"}
            return None

        mock_rpc.side_effect = side_effect
        balances = conn.get_balance()
        usdt = [b for b in balances if b.symbol == "USDT"]
        assert len(usdt) == 1
        assert usdt[0].balance == 100.0
        assert usdt[0].contract_address == ERC20_TOKENS["ethereum"]["USDT"]

    def test_get_balance_no_address(self):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address="")
        conn._status = ConnectionStatus.CONNECTED
        assert conn.get_balance() == []

    @patch("cores.crypto.evm._rpc_call")
    @patch("cores.crypto.evm._explorer_api_call")
    def test_get_transactions(self, mock_explorer, mock_rpc):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)

        # Native tx
        native_tx = {
            "blockNumber": "0x100000",
            "timeStamp": "0x12345678",
            "hash": "0xnatxh",
            "from": TEST_ADDR,
            "to": "0xabcdef1234567890abcdef1234567890abcdef12",
            "value": "0xde0b6b3a7640000",
            "gasPrice": "0x3b9aca00",
            "gasUsed": "0x5208",
            "isError": "0",
            "confirmations": "50",
        }
        # ERC20 tx (decimal timestamps) — newer than native
        erc20_tx = {
            "blockNumber": "100001",
            "timeStamp": "305419897",
            "hash": "0xerctxh",
            "from": "0xother1234567890abcdef1234567890abcdef12",
            "to": TEST_ADDR,
            "tokenSymbol": "USDT",
            "value": "1000000000",
            "tokenDecimal": "6",
        }

        mock_explorer.side_effect = [
            {"status": "1", "message": "OK", "result": [native_tx]},
            {"status": "1", "message": "OK", "result": [erc20_tx]},
        ]
        mock_rpc.return_value = None

        txs = conn.get_transactions(limit=10)
        assert len(txs) == 2
        # ERC20 tx timestamp (305419897) > native tx timestamp (0x12345678 = 305419896)
        assert txs[0].tx_hash == "0xerctxh"
        assert txs[0].asset == "USDT"
        assert txs[0].amount == 1000.0  # 1000000000 / 1e6
        assert txs[0].tx_type == "receive"

        assert txs[1].tx_hash == "0xnatxh"
        assert txs[1].asset == "ETH"
        assert txs[1].amount == 1.0
        assert txs[1].tx_type == "send"

    @patch("cores.crypto.evm._rpc_call")
    @patch("cores.crypto.evm._explorer_api_call")
    def test_get_transactions_empty(self, mock_explorer, mock_rpc):
        """Empty explorer result should return empty list, not crash."""
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)
        mock_explorer.return_value = {"status": "0", "message": "No records found"}
        txs = conn.get_transactions()
        assert txs == []

    @patch("cores.crypto.evm._rpc_call")
    @patch("cores.crypto.evm._explorer_api_call")
    def test_get_withdrawals(self, mock_explorer, mock_rpc):
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)

        outgoing = {
            "blockNumber": "0x100000",
            "timeStamp": "0x12345678",
            "hash": "0xwd1",
            "from": TEST_ADDR,
            "to": "0xdest",
            "value": "0xde0b6b3a7640000",
            "gasPrice": "0x3b9aca00",
            "gasUsed": "0x5208",
            "isError": "0",
            "confirmations": "100",
        }
        incoming = {
            "blockNumber": "0x100001",
            "timeStamp": "0x12345679",
            "hash": "0xincoming",
            "from": "0xother",
            "to": TEST_ADDR,
            "value": "0xde0b6b3a7640000",
            "gasPrice": "0x3b9aca00",
            "gasUsed": "0x5208",
            "isError": "0",
            "confirmations": "99",
        }

        mock_explorer.return_value = {"status": "1", "message": "OK", "result": [outgoing, incoming]}
        mock_rpc.return_value = None

        wds = conn.get_withdrawals()
        assert len(wds) == 1
        assert wds[0].tx_hash == "0xwd1"
        assert wds[0].amount == 1.0
        assert wds[0].destination_address == "0xdest"
        assert wds[0].confirmations == 100
        assert wds[0].status == "confirmed"

    @patch("cores.crypto.evm._rpc_call")
    @patch("cores.crypto.evm._explorer_api_call")
    def test_sync_full(self, mock_explorer, mock_rpc):
        """Full sync() pipeline via mocked internal functions."""
        conn = EVMConnector("ew", "ethereum", rpc_url=self.RPC_URL, address=TEST_ADDR)

        def rpc_side(url, method, params):
            if method == "eth_blockNumber":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x1345c6e"}
            if method == "eth_getBalance":
                return {"jsonrpc": "2.0", "id": 1, "result": "0xde0b6b3a7640000"}
            if method == "eth_call":
                return {"jsonrpc": "2.0", "id": 1, "result": "0x0"}
            return None

        mock_rpc.side_effect = rpc_side
        mock_explorer.return_value = {"status": "0", "message": "No records found"}

        snap = conn.sync()
        assert snap.wallet_id == "ew"
        assert snap.chain == ChainType.EVM
        assert snap.connection == ConnectionStatus.CONNECTED
        assert len(snap.balances) == 1
        assert snap.balances[0].asset == "ETH"
        assert snap.balances[0].balance == 1.0
        assert snap.transactions == []
        assert snap.withdrawals == []
        assert snap.error == ""
        assert snap.synced_at != ""


# ====================================================================
#  TestExchangeConnector
# ====================================================================
class TestExchangeConnector:
    """Exchange connector tests — mocked urllib."""

    @patch("urllib.request.urlopen")
    def test_connect_success(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({"balances": []}).encode()
        mock_urlopen.return_value.__enter__.return_value = resp

        conn = ExchangeConnector("ex_test", "binance")
        conn._api_key = "test_key"
        conn._api_secret = "test_secret"
        conn._exchange_name = "binance"

        status = conn.connect()
        assert status == ConnectionStatus.CONNECTED

    def test_connect_no_creds(self):
        """No API key/secret → UNCONFIGURED."""
        conn = ExchangeConnector("ex_test", "binance")
        conn._api_key = ""
        conn._api_secret = ""
        status = conn.connect()
        assert status == ConnectionStatus.UNCONFIGURED

    @patch("urllib.request.urlopen")
    def test_get_balance(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "balances": [
                {"asset": "BTC", "free": "1.0", "locked": "0.5"},
                {"asset": "ETH", "free": "10.0", "locked": "0.0"},
                {"asset": "ZERO", "free": "0", "locked": "0"},
            ],
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = resp

        conn = ExchangeConnector("ex_test", "binance")
        conn._api_key = "test_key"
        conn._api_secret = "test_secret"
        conn._status = ConnectionStatus.CONNECTED

        balances = conn.get_balance()
        assert len(balances) == 2
        btc = next(b for b in balances if b.asset == "BTC")
        assert btc.balance == 1.5
        assert btc.chain == "exchange:binance"
        eth = next(b for b in balances if b.asset == "ETH")
        assert eth.balance == 10.0

    @patch("urllib.request.urlopen")
    def test_get_transactions(self, mock_urlopen):
        conn = ExchangeConnector("ex_test", "binance")
        conn._api_key = "key"
        conn._api_secret = "secret"
        conn._status = ConnectionStatus.CONNECTED

        trade_resp = MagicMock()
        trade_resp.read.return_value = json.dumps([
            {"id": "trade1", "symbol": "BTCUSDT", "qty": "0.1",
             "quoteQty": "5000", "commission": "0.001",
             "time": 1700000000000, "isBuyer": True},
        ]).encode()

        deposit_resp = MagicMock()
        deposit_resp.read.return_value = json.dumps([
            {"txId": "dep1", "coin": "ETH", "amount": "2.0",
             "insertTime": 1700001000000, "status": "1"},
        ]).encode()

        mock_urlopen.return_value.__enter__.side_effect = [trade_resp, deposit_resp]

        txs = conn.get_transactions(limit=10)
        assert len(txs) == 2
        # deposit has later timestamp
        dep = next(t for t in txs if t.tx_type == "deposit")
        assert dep.asset == "ETH"
        assert dep.amount == 2.0
        assert dep.tx_hash == "dep1"

        trade = next(t for t in txs if t.tx_type != "deposit")
        assert trade.asset == "BTCUSDT"
        assert trade.amount == 0.1
        assert trade.usd_value == 5000.0
        assert trade.fee == 0.001

    @patch("urllib.request.urlopen")
    def test_binance_signing(self, mock_urlopen):
        """Verify HMAC-SHA256 signature generation."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        conn = ExchangeConnector("ex_sig", "binance")
        conn._api_key = "test_key_123"
        conn._api_secret = "test_secret_456"

        fixed_ts_ms = 1700000000000
        with patch("time.time", return_value=fixed_ts_ms / 1000):
            conn._binance_request("/api/v3/account", {"symbol": "BTCUSDT"})

        req = mock_urlopen.call_args[0][0]
        url = req.full_url
        headers = req.headers

        header_key = next((k for k in headers if k.lower() == "x-mbx-apikey"), None)
        assert header_key is not None, "X-MBX-APIKEY header missing"
        assert headers[header_key] == "test_key_123"
        assert f"timestamp={fixed_ts_ms}" in url
        assert "recvWindow=5000" in url
        assert "signature=" in url

        # Re-derive expected signature
        query_part = url.split("?")[1].rsplit("&signature=", 1)[0]
        expected_sig = hmac.new(
            b"test_secret_456",
            query_part.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        assert url.endswith(expected_sig)


# ====================================================================
#  TestBTCConnector
# ====================================================================
class TestBTCConnector:
    """BTC connector tests — mocked Blockstream API."""

    @patch("cores.crypto.btc._api_get")
    def test_connect_success(self, mock_get):
        mock_get.return_value = "840000"
        conn = BTCConnector("btc_w", address=TEST_BTC_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.CONNECTED
        mock_get.assert_called_once_with(f"{BLOCKSTREAM_BASE}/blocks/tip/height")

    @patch("cores.crypto.btc._api_get")
    def test_connect_failure(self, mock_get):
        mock_get.return_value = None
        conn = BTCConnector("btc_w", address=TEST_BTC_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.ERROR

    @patch("cores.crypto.btc._api_get_json")
    @patch("cores.crypto.btc._api_get")
    def test_get_balance(self, mock_get, mock_get_json):
        mock_get.return_value = "840000"  # needed by connect
        mock_get_json.return_value = {
            "chain_stats": {"funded_txo_sum": 100000000, "spent_txo_sum": 20000000},
            "mempool_stats": {"funded_txo_sum": 0, "spent_txo_sum": 0},
        }
        conn = BTCConnector("btc_w", address=TEST_BTC_ADDR)
        conn.connect()
        balances = conn.get_balance()
        assert len(balances) == 1
        assert balances[0].asset == "BTC"
        assert balances[0].balance == 0.8  # (100M - 20M) / 1e8
        assert balances[0].decimals == 8
        assert balances[0].chain == "bitcoin"

    @patch("cores.crypto.btc._api_get_json")
    @patch("cores.crypto.btc._api_get")
    def test_get_transactions(self, mock_get, mock_get_json):
        mock_get.return_value = "840000"

        tx_data = {
            "txid": "btctx1",
            "status": {"confirmed": True, "block_height": 800000, "block_time": 1234567890},
            "vin": [{"prevout": {"scriptpubkey_address": TEST_BTC_ADDR, "value": 50000000}}],
            "vout": [
                {"scriptpubkey_address": "1other", "value": 49000000},
                {"scriptpubkey_address": TEST_BTC_ADDR, "value": 900000},
            ],
        }
        mock_get_json.return_value = [tx_data]
        conn = BTCConnector("btc_w", address=TEST_BTC_ADDR)
        conn.connect()
        txs = conn.get_transactions()
        assert len(txs) == 1
        assert txs[0].tx_hash == "btctx1"
        assert txs[0].tx_type == "send"
        assert txs[0].amount == pytest.approx(0.491)  # (50000000 - 900000) / 1e8
        assert txs[0].from_address == TEST_BTC_ADDR
        assert txs[0].to_address == "1other"

    @patch("cores.crypto.btc._api_get_json")
    @patch("cores.crypto.btc._api_get")
    def test_get_transactions_no_address(self, mock_get, mock_get_json):
        conn = BTCConnector("btc_w", address="")
        assert conn.get_transactions() == []


# ====================================================================
#  TestSolanaConnector
# ====================================================================
class TestSolanaConnector:
    """Solana connector tests — mocked RPC."""

    @patch("cores.crypto.solana._rpc_call")
    def test_connect_success(self, mock_rpc):
        mock_rpc.return_value = {"jsonrpc": "2.0", "result": {"value": "abc123"}}
        conn = SolanaConnector("sol_w", address=TEST_SOL_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.CONNECTED

    @patch("cores.crypto.solana._rpc_call")
    def test_connect_failure(self, mock_rpc):
        mock_rpc.return_value = None
        conn = SolanaConnector("sol_w", address=TEST_SOL_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.ERROR

    def test_connect_no_address(self):
        conn = SolanaConnector("sol_w", address="")
        status = conn.connect()
        assert status == ConnectionStatus.UNCONFIGURED

    @patch("cores.crypto.solana._rpc_call")
    def test_get_balance(self, mock_rpc):
        def side_effect(method, params):
            if method == "getRecentBlockhash":
                return {"jsonrpc": "2.0", "result": {"value": "abc"}}
            if method == "getBalance":
                return {"jsonrpc": "2.0", "result": {"value": 1_000_000_000}}
            return None

        mock_rpc.side_effect = side_effect
        conn = SolanaConnector("sol_w", address=TEST_SOL_ADDR)
        conn.connect()
        balances = conn.get_balance()
        assert len(balances) == 1
        assert balances[0].asset == "SOL"
        assert balances[0].balance == 1.0
        assert balances[0].decimals == 9

    @patch("cores.crypto.solana._rpc_call")
    def test_get_transactions(self, mock_rpc):
        def side_effect(method, params):
            if method == "getRecentBlockhash":
                return {"jsonrpc": "2.0", "result": {"value": "abc"}}
            if method == "getSignaturesForAddress":
                return {"jsonrpc": "2.0", "result": [{"signature": "sig1"}]}
            if method == "getTransaction":
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "meta": {
                            "err": None,
                            "fee": 5000,
                            "preBalances": [1_000_000_000, 0],
                            "postBalances": [500_000_000, 499_000_000],
                        },
                        "blockTime": 1234567890,
                        "slot": 200000000,
                        "transaction": {
                            "message": {
                                "accountKeys": [
                                    {"pubkey": TEST_SOL_ADDR},
                                    {"pubkey": "other_sol_addr"},
                                ],
                            },
                        },
                    },
                }
            return None

        mock_rpc.side_effect = side_effect
        conn = SolanaConnector("sol_w", address=TEST_SOL_ADDR)
        conn.connect()
        txs = conn.get_transactions()
        assert len(txs) == 1
        assert txs[0].tx_hash == "sig1"
        assert txs[0].tx_type == "send"
        assert txs[0].from_address == TEST_SOL_ADDR
        assert txs[0].to_address == "other_sol_addr"
        # amount_sol = change/1e9 → (500M-1000M)/1e9 = -0.5, abs=0.5, minus fee
        # fee = 5000/1e9 = 0.000005, so amount = 0.5 - 0.000005 = 0.499995
        assert txs[0].amount == pytest.approx(0.499995)
        assert txs[0].fee == pytest.approx(0.000005)

    @patch("cores.crypto.solana._rpc_call")
    def test_get_withdrawals(self, mock_rpc):
        def side_effect(method, params):
            if method == "getRecentBlockhash":
                return {"jsonrpc": "2.0", "result": {"value": "abc"}}
            if method == "getSignaturesForAddress":
                return {"jsonrpc": "2.0", "result": [{"signature": "sig_wd"}]}
            if method == "getTransaction":
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "meta": {
                            "err": None,
                            "fee": 5000,
                            "preBalances": [1_000_000_000, 0],
                            "postBalances": [500_000_000, 499_000_000],
                        },
                        "blockTime": 1234567890,
                        "slot": 200,
                        "transaction": {
                            "message": {
                                "accountKeys": [
                                    {"pubkey": TEST_SOL_ADDR},
                                    {"pubkey": "to_addr"},
                                ],
                            },
                        },
                    },
                }
            return None

        mock_rpc.side_effect = side_effect
        conn = SolanaConnector("sol_w", address=TEST_SOL_ADDR)
        conn.connect()
        wds = conn.get_withdrawals()
        assert len(wds) == 1
        assert wds[0].tx_hash == "sig_wd"
        assert wds[0].asset == "SOL"
        assert wds[0].destination_address == "to_addr"


# ====================================================================
#  TestTronConnector
# ====================================================================
class TestTronConnector:
    """Tron connector tests — mocked TronGrid API."""

    @patch("cores.crypto.tron._tron_api_call")
    def test_connect_success(self, mock_api):
        mock_api.return_value = {"data": [{"address": TEST_TRON_ADDR, "balance": 0}]}
        conn = TronConnector("trx_w", address=TEST_TRON_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.CONNECTED
        mock_api.assert_called_once_with(f"/v1/accounts/{TEST_TRON_ADDR}")

    @patch("cores.crypto.tron._tron_api_call")
    def test_connect_failure(self, mock_api):
        mock_api.return_value = {"data": []}
        conn = TronConnector("trx_w", address=TEST_TRON_ADDR)
        status = conn.connect()
        assert status == ConnectionStatus.ERROR

    def test_connect_no_address(self):
        conn = TronConnector("trx_w", address="")
        status = conn.connect()
        assert status == ConnectionStatus.UNCONFIGURED

    @patch("cores.crypto.tron._tron_api_call")
    def test_get_balance_trx_and_trc20(self, mock_api):
        conn = TronConnector("trx_w", address=TEST_TRON_ADDR)
        conn._status = ConnectionStatus.CONNECTED

        mock_api.return_value = {
            "data": [{
                "address": TEST_TRON_ADDR,
                "balance": 10_000_000,  # 10 TRX
                "trc20": [
                    {TRC20_TOKENS["USDT"]: "5000000"},  # 5 USDT
                ],
            }],
        }

        balances = conn.get_balance()
        assert len(balances) == 2

        trx = next(b for b in balances if b.asset == "TRX")
        assert trx.balance == 10.0
        assert trx.decimals == 6

        usdt = next(b for b in balances if b.asset == "USDT")
        assert usdt.balance == 5.0
        assert usdt.contract_address == TRC20_TOKENS["USDT"]

    @patch("cores.crypto.tron._tron_api_call")
    def test_get_transactions(self, mock_api):
        conn = TronConnector("trx_w", address=TEST_TRON_ADDR)

        def side_effect(path, params=None):
            if path == f"/v1/accounts/{TEST_TRON_ADDR}":
                return {"data": [{"address": TEST_TRON_ADDR, "balance": 0}]}
            if path == f"/v1/accounts/{TEST_TRON_ADDR}/transactions":
                return {
                    "data": [{
                        "txID": "trontx1",
                        "block_timestamp": 1700000000000,
                        "from": TEST_TRON_ADDR,
                        "to": "other_tron_addr",
                        "value": 10_000_000,
                        "fee": 100_000,
                        "raw_data": {
                            "contract": [{
                                "parameter": {
                                    "value": {
                                        "owner_address": TEST_TRON_ADDR,
                                        "to_address": "other_tron_addr",
                                        "amount": 10_000_000,
                                    },
                                },
                            }],
                        },
                    }],
                }
            return None

        mock_api.side_effect = side_effect
        conn.connect()
        txs = conn.get_transactions()
        assert len(txs) == 1
        assert txs[0].tx_hash == "trontx1"
        assert txs[0].asset == "TRX"
        assert txs[0].amount == 10.0  # 10_000_000 / 1e6
        assert txs[0].fee == 0.1  # 100_000 / 1e6
        assert txs[0].tx_type == "send"
        assert txs[0].from_address == TEST_TRON_ADDR
        assert txs[0].to_address == "other_tron_addr"


# ====================================================================
#  TestCryptoSyncManager
# ====================================================================
class TestCryptoSyncManager:
    """Sync-manager tests — discovery, sync, history, summary."""

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_register_connector(self, mock_publish):
        mgr = CryptoSyncManager()
        conn = MagicMock()
        conn.wallet_id = "test_wallet"
        conn.chain = ChainType.EVM
        mgr.register_connector(conn)
        assert "test_wallet" in mgr.connectors

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_discover_wallets(self, mock_publish, mock_vault):
        mock_vault.list_accounts.return_value = [
            {"provider_name": "evm_ethereum", "email": "",
             "session_state": "disconnected", "last_checked": None,
             "health_status": "unknown", "has_credentials": True},
            {"provider_name": "btc_mainnet", "email": "",
             "session_state": "disconnected", "last_checked": None,
             "health_status": "unknown", "has_credentials": True},
            {"provider_name": "exchange_binance", "email": "",
             "session_state": "disconnected", "last_checked": None,
             "health_status": "unknown", "has_credentials": True},
            {"provider_name": "solana_mainnet", "email": "",
             "session_state": "disconnected", "last_checked": None,
             "health_status": "unknown", "has_credentials": True},
            {"provider_name": "tron_mainnet", "email": "",
             "session_state": "disconnected", "last_checked": None,
             "health_status": "unknown", "has_credentials": True},
        ]

        mgr = CryptoSyncManager()
        mgr.discover_wallets()
        conns = mgr.connectors
        assert "evm:ethereum" in conns
        assert "btc:btc_mainnet" in conns
        assert "exchange:binance" in conns
        assert "solana:mainnet" in conns
        assert "tron:tron_mainnet" in conns

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_sync_wallet(self, mock_publish):
        mgr = CryptoSyncManager()
        conn = MagicMock()
        conn.wallet_id = "evm_test"
        conn.chain = ChainType.EVM
        conn.sync.return_value = SyncSnapshot(
            wallet_id="evm_test",
            chain=ChainType.EVM,
            balances=[CryptoBalance(asset="ETH", symbol="ETH", balance=1.0, usd_value=3000.0)],
            total_usd=3000.0,
            connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:00",
        )
        mgr.register_connector(conn)

        snap = mgr.sync_wallet("evm_test")
        assert snap is not None
        assert snap.wallet_id == "evm_test"
        assert snap.connection == ConnectionStatus.CONNECTED
        assert snap.total_usd == 3000.0
        conn.sync.assert_called_once()
        mock_publish.assert_called_once()

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_sync_wallet_unknown(self, mock_publish):
        mgr = CryptoSyncManager()
        snap = mgr.sync_wallet("nonexistent")
        assert snap is None

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_sync_all(self, mock_publish):
        mgr = CryptoSyncManager()

        c1 = MagicMock()
        c1.wallet_id = "evm:eth"
        c1.chain = ChainType.EVM
        c1.sync.return_value = SyncSnapshot(
            wallet_id="evm:eth", chain=ChainType.EVM,
            total_usd=1000.0, connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:00",
        )

        c2 = MagicMock()
        c2.wallet_id = "exchange:binance"
        c2.chain = ChainType.EXCHANGE
        c2.sync.return_value = SyncSnapshot(
            wallet_id="exchange:binance", chain=ChainType.EXCHANGE,
            total_usd=2000.0, connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:00",
        )

        c3 = MagicMock()
        c3.wallet_id = "btc:test"
        c3.chain = ChainType.BITCOIN
        c3.sync.return_value = SyncSnapshot(
            wallet_id="btc:test", chain=ChainType.BITCOIN,
            total_usd=500.0, connection=ConnectionStatus.ERROR,
            error="Connection failed",
            synced_at="2024-01-01T00:00:00",
        )

        mgr.register_connector(c1)
        mgr.register_connector(c2)
        mgr.register_connector(c3)

        results = mgr.sync_all()
        assert len(results) == 3
        assert results["evm:eth"].total_usd == 1000.0
        assert results["exchange:binance"].total_usd == 2000.0
        assert results["btc:test"].connection == ConnectionStatus.ERROR
        assert mock_publish.call_count == 3

    @patch("cores.crypto.sync_manager.publish_financial_event")
    def test_get_summary(self, mock_publish, mock_vault):
        mgr = CryptoSyncManager()

        c1 = MagicMock()
        c1.wallet_id = "evm:eth"
        c1.chain = ChainType.EVM
        c1.sync.return_value = SyncSnapshot(
            wallet_id="evm:eth", chain=ChainType.EVM,
            total_usd=1000.0, connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:01",
        )

        c2 = MagicMock()
        c2.wallet_id = "exchange:binance"
        c2.chain = ChainType.EXCHANGE
        c2.sync.return_value = SyncSnapshot(
            wallet_id="exchange:binance", chain=ChainType.EXCHANGE,
            total_usd=2000.0, connection=ConnectionStatus.CONNECTED,
            synced_at="2024-01-01T00:00:02",
        )

        mgr.register_connector(c1)
        mgr.register_connector(c2)
        mgr.sync_all()

        summary = mgr.get_summary()
        assert summary["total_wallets"] == 2
        assert summary["connected_wallets"] == 2
        assert summary["total_usd"] == 3000.0
        assert summary["last_sync"] == "2024-01-01T00:00:02"
        assert summary["by_chain"]["evm"]["count"] == 1
        assert summary["by_chain"]["evm"]["usd_value"] == 1000.0
        assert summary["by_chain"]["exchange"]["count"] == 1
        assert summary["by_chain"]["exchange"]["usd_value"] == 2000.0
        assert summary["by_chain"]["bitcoin"]["count"] == 0
        assert summary["by_chain"]["bitcoin"]["usd_value"] == 0.0
