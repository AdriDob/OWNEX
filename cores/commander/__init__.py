from cores.commander.audit import AuditLogger, get_audit_logger, log_action
from cores.commander.context_engine import (
    build_context,
    build_context_async,
    get_context_engine,
    get_prompt_context,
    get_prompt_context_async,
    log_context_to_audit,
)

# `AgentRegistry` y `CapabilityRegistry` se re-exportaban desde
# `agent_registry` / `capability_registry`, que nunca fueron commiteados
# (`git log` vacío): el paquete era **inimportable** y tumbaba
# `test_e2e_copilot.py` (10 tests) y cualquier import de `cores.commander`.
#
# Los consumidores reales (cores/evolution/supervisor.py:49 y los tests)
# usan los submódulos `context_engine` y `audit`, que sí existen. Por eso
# se quita el re-export en vez de inventar las clases: el módulo canónico de
# capacidades es `cores/capabilities/registry.py:61`.
__all__ = [
    "get_audit_logger",
    "log_action",
    "AuditLogger",
    "get_context_engine",
    "build_context",
    "build_context_async",
    "get_prompt_context",
    "get_prompt_context_async",
    "log_context_to_audit",
]
