"""CSV Importer for ODYSSEY — import bet history from CSV files."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from apps.odyssey.connectors.base import OdysseyConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedBet, NormalizedMarket

logger = logging.getLogger("orion.odyssey.connectors.csv")


class CSVImporterConnector(OdysseyConnector):
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

    async def get_bets(self, since_days: int = 30) -> list[NormalizedBet]:
        return []

    async def get_markets(self, sport: str = "") -> list[NormalizedMarket]:
        return []

    async def get_balance(self) -> float:
        return 0.0

    async def import_csv(self, filepath: str) -> list[NormalizedBet]:
        path = Path(filepath)
        if not path.exists():
            return []
        try:
            with open(path) as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return []
                bets = []
                for row in reader:
                    bet = self._normalize(row)
                    if bet:
                        bets.append(bet)
            logger.info("Imported %d bets from CSV", len(bets))
            return bets
        except Exception as exc:
            logger.error("CSV import failed: %s", exc)
            return []

    def _normalize(self, row: dict) -> NormalizedBet | None:
        event = row.get("Event") or row.get("event") or row.get("description") or ""
        if not event:
            return None
        platform = row.get("Platform") or row.get("platform") or "manual"
        odds = self._safe_float(row.get("Odds") or row.get("odds") or 0)
        stake = self._safe_float(row.get("Stake") or row.get("stake") or 0)
        payout = self._safe_float(row.get("Payout") or row.get("payout") or 0)
        raw_outcome = str(row.get("Outcome") or row.get("result") or "pending").lower()
        outcome = (
            "win"
            if raw_outcome in ("win", "won")
            else "loss"
            if raw_outcome in ("loss", "lost")
            else raw_outcome
            if raw_outcome in ("push", "pending")
            else "pending"
        )
        return NormalizedBet(
            event=event,
            market=row.get("Market") or row.get("market") or "",
            platform=platform,
            odds=float(odds),
            stake=float(stake),
            payout=float(payout),
            outcome=outcome,
            executed_at=row.get("Date") or row.get("date") or "",
        )

    @staticmethod
    def _safe_float(val: object) -> float:
        try:
            return float(str(val).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    async def get_config_fields(self) -> list[dict]:
        return [{"key": "csv_file", "label": "CSV File Path", "type": "text"}]
