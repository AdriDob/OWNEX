"""Platform connectors — public API del paquete.

Este `__init__.py` fue generado vacío por la migración `core/` → `cores/`
(`scripts/migrate_core_to_cores.py`), pero **6 call sites Asumen que el
paquete exporta la API pública**:

    api/routers/control.py:653, 1576, 1588, 1602   → 4 endpoints 500
    cores/daily_tasks.py:305, 514                  → 2 tareas que fallan en silencio

Medido 2026-10-08 con `audit_frontend_contract.py --live`: `GET /api/platforms`
devolvía 500, y la causa era `ImportError: cannot import name
'get_platform_manager' from 'cores.platform_connectors'`.

Lo grave no es el 500: es que `daily_tasks.py` envuelve esos imports en
`try/except: pass`, así que **las recomendaciones de plataformas no
conectadas nunca se generan y nadie se entera**. Un ImportError silenciado es
una capacidad que el sistema cree tener y no tiene.

Se re-exporta en vez de cambiar los 6 call sites: la API pública del paquete
es la que los callers ya asumían, y una sola definición evita que el próximo
mover un símbolo repita el bug.

Ojo al regenerar: si `migrate_core_to_cores.py` vuelve a escribir este
archivo, el re-export se pierde y vuelven los 6 fallos.
"""

from __future__ import annotations

from cores.platform_connectors.universal_connectors import (
    PlatformCategory,
    PlatformConfig,
    PlatformConnectorManager,
    PlatformMetrics,
    PlatformStatus,
    UniversalPlatformConnector,
    get_default_platform_configs,
    get_platform_manager,
)

__all__ = [
    "PlatformCategory",
    "PlatformConfig",
    "PlatformConnectorManager",
    "PlatformMetrics",
    "PlatformStatus",
    "UniversalPlatformConnector",
    "get_default_platform_configs",
    "get_platform_manager",
]
