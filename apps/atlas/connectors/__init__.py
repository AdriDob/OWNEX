"""ATLAS Connectors — one directory per platform.

Each connector is self-contained and calls only REST APIs.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.atlas.connectors.base import AtlasConnector

logger = logging.getLogger("orion.atlas.connectors.registry")

# Registry of available connectors
_CONNECTOR_CLASSES: dict[str, type[AtlasConnector]] = {}


def register_connector(cls: type[AtlasConnector]) -> type[AtlasConnector]:
    """Register a connector class by its connector_id."""
    _CONNECTOR_CLASSES[cls.connector_id] = cls
    logger.debug("Registered connector: %s", cls.connector_id)
    return cls


def get_connector_ids() -> list[str]:
    return list(_CONNECTOR_CLASSES.keys())


def create_connector(connector_id: str) -> AtlasConnector | None:
    """Instantiate a connector by its ID."""
    cls = _CONNECTOR_CLASSES.get(connector_id)
    if cls is None:
        return None
    return cls()


def init_all_connectors() -> dict[str, AtlasConnector]:
    """Create and connect all registered connectors."""
    instances: dict[str, AtlasConnector] = {}
    for cid, cls in _CONNECTOR_CLASSES.items():
        try:
            inst = cls()
            connected = False
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import asyncio as _a

                    connected = _a.run_coroutine_threadsafe(inst.connect(), loop).result(5)
                else:
                    connected = asyncio.run(inst.connect())
            except Exception:
                connected = False
            if connected:
                instances[cid] = inst
                logger.info("Connected: %s", cid)
            else:
                logger.warning("Failed to connect: %s", cid)
        except Exception as exc:
            logger.error("Failed to init connector %s: %s", cid, exc)
    return instances


# Auto-register built-in connectors — noqa: E402 (intentional after functions)
from apps.atlas.connectors.binance.connector import BinanceConnector  # noqa: E402
from apps.atlas.connectors.coinbase.connector import CoinbaseConnector  # noqa: E402
from apps.atlas.connectors.csv.connector import CSVImporterConnector  # noqa: E402
from apps.atlas.connectors.kraken.connector import KrakenConnector  # noqa: E402
from apps.atlas.connectors.yahoo.connector import YahooConnector  # noqa: E402

register_connector(BinanceConnector)
register_connector(CoinbaseConnector)
register_connector(KrakenConnector)
register_connector(YahooConnector)
register_connector(CSVImporterConnector)

# Optional connectors (require external running instances)
try:
    from apps.atlas.connectors.freqtrade.connector import FreqtradeConnector  # noqa: E402

    register_connector(FreqtradeConnector)
except ImportError:
    pass

try:
    from apps.atlas.connectors.hummingbot.connector import HummingbotConnector  # noqa: E402

    register_connector(HummingbotConnector)
except ImportError:
    pass
