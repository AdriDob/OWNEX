"""Abstract interfaces for OWNEX Core modules.
Every implementation in core/ MUST inherit from these interfaces.
Apps depend on contracts, not concrete implementations.
"""

from cores.interfaces.agent import IAgent
from cores.interfaces.app import IAppPlugin
from cores.interfaces.connector import IConnector
from cores.interfaces.database import IDatabase
from cores.interfaces.event_bus import IEventBus
from cores.interfaces.scheduler import IScheduler
from cores.interfaces.storage import IStorage

__all__ = [
    "IConnector",
    "IEventBus",
    "IScheduler",
    "IDatabase",
    "IAgent",
    "IAppPlugin",
    "IStorage",
]
