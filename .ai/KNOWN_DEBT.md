# Known Debt — Deuda Técnica Conocida

> Deuda identificada durante el audit arquitectónico. Cada entrada incluye evidencia de su existencia.

## 1. Tres sistemas de salud superpuestos

- **Evidencia**: 
  - `cores/health/engine.py` — SystemHealthEngine
  - `cores/recovery/health_monitor.py` — HealthMonitor
  - `desktop/watchdog.py` — Watchdog
- **Problema**: Los tres sistemas monitorean salud del sistema pero no comparten estado ni se coordinan. Pueden producir estados contradictorios.
- **Impacto**: Alto. Un componente puede estar "saludable" para un sistema y "caído" para otro.
- **Solución propuesta**: Unificar en un solo `UnifiedHealthMonitor`.

## 2. Sin tests para CSRF middleware

- **Evidencia**: `api/middleware/csrf_middleware.py` existe pero no hay tests específicos
- **Problema**: El middleware CSRF no tiene cobertura de tests automatizados
- **Impacto**: Medio. Cambios futuros podrían romper la protección CSRF sin detección.

## 3. Sin tests para scheduler adaptativo

- **Evidencia**: `api/scheduler.py` fue reescrito sin tests específicos
- **Problema**: El scheduler adaptativo (cooldown, priorización) no tiene tests
- **Impacto**: Medio. Cambios en la lógica de priorización no están cubiertos.

## 4. Sin tests para rate limit mejorado

- **Evidencia**: `api/middleware/rate_limit_middleware.py` modificado sin tests
- **Problema**: La resolución de identity por token no tiene tests
- **Impacto**: Bajo. El fallback a IP funciona como antes.

## 5. Sin pre-commit hooks

- **Evidencia**: No hay `.pre-commit-config.yaml`
- **Problema**: No hay validación automática antes de commits
- **Impacto**: Bajo. Las herramientas están configuradas pero no se ejecutan automáticamente.

## 6. DuplicateDetector no conectado al DedupTracker

- **Evidencia**: 
  - `cores/analysis/duplicate_detector.py` usa su propio `_history` in-memory
  - `cores/dedup.py` existe pero no se usa desde análisis
- **Problema**: El detector de duplicados fuzzy no comparte estado con el tracker unificado
- **Impacto**: Bajo. Cada sistema funciona independientemente.

## 7. Dependencias frontend no auditadas

- **Evidencia**: `frontend/package.json` y `node_modules/` extensos
- **Problema**: No se ha auditado seguridad de dependencias npm
- **Impacto**: Potencialmente alto.

## 8. Documentación dispersa

- **Evidencia**: 16 archivos .md en la raíz + 4 en docs/
- **Problema**: Información redundante y desactualizada en múltiples archivos
- **Impacto**: Medio. Dificulta encontrar información precisa.
