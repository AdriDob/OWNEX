"""CSV Importer Connector — imports transaction history from CSV files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.csv")


class CSVImporterConnector(AtlasConnector):
    connector_id = "csv_importer"
    display_name = "CSV Importer"

    def __init__(self) -> None:
        self._ready = False

    async def connect(self) -> bool:
        self._ready = True
        return True

    async def disconnect(self) -> None:
        self._ready = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._ready)

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def import_csv(self, filepath: str) -> list[NormalizedTransaction]:
        """Import transactions from a CSV file. Auto-detects format."""
        path = Path(filepath)
        if not path.exists():
            logger.warning("CSV not found: %s", filepath)
            return []
        try:
            with open(path) as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return []
                transactions = []
                for row in reader:
                    tx = self._normalize(row)
                    if tx:
                        transactions.append(tx)
            logger.info("Imported %d transactions from CSV", len(transactions))
            return transactions
        except Exception as exc:
            logger.error("CSV import failed: %s", exc)
            return []

    def _normalize(self, row: dict) -> NormalizedTransaction | None:
        symbol = row.get("Symbol") or row.get("Ticker") or row.get("asset") or ""
        if not symbol:
            return None
        qty = self._safe_float(row.get("Quantity") or row.get("amount") or row.get("filled") or 0)
        price = self._safe_float(row.get("Price") or row.get("AvgPrice") or 0)
        fees = self._safe_float(row.get("Fees") or row.get("Commission") or 0)
        raw_type = str(row.get("Type") or row.get("Side") or "buy").lower()
        tx_type = "buy" if raw_type in ("buy", "bought") else "sell" if raw_type in ("sell", "sold") else raw_type
        return NormalizedTransaction(
            symbol=symbol,
            tx_type=tx_type,
            quantity=qty,
            price=price,
            fees=fees,
            total=qty * price,
            executed_at=row.get("Date") or row.get("date") or "",
            platform="csv",
        )

    @staticmethod
    def _safe_float(val: object) -> float:
        try:
            return float(str(val).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [{"key": "csv_file", "label": "CSV File Path", "type": "text"}]
