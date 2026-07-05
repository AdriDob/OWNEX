from __future__ import annotations

import logging
import secrets
import urllib.parse
import urllib.request

from cores.crypto.base import (
    ChainType,
    ConnectionStatus,
    CryptoBalance,
    CryptoConnector,
    CryptoTransaction,
    CryptoWithdrawalInfo,
)
from cores.crypto.evm import EVMConnector
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("catseye.crypto.wallet_connect")

WC_RELAY_URL = "https://bridge.walletconnect.org"
WC_PROTOCOL = "wc"


def _generate_hex(nbytes: int = 32) -> str:
    return secrets.token_hex(nbytes)


class WalletConnectConnector(CryptoConnector):
    def __init__(
        self,
        wallet_id: str,
        uri: str = "",
        chain_name: str = "ethereum",
    ) -> None:
        self._wallet_id = wallet_id
        self._chain_name = chain_name.lower()
        self._status = ConnectionStatus.UNCONFIGURED
        self._uri = uri

        self._session_topic: str = ""
        self._symmetric_key: str = ""
        self._peer_topic: str = ""
        self._address: str = ""
        self._evm: EVMConnector | None = None

        vault = get_identity_vault()
        creds = vault.get_credentials(f"wc_{wallet_id}")
        if creds:
            self._session_topic = creds.get("session_topic", "")
            self._symmetric_key = creds.get("symmetric_key", "")
            self._peer_topic = creds.get("peer_topic", "")
            self._address = creds.get("address", "")
            self._chain_name = creds.get("chain_name", self._chain_name)
            if self._address and self._chain_name:
                self._evm = EVMConnector(
                    wallet_id=f"{wallet_id}_evm",
                    chain_name=self._chain_name,
                    address=self._address,
                )

    @property
    def chain(self) -> ChainType:
        return ChainType.EVM

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def address(self) -> str:
        return self._address

    def generate_pairing_uri(self) -> str:
        self._session_topic = _generate_hex()
        self._symmetric_key = _generate_hex()
        params = urllib.parse.urlencode({
            "relay-protocol": "irn",
            "symKey": self._symmetric_key,
        })
        uri = f"wc:{self._session_topic}@2?{params}"
        self._uri = uri
        self._persist()
        return uri

    def pair(self, uri: str, address: str = "") -> ConnectionStatus:
        try:
            parsed = urllib.parse.urlparse(uri)
            if parsed.scheme != WC_PROTOCOL:
                logger.error("Invalid WC URI scheme: %s", parsed.scheme)
                return ConnectionStatus.ERROR

            path = parsed.path.lstrip("/")
            if "@" in path:
                self._peer_topic, _ = path.split("@", 1)
            else:
                self._peer_topic = path

            qs = urllib.parse.parse_qs(parsed.query)
            sym_key_list = qs.get("symKey", [])
            if sym_key_list:
                self._symmetric_key = sym_key_list[0]

            self._uri = uri
            self._status = ConnectionStatus.CONNECTED

            if address:
                self.set_address(address)

            self._persist()
            logger.info(
                "WalletConnect paired: %s (peer=%s)",
                self._wallet_id, self._peer_topic[:16],
            )
            return self._status
        except Exception as exc:
            logger.error("WalletConnect pair failed: %s", exc)
            self._status = ConnectionStatus.ERROR
            return self._status

    def is_paired(self) -> bool:
        return bool(self._peer_topic or self._address)

    def disconnect(self) -> None:
        self._session_topic = ""
        self._symmetric_key = ""
        self._peer_topic = ""
        self._address = ""
        self._uri = ""
        self._evm = None
        self._status = ConnectionStatus.DISCONNECTED
        vault = get_identity_vault()
        vault.remove_credentials(f"wc_{self._wallet_id}")
        logger.info("WalletConnect disconnected: %s", self._wallet_id)

    def set_address(self, address: str) -> None:
        self._address = address
        if address and self._chain_name:
            self._evm = EVMConnector(
                wallet_id=f"{self._wallet_id}_evm",
                chain_name=self._chain_name,
                address=address,
            )
        self._persist()

    def _persist(self) -> None:
        vault = get_identity_vault()
        vault.store_credentials(
            provider=f"wc_{self._wallet_id}",
            email="",
            token="",
            password="",
            metadata={
                "session_topic": self._session_topic,
                "symmetric_key": self._symmetric_key,
                "peer_topic": self._peer_topic,
                "address": self._address,
                "chain_name": self._chain_name,
                "uri": self._uri,
            },
        )
        vault.update_session_state(
            f"wc_{self._wallet_id}",
            "connected" if self.is_paired() else "disconnected",
        )

    def connect(self) -> ConnectionStatus:
        if not self.is_paired():
            logger.warning("WalletConnect %s: not paired", self._wallet_id)
            self._status = ConnectionStatus.UNCONFIGURED
            return self._status

        try:
            req = urllib.request.Request(
                f"{WC_RELAY_URL}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                self._status = (
                    ConnectionStatus.CONNECTED
                    if resp.status == 200
                    else ConnectionStatus.ERROR
                )
        except Exception as exc:
            logger.warning("WalletConnect relay ping failed: %s", exc)
            self._status = ConnectionStatus.ERROR

        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        if not self._evm:
            return []
        if self._evm.connect() != ConnectionStatus.CONNECTED:
            return []
        return self._evm.get_balance()

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        if not self._evm:
            return []
        if self._evm.connect() != ConnectionStatus.CONNECTED:
            return []
        return self._evm.get_transactions(limit=limit)

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        if not self._evm:
            return []
        if self._evm.connect() != ConnectionStatus.CONNECTED:
            return []
        return self._evm.get_withdrawals(limit=limit)
