# Scheduler con Auth Real — Plan

## Problema

El scheduler valida findings con `AuthContext(headers={}, cookies={}, token=None)` — siempre anónimo. El challenger funciona, pero las pruebas de IDOR, auth_bypass y privilege_escalation son inefectivas porque no hay identidades reales.

## Solución

Usar `TargetIdentity` + `SessionResolver` para obtener AuthContext con sesiones reales, en 3 pasos por finding:

```
Finding.target_id → query TargetIdentity(is_baseline, is_active) → SessionResolver.resolve() → AuthContext
```

## Archivos a modificar

### Solo: `api/scheduler.py`

**Dos cambios:**

#### A. Nuevo helper `_resolve_auth_pair()`

```python
async def _resolve_auth_pair(self, session, target_id: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Resuelve baseline y probe AuthContext para un target.

    Retorna (baseline_ctx, probe_ctx).
    Si no hay identidades configuradas, ambos son None (anónimo).
    El resolve() puede hacer login HTTP (login_form) → to_thread().
    """
    from cores.target_auth.session_resolver import get_session_resolver

    resolver = get_session_resolver()

    baseline_id = (
        session.query(models.TargetIdentity.id)
        .filter(
            models.TargetIdentity.target_id == target_id,
            models.TargetIdentity.is_baseline.is_(True),
            models.TargetIdentity.is_active.is_(True),
        )
        .scalar()
    )

    probe_id = (
        session.query(models.TargetIdentity.id)
        .filter(
            models.TargetIdentity.target_id == target_id,
            models.TargetIdentity.is_baseline.is_(False),
            models.TargetIdentity.is_active.is_(True),
        )
        .scalar()
    )

    baseline_ctx = await asyncio.to_thread(resolver.resolve, baseline_id) if baseline_id else None
    probe_ctx = await asyncio.to_thread(resolver.resolve, probe_id) if probe_id else None

    if not baseline_id:
        logger.info("[VALIDATE] Target %d: no baseline identity — anonymous", target_id)
    if not probe_id:
        logger.info("[VALIDATE] Target %d: no probe identity — anonymous", target_id)

    return baseline_ctx, probe_ctx
```

#### B. Modificar `_stage_validate()`

Reemplazar los `AuthContext(headers={}, cookies={}, token=None)` por:

```python
baseline_ctx, probe_ctx = await self._resolve_auth_pair(session, f.target_id)

auth_baseline = AuthContext(
    token=(baseline_ctx or {}).get("token"),
    cookies=(baseline_ctx or {}).get("cookies", {}),
    headers=(baseline_ctx or {}).get("headers", {}),
    label="baseline",
)
auth_probe = AuthContext(
    token=(probe_ctx or {}).get("token"),
    cookies=(probe_ctx or {}).get("cookies", {}),
    headers=(probe_ctx or {}).get("headers", {}),
    label="probe",
)
```

También agregar `from typing import Any` si no existe.

## Lo que NO cambia

- `cores/target_auth/` — intacto (SessionResolver + SessionManager ya funcionan)
- `cores/validation/` — intacto (ya acepta AuthContext)
- `database/models.py` — intacto (TargetIdentity ya existe)
- Tests — sin cambios (no hay tests para scheduler)

## Dependencias

- El usuario debe haber creado TargetIdentity + TargetSession para los targets que quiere validar (via API `/api/targets/{id}/identities` + login).
- Si no hay identidades, el scheduler cae a anónimo (comportamiento actual, con log warning).

## Verificación

1. Ejecutar scheduler con logging DEBUG
2. Ver "[VALIDATE] Target X: resolved baseline=user_a probe=user_b"
3. Si no hay identidades: "[VALIDATE] Target X: no baseline identity — anonymous"
4. `pytest --timeout=60 -q` — 416 tests verdes (sin regresiones)
5. `ruff check api/scheduler.py` — clean
