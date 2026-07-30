"""Takenos connector — balance tracking + CSV import.

Takenos is a virtual USD wallet for LATAM freelancers.
No public REST API available — supports:
  - Manual balance entry
  - CSV import from Takenos extracts
  - On-chain Solana USDC tracking (optional, if wallet linked)
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO

logger = logging.getLogger("ownex.financial.takenos")


@dataclass
class TakenosBalance:
    usd_balance: float = 0.0
    ars_balance: float = 0.0
    usdc_solana: float = 0.0
    pending_deposits: float = 0.0
    takecard_available: float = 0.0
    last_updated: str = ""


@dataclass
class TakenosTransaction:
    tx_id: str
    date: str
    description: str
    amount: float
    currency: str = "USD"
    tx_type: str = "deposit"  # deposit, withdrawal, conversion, card_payment
    status: str = "completed"
    reference: str = ""


class TakenosConnector:
    """Takenos virtual wallet connector.

    Usage:
        conn = TakenosConnector()
        conn.set_balance_manual(usd=1500.00)
        conn.import_csv(csv_content)
        state = conn.get_state()
    """

    provider_id = "takenos"
    display_name = "Takenos"

    def __init__(self) -> None:
        self._balance = TakenosBalance()
        self._transactions: list[TakenosTransaction] = []
        self._solana_wallet: str = ""
        self._csv_loaded = False
        self._has_api = False

    # ── Manual entry ─────────────────────────────────

    def set_balance_manual(
        self,
        usd: float = 0.0,
        ars: float = 0.0,
        pending: float = 0.0,
        takecard: float = 0.0,
    ) -> None:
        """Set current Takenos balance manually."""
        self._balance.usd_balance = usd
        self._balance.ars_balance = ars
        self._balance.pending_deposits = pending
        self._balance.takecard_available = takecard
        self._balance.last_updated = datetime.now(UTC).isoformat()
        logger.info("Takenos balance updated: USD=%.2f, ARS=%.2f", usd, ars)

    def link_solana_wallet(self, address: str) -> None:
        """Link a Solana wallet address to track USDC on-chain.

        Takenos uses Solana USDC internally. Linking your deposit wallet
        allows automatic balance tracking.
        """
        self._solana_wallet = address
        logger.info("Takenos linked to Solana wallet: %s", address)

    # ── CSV import ───────────────────────────────────

    def import_csv(self, csv_content: str) -> dict:
        """Import a Takenos CSV extract.

        Expected columns: date, description, amount, currency, type, status, reference
        """
        records = []
        errors: list[str] = []
        reader = csv.DictReader(StringIO(csv_content))
        for i, row in enumerate(reader):
            try:
                tx = TakenosTransaction(
                    tx_id=row.get("id", str(i)),
                    date=row.get("date", ""),
                    description=row.get("description", ""),
                    amount=float(row.get("amount", 0)),
                    currency=row.get("currency", "USD"),
                    tx_type=row.get("type", "deposit"),
                    status=row.get("status", "completed"),
                    reference=row.get("reference", ""),
                )
                self._transactions.append(tx)
                records.append(tx.tx_id)
            except (ValueError, KeyError) as exc:
                errors.append(f"Row {i}: {exc}")

        self._csv_loaded = True
        self._recompute_balance_from_txns()

        logger.info("Takenos CSV import: %d records, %d errors", len(records), len(errors))
        return {"imported": len(records), "errors": errors, "total": len(self._transactions)}

    def import_csv_file(self, filepath: str) -> dict:
        """Import a Takenos CSV file from disk."""
        if not os.path.isfile(filepath):
            return {"imported": 0, "errors": [f"File not found: {filepath}"], "total": len(self._transactions)}
        with open(filepath) as f:
            content = f.read()
        return self.import_csv(content)

    # ── On-chain sync (Solana USDC) ──────────────────

    def sync_from_solana(self) -> dict:
        """Sync balance from Solana USDC wallet (if linked)."""
        if not self._solana_wallet:
            return {"synced": False, "error": "No Solana wallet linked"}

        try:
            from cores.crypto.solana import SolanaConnector

            connector = SolanaConnector(wallet_id=f"takenos_{self._solana_wallet[:8]}")
            connector.set_address(self._solana_wallet)
            status = connector.connect()
            if status.value != "connected":
                return {"synced": False, "error": f"Solana connect failed: {status.value}"}

            balances = connector.get_balance()
            for bal in balances:
                if bal.asset in ("USDC", "usd-coin"):
                    self._balance.usdc_solana = bal.balance
                    self._balance.usd_balance = max(self._balance.usd_balance, bal.usd_value)

            self._balance.last_updated = datetime.now(UTC).isoformat()
            logger.info("Takenos synced from Solana: %.2f USDC", self._balance.usdc_solana)
            return {"synced": True, "usdc_balance": self._balance.usdc_solana}
        except Exception as exc:
            logger.warning("Takenos Solana sync failed: %s", exc)
            return {"synced": False, "error": str(exc)}

    # ── State ────────────────────────────────────────

    def get_state(self) -> dict:
        """Return current Takenos state for the unified dashboard."""
        return {
            "provider": "takenos",
            "display_name": "Takenos",
            "balance": {
                "usd": round(self._balance.usd_balance, 2),
                "ars": round(self._balance.ars_balance, 2),
                "usdc_solana": round(self._balance.usdc_solana, 2),
                "pending": round(self._balance.pending_deposits, 2),
                "takecard": round(self._balance.takecard_available, 2),
            },
            "solana_wallet_linked": bool(self._solana_wallet),
            "csv_loaded": self._csv_loaded,
            "transaction_count": len(self._transactions),
            "has_api": self._has_api,
            "recent_transactions": [self._tx_to_dict(t) for t in self._transactions[-10:]],
            "last_updated": self._balance.last_updated,
        }

    def get_summary(self) -> dict:
        """Compact summary for dashboard."""
        return {
            "balance_usd": round(self._balance.usd_balance, 2),
            "pending": round(self._balance.pending_deposits, 2),
            "solana_usdc": round(self._balance.usdc_solana, 2),
            "csv_loaded": self._csv_loaded,
            "wallet_linked": bool(self._solana_wallet),
        }

    def health(self) -> dict:
        """Connection health."""
        has_data = self._csv_loaded or bool(self._balance.last_updated) or bool(self._solana_wallet)
        return {
            "provider": "takenos",
            "available": has_data,
            "csv_loaded": self._csv_loaded,
            "wallet_linked": bool(self._solana_wallet),
            "manual_balance_set": bool(self._balance.last_updated),
            "balance_usd": round(self._balance.usd_balance, 2),
            "has_api": self._has_api,
        }

    # ── Internal ─────────────────────────────────────

    def _recompute_balance_from_txns(self) -> None:
        total = 0.0
        for tx in self._transactions:
            if tx.tx_type in ("deposit", "conversion_in"):
                total += tx.amount
            elif tx.tx_type in ("withdrawal", "card_payment", "conversion_out"):
                total -= tx.amount
        if total != 0:
            self._balance.usd_balance = total

    @staticmethod
    def _tx_to_dict(tx: TakenosTransaction) -> dict:
        return {
            "id": tx.tx_id,
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "currency": tx.currency,
            "type": tx.tx_type,
            "status": tx.status,
            "reference": tx.reference,
        }


_takenos_connector: TakenosConnector | None = None


def get_takenos_connector() -> TakenosConnector:
    global _takenos_connector
    if _takenos_connector is None:
        _takenos_connector = TakenosConnector()
    return _takenos_connector
