# Session Checkpoint — Julio 2026

> Este checkpoint permite a cualquier agente retomar exactamente donde terminó el anterior.

## Último Objetivo

Construir el Agent Operating System (AOS): directorio `.ai/` como memoria permanente del proyecto.

## Últimos Cambios

1. **`.ai/AGENT_CHARTER.md`** — Constitución del proyecto con Agent Loop obligatorio y Regla de Oro
2. **`.ai/PROJECT_CONTEXT.md`** — Contexto completo del proyecto
3. **`.ai/ARCHITECTURE.md`** — Arquitectura del sistema con puntos de integración
4. **`.ai/CURRENT_STATE.md`** — Estado verificado (solo con evidencia)
5. **`.ai/ROADMAP.md`** — Roadmap priorizado
6. **`.ai/TASK_QUEUE.md`** — Tareas pendientes con criterios de finalización
7. **`.ai/PRODUCTION_RULES.md`** — Reglas de producción
8. **`.ai/SECURITY_POLICY.md`** — Política de seguridad
9. **`.ai/TESTING_POLICY.md`** — Política de testing
10. **`.ai/CODE_QUALITY.md`** — Estándares de calidad
11. **`.ai/KNOWN_DEBT.md`** — Deuda técnica con evidencia
12. **`.ai/DECISIONS.md`** — Decisiones arquitectónicas
13. **`.ai/DO_NOT_TOUCH.md`** — Componentes estables identificados
14. **`.ai/COMPLETED_FEATURES.json`** — Features con evidencia (solo verificadas)
15. **`.ai/INTEGRATION_REGISTRY.json`** — Mapa de módulos
16. **`opencode.json`** — Configuración de OpenCode con `instructions` y `references`
17. **`.opencode/skills/agent-loop/SKILL.md`** — Skill del Agent Loop para OpenCode
18. **`.cline/rules/core.md`** — Actualizado para referenciar `.ai/`
19. **`README.md`** — Actualizado para referenciar `.ai/`

## Archivos Modificados en esta Sesión

### Nuevos:
- `.ai/` (19 archivos)
- `.opencode/skills/agent-loop/SKILL.md`
- `opencode.json`

### Modificados (hardening de seguridad):
- `cores/license/validator.py` — Ed25519
- `cores/identity_vault.py` — Clave aleatoria + migración
- `cores/vault_crypto.py` — Nuevo módulo compartido
- `cores/auth/token_service.py` — Cifrado AES-256-GCM
- `cores/auth/session.py` — Cifrado AES-256-GCM
- `api/middleware/csrf_middleware.py` — Nuevo middleware CSRF
- `api/middleware/error_handling.py` — Sin fuga de excepciones
- `api/middleware/rate_limit_middleware.py` — Rate limit por user-id
- `api/main.py` — CORS fix
- `cores/authhub/gmail.py` — OAuth2 state token
- `cores/authhub/base.py` — state parameter
- `api/routers/authhub.py` — state en callback
- `cores/audit_log.py` — Nuevo audit log
- `api/routers/auth.py` — Audit events
- `tests/conftest.py` — Dev private key para tests

### Modificados (persistencia, dedup, scheduler):
- `cores/recovery/circuit_breaker.py` — time.time() + persistencia
- `cores/recovery/persistence.py` — learning_state + health_snapshots tables
- `cores/intelligence/reward_learning.py` — Persistencia de ajustes
- `api/scheduler.py` — Adaptativo con cooldown + priorización
- `cores/dedup.py` — Nuevo DedupTracker

### Frontend:
- `frontend/src/stores/settings.ts` — API keys a sessionStorage

## Siguiente Prioridad

**Fase 5: Tests y validación** — Verificar cobertura de tests para todos los cambios recientes, especialmente CSRF middleware y scheduler adaptativo.

## Riesgos

- `test_login_rate_limit` en `tests/test_security.py` falla intermitentemente (preexistente, no relacionado con cambios)
- Los tests no cubren el nuevo CSRF middleware ni el scheduler adaptativo
- Cline tiene configuración separada en `.cline/rules/` que ahora referencia `.ai/`

## Bloqueadores

- Ninguno actualmente

## Decisiones Tomadas en esta Sesión

Ver `DECISIONS.md` para el registro completo. Las más relevantes:

1. Ed25519 > RSA para licencias (claves más pequeñas, sin dependencia openssl)
2. Clave AES aleatoria en archivo > /etc/machine-id (CVE-2)
3. Doble-submit cookie > session store para CSRF
4. Scheduler adaptativo con cooldown > intervalos fijos
5. `.ai/` como fuente de verdad única > documentación dispersa
