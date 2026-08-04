"""ODYSSEY Connectors — one directory per platform.

Each connector is self-contained and calls only REST APIs.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.odyssey.connectors.base import OdysseyConnector

logger = logging.getLogger("orion.odyssey.connectors.registry")

_CONNECTOR_CLASSES: dict[str, type[OdysseyConnector]] = {}


def register_connector(cls: type[OdysseyConnector]) -> type[OdysseyConnector]:
    _CONNECTOR_CLASSES[cls.connector_id] = cls
    logger.debug("Registered connector: %s", cls.connector_id)
    return cls


def get_connector_ids() -> list[str]:
    return list(_CONNECTOR_CLASSES.keys())


def create_connector(connector_id: str) -> OdysseyConnector | None:
    cls = _CONNECTOR_CLASSES.get(connector_id)
    if cls is None:
        return None
    return cls()


def init_all_connectors() -> dict[str, OdysseyConnector]:
    instances: dict[str, OdysseyConnector] = {}
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


from apps.odyssey.connectors.betfair.connector import BetfairConnector  # noqa: E402
from apps.odyssey.connectors.csv.connector import CSVImporterConnector  # noqa: E402
from apps.odyssey.connectors.polymarket.connector import PolymarketConnector  # noqa: E402
from apps.odyssey.connectors.the_odds_api.connector import OddsHarvesterConnector  # noqa: E402

register_connector(BetfairConnector)
register_connector(CSVImporterConnector)
register_connector(PolymarketConnector)
register_connector(OddsHarvesterConnector)
