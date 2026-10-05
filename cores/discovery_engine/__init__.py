"""Universal Opportunity Discovery Engine

Explora el internet en busca de plataformas, programas, recompensas,
concursos y oportunidades públicas compatibles con la filosofía de OWNEX.

Historial (2026-10-01): este `__init__.py` re-exportaba seis submódulos —
`analyzer`, `classifier`, `deduplicator`, `knowledge`, `scheduler`, `scorer` —
que **nunca fueron commiteados** (`git log` vacío para los seis). Eso dejaba
el paquete inimportable (`ModuleNotFoundError: cores.discovery_engine.analyzer`)
y a `discovery.py` inalcanzable a propósito.

El módulo real es `discovery.py`, con `DiscoveryConfig` y `DiscoveryEngine`.
Se exporta sólo eso: preferimos un paquete que funciona sobre uno que promete
capacidades inexistentes. Si los seis módulos hacen falta, deben escribirse.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .discovery import DiscoveryConfig, DiscoveryEngine

__all__ = ["DiscoveryEngine", "DiscoveryConfig"]
