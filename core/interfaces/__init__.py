"""Abstract interfaces for OWNEX Core modules.
Every implementation in core/ MUST inherit from these interfaces.
Apps depend on contracts, not concrete implementations.
"""

from core.interfaces.agent import IAgent
from core.interfaces.app import IAppPlugin
from core.interfaces.connector import IConnector
from core.interfaces.database import IDatabase
from core.interfaces.event_bus import IEventBus
from core.interfaces.scheduler import IScheduler
from core.interfaces.storage import IStorage

__all__ = [
    "IConnector",
    "IEventBus",
    "IScheduler",
    "IDatabase",
    "IAgent",
    "IAppPlugin",
    "IStorage",
]
