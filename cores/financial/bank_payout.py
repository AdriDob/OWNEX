"""Bank Payout Connector — detects and tracks incoming payouts via bank APIs.

Supports:
  - Plaid API (/transactions/sync endpoint)
  - Manual CSV import
  - Webhook receiver for payment notifications

Payout sources detected:
  - HackerOne, Bugcrowd, Intigriti, Stripe, generic bank transfers
"""

from __future__ import annotations

import contextlib
import csv
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from cores.financial.events import publish_financial_event
from cores.financial.withdrawal import ConfirmationMethod, complete_withdrawal, create_withdrawal
from cores.identity_vault import get_identity_vault
from cores.ledger import LedgerEvent, record_event

logger = logging.getLogger("cateye.financial.bank_payout")

PLATFORM_PATTERNS: dict[str, list[str]] = {
    "hackerone": [r"HACKERONE", r"HackerOne\s*Inc", r"H1\s+Payout"],
    "bugcrowd": [r"BUG\s*CROWD", r"Bugcrowd\s*Inc", r"BC\s+Payout"],
    "intigriti": [r"INTIGRITI", r"Intigriti"],
    "stripe": [r"STRIPE", r"Stripe\s*Payout", r"STRIPE\s+TRANSFER"],
    "yeswehack": [r"YESWEHACK", r"YesWeHack"],
    "huntr": [r"HUNTR", r"huntr\s+payout"],
    "immunefi": [r"MMUNEFI", r"Immunefi"],
    "synack": [r"SYNACK", r"Synack"],
}

DEFAULT_PLAID_ENV = "sandbox"
PLAID_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
}


@dataclass
class PayoutEntry:
    source: str
    transaction_id: str
    amount: float
    currency: str
    date: str
    description: str
    account_name: str
    account_number: str = ""
    platform: str = ""
    confidence: float = 0.5
    raw: dict[str, Any] = field(default_factory=dict)


class PlaidProvider:
    """Connects to the Plaid API for transaction data."""

    def __init__(self, client_id: str = "", secret: str = "", env: str = DEFAULT_PLAID_ENV) -> None:
        self.client_id = client_id
        self.secret = secret
        self.env = env if env in PLAID_URLS else DEFAULT_PLAID_ENV
        self.base_url = PLAID_URLS[self.env]

    def _request(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8")
        req = Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "PLAID-CLIENT-ID": self.client_id,
                "PLAID-SECRET": self.secret,
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            error_body = ""
            if hasattr(e, "read"):
                with contextlib.suppress(Exception):
                    error_body = e.read().decode("utf-8")
            logger.error("Plaid API error on %s: %s — %s", path, e, error_body)
            raise

    def create_link_token(self, user_id: str) -> dict[str, Any]:
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
            "user": {"client_user_id": user_id},
            "products": ["transactions"],
            "country_codes": ["US"],
            "language": "en",
        }
        result = self._request("/link/token/create", body)
        logger.info("Plaid link token created for user %s", user_id)
        return result

    def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
            "public_token": public_token,
        }
        result = self._request("/item/public_token/exchange", body)
        access_token = result.get("access_token", "")
        item_id = result.get("item_id", "")
        if access_token and item_id:
            vault = get_identity_vault()
            vault.store_credentials(
                provider=f"plaid_{item_id}",
                email="",
                token=access_token,
                metadata={"item_id": item_id, "env": self.env},
            )
            logger.info("Plaid access_token stored for item %s", item_id)
        return result

    def sync_transactions(self, access_token: str, cursor: str = "") -> dict[str, Any]:
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
            "access_token": access_token,
            "cursor": cursor,
        }
        result = self._request("/transactions/sync", body)
        return result

    def get_accounts(self, access_token: str) -> dict[str, Any]:
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
            "access_token": access_token,
        }
        return self._request("/accounts/get", body)

    def get_balances(self, access_token: str) -> dict[str, Any]:
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
            "access_token": access_token,
        }
        return self._request("/accounts/balance/get", body)


class CSVImporter:
    """Parses bank CSV files and detects payout entries."""

    @staticmethod
    def import_csv(file_path: str, account_name: str) -> list[PayoutEntry]:
        entries: list[PayoutEntry] = []
        if not os.path.exists(file_path):
            logger.warning("CSV file not found: %s", file_path)
            return entries

        try:
            with open(file_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    entry = CSVImporter._row_to_entry(row, headers, account_name, file_path)
                    if entry:
                        entries.append(entry)
        except Exception as e:
            logger.error("Failed to parse CSV %s: %s", file_path, e)

        logger.info("Imported %d entries from CSV %s", len(entries), file_path)
        return entries

    @staticmethod
    def _row_to_entry(row: dict[str, str], headers: list[str], account_name: str, source_file: str) -> PayoutEntry | None:
        def _find_col(*names: str) -> str:
            for name in names:
                for h in headers:
                    if h.strip().lower() == name.lower():
                        return row.get(h, "").strip()
            return ""

        txn_id = _find_col("transaction id", "id", "txn_id", "reference", "transaction_id")
        amount_raw = _find_col("amount", "value", "sum", "credit", "debit", "monto")
        date_val = _find_col("date", "transaction date", "posting date", "fecha", "timestamp")
        desc = _find_col("description", "memo", "details", "narrative", "payee", "name", "descripcion")

        if not all([txn_id, amount_raw, date_val, desc]):
            return None

        try:
            amount = float(amount_raw.replace(",", "").replace("$", "").replace(" ", ""))
        except (ValueError, TypeError):
            return None

        entry = PayoutEntry(
            source="csv",
            transaction_id=txn_id,
            amount=abs(amount),
            currency="USD",
            date=date_val,
            description=desc,
            account_name=account_name,
            raw={"file": source_file, "row": row},
        )
        return entry

    @staticmethod
    def detect_payouts(entries: list[PayoutEntry]) -> list[PayoutEntry]:
        detected: list[PayoutEntry] = []
        for entry in entries:
            platform, confidence = CSVImporter._classify(entry.description)
            if platform:
                entry.platform = platform
                entry.confidence = max(entry.confidence, confidence)
                detected.append(entry)
        return detected

    @staticmethod
    def _classify(description: str) -> tuple[str, float]:
        desc_upper = description.upper()
        for platform, patterns in PLATFORM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, desc_upper):
                    return platform, 0.8
        if re.search(r"DIRECT\s+DEPOSIT|WIRE\s+TRANSFER|ACH\s+CREDIT|SEPA|BANK\s+TRANSFER", desc_upper):
            return "bank_transfer", 0.4
        return "", 0.0


class WebhookHandler:
    """Processes webhook notifications from Plaid and custom payment sources."""

    @staticmethod
    def handle_plaid_webhook(payload: dict[str, Any]) -> list[PayoutEntry]:
        entries: list[PayoutEntry] = []
        webhook_type = payload.get("webhook_type", "")
        webhook_code = payload.get("webhook_code", "")

        logger.info("Plaid webhook received: %s / %s", webhook_type, webhook_code)

        if webhook_code == "SYNC_UPDATES_AVAILABLE":
            item_id = payload.get("item_id", "")
            logger.info("Sync updates available for item %s — trigger sync", item_id)

        elif webhook_code == "TRANSACTIONS_REMOVED":
            removed = payload.get("removed_transactions", [])
            logger.info("Transactions removed: %d entries", len(removed))

        elif webhook_code == "DEFAULT_UPDATE":
            entries = WebhookHandler._extract_transactions(payload)

        return entries

    @staticmethod
    def handle_custom_webhook(data: dict[str, Any]) -> list[PayoutEntry]:
        entries: list[PayoutEntry] = []
        txn_id = data.get("transaction_id", "") or str(uuid.uuid4())
        amount = float(data.get("amount", 0))
        currency = data.get("currency", "USD")
        date_val = data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        description = data.get("description", "")
        account_name = data.get("account_name", "webhook")

        if amount > 0:
            entry = PayoutEntry(
                source="webhook",
                transaction_id=txn_id,
                amount=amount,
                currency=currency,
                date=date_val,
                description=description,
                account_name=account_name,
                raw=data,
            )
            platform, confidence = CSVImporter._classify(description)
            entry.platform = platform
            entry.confidence = max(entry.confidence, confidence)
            entries.append(entry)

        return entries

    @staticmethod
    def _extract_transactions(payload: dict[str, Any]) -> list[PayoutEntry]:
        entries: list[PayoutEntry] = []
        for txn in payload.get("transactions", []):
            amount = abs(float(txn.get("amount", 0)))
            if amount <= 0:
                continue
            entry = PayoutEntry(
                source="plaid_webhook",
                transaction_id=txn.get("transaction_id", ""),
                amount=amount,
                currency=txn.get("iso_currency_code", "USD"),
                date=txn.get("date", ""),
                description=txn.get("name", ""),
                account_name=txn.get("account_name", ""),
                raw=txn,
            )
            platform, confidence = CSVImporter._classify(entry.description)
            entry.platform = platform
            entry.confidence = max(entry.confidence, confidence)
            entries.append(entry)
        return entries


class BankPayoutConnector:
    """Connects to bank APIs to detect and track incoming payouts."""

    def __init__(self, wallet_id: str = "default") -> None:
        self.wallet_id = wallet_id
        self._plaid_provider: PlaidProvider | None = None
        self._csv_importer = CSVImporter()
        self._webhook_handler = WebhookHandler()
        self._detected_payouts: list[PayoutEntry] = []
        self._last_sync: float = 0.0
        self._sync_status = "never"
        self._load_plaid_credentials()

    def _load_plaid_credentials(self) -> None:
        vault = get_identity_vault()
        plaid_creds = vault.get_credentials("plaid")
        if plaid_creds:
            client_id = plaid_creds.get("token", "").split("|")[0] if "|" in plaid_creds.get("token", "") else ""
            secret = plaid_creds.get("password", "")
            env = plaid_creds.get("env", DEFAULT_PLAID_ENV)
            if not client_id:
                client_id = plaid_creds.get("client_id", "")
            if not secret:
                secret = plaid_creds.get("secret", "")
            if client_id and secret:
                self._plaid_provider = PlaidProvider(
                    client_id=client_id,
                    secret=secret,
                    env=env,
                )
                logger.info("Plaid provider initialized (%s)", env)
            else:
                logger.info("Plaid credentials incomplete — Plaid sync disabled")
        else:
            logger.info("No Plaid credentials found — Plaid sync disabled")
            vault.store_credentials(
                provider="plaid",
                email="plaid_service",
                metadata={"configured": "false", "env": DEFAULT_PLAID_ENV},
            )

    def configure_plaid(self, client_id: str, secret: str, env: str = DEFAULT_PLAID_ENV) -> None:
        vault = get_identity_vault()
        vault.store_credentials(
            provider="plaid",
            email="plaid_service",
            token=f"{client_id}|{secret}",
            password=secret,
            metadata={"client_id": client_id, "env": env},
        )
        self._plaid_provider = PlaidProvider(
            client_id=client_id,
            secret=secret,
            env=env,
        )
        logger.info("Plaid configured: env=%s", env)

    def sync_all(self) -> list[PayoutEntry]:
        all_payouts: list[PayoutEntry] = []

        if self._plaid_provider:
            try:
                plaid_payouts = self._sync_plaid_accounts()
                all_payouts.extend(plaid_payouts)
                self._sync_status = "ok"
            except Exception as e:
                logger.error("Plaid sync failed: %s", e)
                self._sync_status = "error"

        self._last_sync = time.time()

        for payout in all_payouts:
            if payout not in self._detected_payouts:
                self._detected_payouts.append(payout)

        logger.info("Bank payout sync complete: %d payouts detected", len(all_payouts))
        return all_payouts

    def _sync_plaid_accounts(self) -> list[PayoutEntry]:
        payouts: list[PayoutEntry] = []
        vault = get_identity_vault()

        for provider_name in vault.list_accounts():
            pname = provider_name.get("provider_name", "")
            if not pname.startswith("plaid_"):
                continue
            creds = vault.get_credentials(pname)
            access_token = creds.get("token", "")
            if not access_token:
                continue

            try:
                sync_result = self._plaid_provider.sync_transactions(access_token)
                added = sync_result.get("added", [])
                modified = sync_result.get("modified", [])
                all_txns = added + modified

                for txn in all_txns:
                    amount = abs(float(txn.get("amount", 0)))
                    if amount <= 0:
                        continue
                    entry = PayoutEntry(
                        source="plaid",
                        transaction_id=txn.get("transaction_id", ""),
                        amount=amount,
                        currency=txn.get("iso_currency_code", "USD"),
                        date=txn.get("date", ""),
                        description=txn.get("name", ""),
                        account_name=txn.get("account_name", ""),
                        raw=txn,
                    )
                    platform, confidence = self.detect_platform_payouts([txn])
                    if platform:
                        entry.platform = platform
                        entry.confidence = max(entry.confidence, confidence)
                        payouts.append(entry)
                    elif amount > 0:
                        payouts.append(entry)

                cursor = sync_result.get("next_cursor", "")
                if cursor:
                    vault.store_credentials(
                        provider=pname,
                        email=creds.get("email", ""),
                        token=access_token,
                        metadata={"cursor": cursor, "item_id": pname.replace("plaid_", "")},
                    )

            except Exception as e:
                logger.error("Failed to sync plaid account %s: %s", pname, e)

        return payouts

    def detect_platform_payouts(self, transactions: list[dict[str, Any]]) -> tuple[str, float]:
        best_platform = ""
        best_confidence = 0.0
        for txn in transactions:
            name = txn.get("name", "")
            desc = txn.get("description", "")
            combined = f"{name} {desc}"
            platform, confidence = CSVImporter._classify(combined)
            if confidence > best_confidence:
                best_platform = platform
                best_confidence = confidence
        return best_platform, best_confidence

    def record_payout(self, entry: PayoutEntry) -> dict[str, Any]:
        if not entry.platform:
            logger.warning("Cannot record payout without detected platform: %s", entry.transaction_id)
            return {"recorded": False, "reason": "no_platform_detected"}

        if entry not in self._detected_payouts:
            self._detected_payouts.append(entry)

        ledger_entry = record_event(
            event=LedgerEvent.PAYOUT_RECEIVED,
            amount=entry.amount,
            currency=entry.currency,
            description=f"Payout from {entry.platform}: {entry.description[:80]}",
            source=f"bank_payout:{entry.source}",
            source_id=entry.transaction_id,
            platform=entry.platform,
            metadata={
                "account": entry.account_name,
                "transaction_id": entry.transaction_id,
                "confidence": entry.confidence,
                "date": entry.date,
            },
        )

        withdrawal = create_withdrawal(
            amount=entry.amount,
            currency=entry.currency,
            platform=entry.platform,
            target_account="bank:" + entry.account_name,
            method="bank_transfer",
            metadata={
                "payout_entry_id": entry.transaction_id,
                "source": entry.source,
                "confidence": entry.confidence,
            },
        )

        complete_withdrawal(
            withdrawal_id=withdrawal.id,
            confirmation=ConfirmationMethod.RECONCILIATION,
            tx_hash=entry.transaction_id,
        )

        publish_financial_event(
            event_type="financial:payout_received",
            amount=entry.amount,
            currency=entry.currency,
            platform=entry.platform,
            description=f"Pago recibido de {entry.platform}: ${entry.amount:.2f}",
            metadata={
                "transaction_id": entry.transaction_id,
                "source": entry.source,
                "ledger_entry_id": ledger_entry.entry_id,
            },
        )

        logger.info(
            "Payout recorded: %.2f %s from %s (txn: %s, ledger: %s)",
            entry.amount, entry.currency, entry.platform,
            entry.transaction_id[:16], ledger_entry.entry_id[:8],
        )

        return {
            "recorded": True,
            "ledger_entry_id": ledger_entry.entry_id,
            "withdrawal_id": withdrawal.id,
        }

    def import_csv(self, file_path: str, account_name: str) -> list[PayoutEntry]:
        entries = self._csv_importer.import_csv(file_path, account_name)
        detected = self._csv_importer.detect_payouts(entries)
        for payout in detected:
            if payout not in self._detected_payouts:
                self._detected_payouts.append(payout)
        return detected

    def handle_plaid_webhook(self, payload: dict[str, Any]) -> list[PayoutEntry]:
        entries = self._webhook_handler.handle_plaid_webhook(payload)
        for entry in entries:
            if entry not in self._detected_payouts:
                self._detected_payouts.append(entry)
        return entries

    def handle_custom_webhook(self, data: dict[str, Any]) -> list[PayoutEntry]:
        entries = self._webhook_handler.handle_custom_webhook(data)
        for entry in entries:
            if entry not in self._detected_payouts:
                self._detected_payouts.append(entry)
        return entries

    def get_status(self) -> dict[str, Any]:
        plaid_configured = self._plaid_provider is not None
        vault = get_identity_vault()
        plaid_accounts = [
            a for a in vault.list_accounts()
            if a.get("provider_name", "").startswith("plaid_")
        ]
        return {
            "plaid_configured": plaid_configured,
            "plaid_accounts": len(plaid_accounts),
            "plaid_env": self._plaid_provider.env if self._plaid_provider else None,
            "last_sync": self._last_sync,
            "last_sync_iso": datetime.fromtimestamp(self._last_sync, tz=timezone.utc).isoformat() if self._last_sync else "",
            "sync_status": self._sync_status,
            "detected_payouts": len(self._detected_payouts),
            "wallet_id": self.wallet_id,
        }

    def get_detected_payouts(self) -> list[dict[str, Any]]:
        return [
            {
                "source": p.source,
                "transaction_id": p.transaction_id,
                "amount": p.amount,
                "currency": p.currency,
                "date": p.date,
                "description": p.description,
                "account_name": p.account_name,
                "platform": p.platform,
                "confidence": p.confidence,
            }
            for p in self._detected_payouts
        ]


_CONNECTOR: BankPayoutConnector | None = None


def get_bank_payout_connector() -> BankPayoutConnector:
    global _CONNECTOR
    if _CONNECTOR is None:
        _CONNECTOR = BankPayoutConnector()
    return _CONNECTOR
