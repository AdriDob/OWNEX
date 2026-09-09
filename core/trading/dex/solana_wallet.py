from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey

logger = logging.getLogger("orion.trading.solana_wallet")


class SolanaWallet:
    def __init__(self, private_key_b58: str | None = None, keypair_path: str | None = None) -> None:
        self._keypair: Keypair | None = None

        if private_key_b58:
            self._keypair = Keypair.from_base58_string(private_key_b58)
        elif keypair_path:
            self._load_from_file(keypair_path)
        else:
            self._load_from_env()

        if self._keypair is None:
            logger.warning("No Solana wallet configured — RealExecutor will fail on execution")

    def _load_from_env(self) -> None:
        raw = os.getenv("SOLANA_PRIVATE_KEY", "")
        if raw:
            try:
                self._keypair = Keypair.from_base58_string(raw.strip())
                logger.info("Solana wallet loaded from SOLANA_PRIVATE_KEY env")
            except Exception as e:
                logger.error("Failed to parse SOLANA_PRIVATE_KEY: %s", e)
            return

        keypair_path = os.getenv("SOLANA_KEYPAIR_PATH", "")
        if keypair_path:
            self._load_from_file(keypair_path)

    def _load_from_file(self, path: str) -> None:
        p = Path(path).expanduser()
        if not p.exists():
            logger.warning("Keypair file not found: %s", p)
            return
        try:
            raw = p.read_text().strip()
            if raw.startswith("["):
                data = json.loads(raw)
                self._keypair = Keypair.from_bytes(bytes(data))
            else:
                self._keypair = Keypair.from_base58_string(raw)
            logger.info("Solana wallet loaded from %s", p)
        except Exception as e:
            logger.error("Failed to load keypair from %s: %s", p, e)

    def load_from_vault(self, vault: Any, provider: str = "solana_trading") -> bool:
        creds = vault.get_credentials(provider)
        raw = creds.get("token", "") or creds.get("password", "")
        if not raw:
            logger.warning("No Solana key in vault (provider=%s)", provider)
            return False
        try:
            key_bytes = bytes.fromhex(raw)
            self._keypair = Keypair.from_bytes(key_bytes)
            logger.info("Solana wallet loaded from vault (provider=%s)", provider)
            return True
        except Exception as e:
            logger.error("Failed to load keypair from vault: %s", e)
            return False

    def store_in_vault(self, vault: Any, provider: str = "solana_trading") -> bool:
        if not self._keypair:
            return False
        try:
            vault.store_credentials(
                provider=provider,
                email="solana@trading",
                token=self._keypair.to_bytes().hex(),
            )
            logger.info("Solana wallet stored in vault (provider=%s)", provider)
            return True
        except Exception as e:
            logger.error("Failed to store wallet in vault: %s", e)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._keypair is not None

    @property
    def address(self) -> str:
        if not self._keypair:
            return ""
        return str(self._keypair.pubkey())

    @property
    def pubkey(self) -> Pubkey | None:
        if not self._keypair:
            return None
        return self._keypair.pubkey()

    @property
    def keypair(self) -> Keypair | None:
        return self._keypair

    def sign_and_serialize(self, tx_b64: str) -> str | None:
        if not self._keypair:
            logger.error("Cannot sign: wallet not loaded")
            return None

        try:
            from solders.transaction import VersionedTransaction

            raw = base58.b58decode(tx_b64) if not tx_b64.startswith("A") else __import__("base64").b64decode(tx_b64)
            if len(raw) < 64:
                raw = __import__("base64").b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(raw)
            sig = self._keypair.sign_message(tx.message.serialize())
            signed = VersionedTransaction([sig], tx.message)
            return __import__("base64").b64encode(bytes(signed)).decode()
        except Exception as e:
            logger.error("Failed to sign transaction: %s", e)
            return None

    def generate_new(self) -> str:
        self._keypair = Keypair()
        addr = self.address
        logger.info("Generated new Solana wallet: %s", addr)
        return addr

    def export_private_key_b58(self) -> str:
        if not self._keypair:
            return ""
        return base58.b58encode(bytes(self._keypair)).decode()

    def export_private_key_hex(self) -> str:
        if not self._keypair:
            return ""
        return bytes(self._keypair).hex()
