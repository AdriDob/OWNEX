"""OWNEX Omega — Departmental Agent Organization."""

# Executive Level
# Build Department
from .architecture import ArchitectureAgent

# Operations Department
from .automation import AutomationAgent
from .coding import CodingAgent
from .debug import DebugAgent

# Knowledge Department
from .documentation import DocumentationAgent

# Strategic Department
from .evolution import EvolutionAgent
from .infrastructure import InfrastructureAgent
from .orchestrator import OrchestratorAgent

# Business Department
from .product import ProductAgent

# Quality Department
from .qa import QAAgent
from .research import ResearchAgent
from .revenue import RevenueAgent
from .security import SecurityAgent

__all__ = [
    # Executive
    "OrchestratorAgent",
    # Build
    "ArchitectureAgent",
    "CodingAgent",
    "DebugAgent",
    # Quality
    "QAAgent",
    "SecurityAgent",
    # Knowledge
    "DocumentationAgent",
    "ResearchAgent",
    # Business
    "ProductAgent",
    "RevenueAgent",
    # Operations
    "AutomationAgent",
    "InfrastructureAgent",
    # Strategic
    "EvolutionAgent",
]
