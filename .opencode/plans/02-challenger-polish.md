# Challenger Polish — Tests + Scheduler + Missing dinámico

## Problemas a resolver

### 1. Sin tests (crítico)
`HypothesisChallenger` no tiene cobertura. Archivo nuevo, 0 tests.

### 2. Scheduler no pasa vulnerability_type
`api/scheduler.py:287` llama `engine.evaluate(vulnerability_type="unknown")`. El challenger da explicaciones genéricas siempre.
**Causa raíz**: `models.Finding` no tiene `vulnerability_type`. El dato se pierde entre la generación de hipótesis y la creación del finding.

### 3. Missing verifications estáticas
Las advertencias de "no se verificó X" son strings hardcodeados que no consideran las señales ya detectadas.

---

## Cambios necesarios

### A. `tests/test_challenger.py` (nuevo)

~10 tests:

| Test | Qué verifica |
|---|---|
| `test_challenge_returns_enriched_data` | `challenge()` devuelve `EnrichedVerdictData` |
| `test_idor_alternatives` | "idor" da 4 explicaciones específicas |
| `test_auth_bypass_alternatives` | "auth_bypass" da 4 específicas |
| `test_unknown_type_fallback` | Tipo desconocido da genéricos |
| `test_uncertainty_penalty_mapping` | "baja"→0.0, "media"→0.05, "alta"→0.12 |
| `test_pick_next_best` | Elige test con mayor info_gain |
| `test_to_dict_serialization` | `to_dict()` produce JSON válido |
| `test_missing_filtered_by_signals` | Si signal `ownership_boundary` presente, no dice "falta ownership" |

### B. `cores/validation/challenger.py` — Missing dinámico

Agregar en `_design_contradiction_tests` y `challenge()`:

```python
def _filter_missing_by_signals(
    self, vt: str, signals: dict[str, Any]
) -> list[str]:
    """Filtrar missing_verifications según señales ya detectadas."""
    all_missing = list(MISSING_VERIFICATIONS.get(vt, []))
    # Mapa: signal → prefijo de missing_verification a remover
    prefix_map = {
        "ownership_boundary": "Ownership",
        "tenant_boundary": "Tenant",
        "public_endpoint": "Recurso público",
        "uuid": "Recurso inexistente",
        "cacheable": "Cache",
    }
    for signal, prefix in prefix_map.items():
        if signals.get(signal):
            all_missing = [m for m in all_missing if not m.startswith(prefix)]
    return all_missing or self._generic_missing(vt)
```

Llamarlo en `challenge()` en vez de `MISSING_VERIFICATIONS.get(vt, ...)`.

### C. `cores/validation/gate.py` — vulnerability_type en Verdict

```python
@dataclass
class Verdict:
    ...
    vulnerability_type: str = "unknown"
```

### D. `cores/validation/loop_engine.py` — pasar vt a Verdict

Al construir el Verdict, agregar:
```python
vulnerability_type=vulnerability_type,
```

### E. `cores/validation/verdict_handler.py` — vt al Finding

```python
finding = models.Finding(
    target_id=target_id,
    endpoint_id=endpoint_id,
    title=title,
    severity=severity,
    description=description,
    vulnerability_type=getattr(verdict, "vulnerability_type", "unknown"),
)
```

### F. `database/models.py` — columnas nuevas

En `Verdict` (después de `next_best_test`):
```python
vulnerability_type = Column(String, nullable=True, default="unknown")
```

En `Finding` (después de `status`):
```python
vulnerability_type = Column(String, nullable=True, default="unknown")
```

### G. `database/db.py` — migración

Agregar:
```python
_migrate_columns(session, "verdicts", [
    ("vulnerability_type", "VARCHAR DEFAULT 'unknown'"),
])
_migrate_columns(session, "findings", [
    ("vulnerability_type", "VARCHAR DEFAULT 'unknown'"),
])
```

### H. `api/scheduler.py` — pasar vt

```python
for f in findings:
    vt = getattr(f, "vulnerability_type", None) or "unknown"
    ...
    engine.evaluate(
        hot_path_id=f"finding_{f.id}",
        endpoint_details=endpoint_details,
        endpoint_signals={},
        auth_baseline=auth_baseline,
        auth_probe=auth_probe,
        vulnerability_type=vt,
    )
```

---

## Archivos modificados (8)

| Archivo | Cambio |
|---|---|
| `tests/test_challenger.py` | **Nuevo** — 8-10 tests |
| `cores/validation/challenger.py` | `_filter_missing_by_signals()` |
| `cores/validation/gate.py` | Campo `vulnerability_type` en Verdict |
| `cores/validation/loop_engine.py` | Pasar vt al Verdict |
| `cores/validation/verdict_handler.py` | Copiar vt al Finding |
| `database/models.py` | Columnas en Verdict + Finding |
| `database/db.py` | Migración de ambas tablas |
| `api/scheduler.py` | Pasar `vulnerability_type` a evaluate() |

## Lo que NO cambia

- `cores/validation/replayer.py` — intacto
- `cores/validation/rules.py` — intacto
- `cores/validation/confidence.py` — intacto (ya tiene uncertainty_penalty)
- `cores/engine/hypothesis/` — intacto
- `cores/orion/` — intacto

## Verificación

1. `pytest tests/test_challenger.py -v` — 8-10 tests verdes
2. `pytest --timeout=60 -x -q` — 393 + nuevos tests pasan
3. `ruff check cores/validation/challenger.py` — clean
4. Ejecutar scheduler con debug — ver "[Challenger: vt=idor, ...]"
