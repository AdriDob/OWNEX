# Task Queue — Tareas Pendientes

> Cada tarea DEBE tener evidencia de que no existe ya implementada antes de comenzar.
> Cuando una tarea se completa, se ELIMINA de esta cola.

## CATEYE v3.0.0 STABLE

No hay tareas pendientes para v3.0.0. Todas las verificaciones fueron completadas.

## CATEYE v3.1 — ORION Reasoning Layer

### 1. ✅ Hypothesis Challenger
- **Descripción**: Antes de validar una hipótesis, preguntar "¿qué tendría que ser cierto para que esta vulnerabilidad NO exista?" y diseñar pruebas en consecuencia.
- **Impacto**: Reduce falsos positivos por recursos públicos, caché, stubs.
- **Archivos**: cores/validation/challenger.py (nuevo), gate.py, confidence.py, loop_engine.py, verdict_handler.py, models.py, db.py
- **Estado**: ✅ COMPLETED — 2026-07-09
- **Evidencia**: 393 tests pasan. Ruff clean. El sistema evalúa explicaciones alternativas para 7+ tipos de vulnerabilidad.

### 2. Evidence Graph
- **Descripción**: Guardar evidencia a favor y en contra de cada hipótesis, no solo el confidence score final.
- **Impacto**: Razonamiento interpretable por el humano.
- **Dependencias**: validation/loop_engine.py, validation/gate.py
- **Estado**: Pendiente
- **Criterio de finalización**: El Verdict incluye "evidence_for", "evidence_against", "missing_verifications".

### 3. Adaptive Report Gate
- **Descripción**: Threshold dinámico por tipo de vulnerabilidad (IDOR necesita ownership violation; SSRF necesita interacción externa).
- **Impacto**: Reduce falsos positivos específicos por tipo.
- **Dependencias**: validation/gate.py
- **Estado**: Pendiente
- **Criterio de finalización**: IDOR, SSRF, Auth Bypass tienen distintos criterios de admisión.

### Prioridad Media

### 4. FeedbackLearner pipeline
- **Descripción**: Conectar FeedbackLearner al ConfidenceScorer para que los pesos se ajusten con la experiencia.
- **Impacto**: El sistema mejora con el tiempo.
- **Dependencias**: validation/llm_analyzer.py, validation/confidence.py
- **Estado**: Pendiente
- **Criterio de finalización**: Los insights de FeedbackLearner modifican los pesos del ConfidenceScorer.

### 5. Pending debt (from v3.0)
- ~~Unificar 3 sistemas de salud superpuestos~~ → ✅ HealthCenter unificado en core/health/engine.py
- ~~Agregar persistencia a health snapshots~~ → ✅ Snapshots in-memory (últimos 100)
- ~~Mover API keys del frontend al backend~~ → ✅ SecretsManager en core/secrets/manager.py
- Conectar DuplicateDetector con DedupTracker
- Auditoría de dependencias no utilizadas

## ORION Platform v4.0.0 (COMPLETED)

### ✅ Extension SDK
- **Archivos**: core/extension/manifest.py, registry.py, hooks.py, capabilities.py, settings.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: 63 tests nuevos, Ruff clean. Extensions auto-descubiertas desde extensions/*/manifest.py. Hooks (before/after), capabilities registry, declarative settings.

### ✅ Secrets Manager
- **Archivos**: core/secrets/manager.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: IdentityVault bridge (AES-256-GCM). Env var fallback. Cache in-memory.

### ✅ Health Center
- **Archivos**: core/health/engine.py, checks.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: Unifica 3 sistemas legacy. Checks por categoría (system/background/integration). Status green/yellow/red.

### ✅ Documentation
- **Archivos**: CONFIGURATION_GUIDE.md, EXTENSION_SDK.md, CONNECTOR_GUIDE.md, ARCHITECTURE_DECISIONS.md
- **Estado**: ✅ COMPLETED — 2026-07-10

## ORION Platform v4.1.0 — Financial Layer (COMPLETED)

### ✅ CoinGecko price feed
- **Archivos**: cores/crypto/coingecko.py
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Takenos connector
- **Archivos**: cores/financial/takenos/
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Dashboard unificado
- **Archivos**: cores/financial/dashboard.py
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Integrations status
- **Archivos**: api/routers/financial_truth.py
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Fix Coinbase ATLAS connector (HMAC)
- **Archivos**: apps/atlas/connectors/coinbase/connector.py
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Fix Kraken ATLAS connector (private API)
- **Archivos**: apps/atlas/connectors/kraken/connector.py
- **Estado**: ✅ COMPLETED — 2026-07-10

## Hermes Automation Agent v1 (COMPLETED)

### ✅ Manifest + AppRegistry
- **Archivos**: apps/hermes/manifest.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: App "hermes" registrada con scheduler job hermes_health_check

### ✅ Automation Engine
- **Archivos**: apps/hermes/engine.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: 6 comandos (backup, status, health, logs, doctor, help), safe mode, permission control, action logging

### ✅ CLI wrapper
- **Archivos**: run.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: `python run.py --hermes <command>` funciona

### ✅ Tests
- **Archivos**: tests/test_hermes.py
- **Estado**: ✅ COMPLETED — 2026-07-10
- **Evidencia**: 15 tests pasan, Ruff clean, 0 regresiones

### ✅ User Guide
- **Archivos**: docs/HERMES_GUIDE.md
- **Estado**: ✅ COMPLETED — 2026-07-10

### ✅ Windows launcher
- **Archivos**: scripts/hermes_shortcut.bat, scripts/hermes_silent.vbs
- **Estado**: ✅ COMPLETED — 2026-07-10
