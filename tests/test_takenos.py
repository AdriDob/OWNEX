"""Tests for Takenos connector."""

from __future__ import annotations

from cores.financial.takenos.connector import TakenosConnector


class TestTakenosConnector:
    def test_initial_state(self):
        conn = TakenosConnector()
        state = conn.get_state()
        assert state["provider"] == "takenos"
        assert state["balance"]["usd"] == 0.0
        assert state["has_api"] is False
        assert state["csv_loaded"] is False

    def test_set_balance_manual(self):
        conn = TakenosConnector()
        conn.set_balance_manual(usd=1500.50, ars=500000, pending=200.0, takecard=300.0)
        state = conn.get_state()
        assert state["balance"]["usd"] == 1500.50
        assert state["balance"]["ars"] == 500000
        assert state["balance"]["pending"] == 200.0
        assert state["balance"]["takecard"] == 300.0
        assert state["last_updated"] != ""

    def test_get_summary(self):
        conn = TakenosConnector()
        conn.set_balance_manual(usd=2500.0)
        summary = conn.get_summary()
        assert summary["balance_usd"] == 2500.0

    def test_health_no_data(self):
        conn = TakenosConnector()
        health = conn.health()
        assert health["available"] is False
        assert health["balance_usd"] == 0.0

    def test_health_with_csv(self):
        conn = TakenosConnector()
        conn.set_balance_manual(usd=1000.0)
        health = conn.health()
        assert health["available"] is True

    def test_link_solana_wallet(self):
        conn = TakenosConnector()
        conn.link_solana_wallet("SolanaWalletAddress123")
        state = conn.get_state()
        assert state["solana_wallet_linked"] is True

    def test_import_csv(self):
        conn = TakenosConnector()
        csv_content = (
            "date,description,amount,currency,type,status,reference\n"
            "2026-01-01,Bounty H1,1000.00,USD,deposit,completed,REF001\n"
            "2026-01-02,Withdrawal,-200.00,USD,withdrawal,completed,REF002\n"
            "2026-01-03,Card payment,-50.00,USD,card_payment,completed,REF003\n"
        )
        result = conn.import_csv(csv_content)
        assert result["imported"] == 3
        assert result["total"] == 3
        assert result["errors"] == []

    def test_import_csv_recomputes_balance(self):
        conn = TakenosConnector()
        csv_content = (
            "date,description,amount,currency,type,status,reference\n"
            "2026-01-01,Deposit,1000.00,USD,deposit,completed,REF001\n"
        )
        conn.import_csv(csv_content)
        summary = conn.get_summary()
        assert summary["balance_usd"] == 1000.0

    def test_import_csv_no_file(self):
        conn = TakenosConnector()
        result = conn.import_csv_file("/tmp/nonexistent_takenos_file.csv")
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]

    def test_sync_from_solana_no_wallet(self):
        conn = TakenosConnector()
        result = conn.sync_from_solana()
        assert result["synced"] is False
        assert "wallet linked" in result["error"]

    def test_get_summary_empty(self):
        conn = TakenosConnector()
        summary = conn.get_summary()
        assert summary["balance_usd"] == 0.0
        assert summary["pending"] == 0.0

    def test_multiple_balance_updates(self):
        conn = TakenosConnector()
        conn.set_balance_manual(usd=100.0)
        assert conn.get_summary()["balance_usd"] == 100.0
        conn.set_balance_manual(usd=200.0)
        assert conn.get_summary()["balance_usd"] == 200.0
