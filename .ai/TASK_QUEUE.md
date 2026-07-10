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
- Unificar 3 sistemas de salud superpuestos
- Agregar persistencia a health snapshots
- Conectar DuplicateDetector con DedupTracker
- Mover API keys del frontend al backend
- Auditoría de dependencias no utilizadas
