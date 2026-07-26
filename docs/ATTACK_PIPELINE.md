# Attack Pipeline — De Hipótesis a Evidencia

> v4.6.0 — Julio 2026

## Visión General

El Attack Pipeline cierra el gap más crítico del sistema: **convertir hipótesis de vulnerabilidad en evidencia reproducible**. Antes de esta pipeline, ORION generaba hipótesis pero no ejecutaba pruebas reales contra el target. Ahora el ciclo es completo.

```
Hypothesis
    ↓
AttackPlanner.plan()
    ↓
TestPlan (baseline + N attack steps)
    ↓
ProbeEngine.execute_plan()
    ↓
Response Comparison
    ↓
Detection + Confidence Scoring
    ↓
Evidence Composer
    ↓
Finding Promotion
    ↓
Report Quality Gate
    ↓
Revenue Pipeline
```

---

## 1. AttackPlanner

**Archivo**: `core/offensive/attack_planner.py`

Convierte una `Hypothesis` en un `TestPlan` con `AttackStep` tipados. Cada tipo de vulnerabilidad tiene su propio planner que genera payloads específicos.

### TestPlan

```python
@dataclass
class TestPlan:
    hypothesis_id: str
    vulnerability_type: str   # "idor", "ssrf", "xss", "sqli", "auth_bypass"
    target: str               # Base URL del target
    endpoint_path: str
    steps: list[AttackStep]   # Baseline + N test steps
    payloads: dict[str, list[str]]  # Payloads por key
    detection_strategy: str   # "status_diff", "body_diff", "timing", etc.
    auth_required: bool
```

### AttackStep

```python
@dataclass
class AttackStep:
    purpose: str       # "baseline", "test", "verify", "enumerate"
    method: str        # GET, POST, PUT, DELETE
    path: str          # Ruta del endpoint
    headers: dict      # Headers adicionales
    params: dict       # Parámetros de query
    body: Any          # Cuerpo de la request
    payload_key: str | None  # Key del payload usado
```

### Planners por vulnerabilidad

| Vuln Type | Steps | Payloads | Estrategia de detección |
|---|---|---|---|
| **IDOR** | baseline + 4 | IDs alternativos (999999, 0, -1, admin) | status_diff, body_diff |
| **SSRF** | baseline + 5 | localhost, 169.254.169.254, file://, 0.0.0.0 | timing, error_pattern |
| **XSS** | baseline + 5 | img onerror, script, svg onload, `">` breakout | content_match |
| **SQLi** | baseline + 5 | OR/AND, sleep, error-based, UNION | error_pattern, timing |
| **Auth Bypass** | baseline + 7 | X-Forwarded-For, Cookie, Authorization alternative | status_diff |
| **Generic** | baseline + 3 | test_value, empty, null | behavioral_diff |

### Uso

```python
from core.offensive.attack_planner import AttackPlanner
from core.offensive.models import Hypothesis

hyp = Hypothesis(
    vulnerability_type="idor",
    endpoint="/api/users/{id}",
    method="GET",
    parameters_of_interest=["id"],
)

planner = AttackPlanner()
plan = planner.plan(hyp)
# → TestPlan con 5 AttackSteps
```

---

## 2. ProbeEngine.execute_plan()

**Archivo**: `core/offensive/probe/engine.py`

Ejecuta un `TestPlan` completo contra el target real y retorna un `ProbeResult` con evidencia.

### Pipeline interno

```
1. Abrir cliente HTTP (httpx.Client, verify=False)
2. Para cada AttackStep en plan.steps:
   a. Convertir step → ProbeRequest (URL, method, params, headers, body)
   b. Enviar request HTTP
   c. Capturar ProbeResponse (status, headers, body, timing)
   d. Almacenar como ProbeEvidence
3. Ejecutar detección multi-payload:
   a. Usar baseline como referencia
   b. Comparar cada test response contra baseline
   c. Elegir detección con mayor confianza
4. Si confirmed:
   a. Enviar verify request (mismos params que baseline)
   b. Almacenar como evidencia adicional
5. Retornar ProbeResult
```

### Detección

Cada tipo de vulnerabilidad tiene su propio detector:

| Vuln Type | Detector | Indicadores |
|---|---|---|
| IDOR | `_detect_idor` | Status 200 vs 403/401, body size difference |
| SSRF | `_detect_ssrf` | Timing > 2x baseline, error patterns, body content |
| XSS | `_detect_xss` | Payload reflected in response body |
| SQLi | `_detect_sqli` | SQL error messages, timing > 5s |
| Auth Bypass | `_detect_auth_bypass` | Status 200 vs 401/403 |

### Confidence Scoring

El confidence score (0.0-1.0) se calcula como:

| Factor | Peso | Descripción |
|---|---|---|
| Status difference | 0.3 | Código HTTP diferente al baseline |
| Body size delta | 0.2 | > 20% de diferencia en tamaño |
| Timing anomaly | 0.15 | > 2x el tiempo del baseline |
| Error pattern match | 0.2 | Patrón de error específico de la vuln |
| Content match | 0.15 | Payload reflejado en respuesta |

### Uso

```python
from core.offensive.probe import ProbeEngine

engine = ProbeEngine()
result = engine.execute_plan(
    plan=plan,
    auth_headers={"Authorization": "Bearer eyJ..."},
    extra_headers={"X-Custom": "value"},
)

if result.confirmed:
    print(f"Confirmed {result.vulnerability_type} at {result.endpoint}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.detection_method}")
    print(f"Evidence: {len(result.evidence)} items")
```

---

## 3. Evidence Composer

**Archivo**: `core/evidence/composer.py`

Toma el resultado del probe y genera un bundle de evidencia profesional.

### Contenido del EvidenceBundle

- **PoC**: Descripción narrativa de la vulnerabilidad
- **Requests HTTP**: Request completa con headers y body
- **Responses HTTP**: Response completa con status, headers, body
- **Curl command**: Comando curl reproducible
- **Python exploit**: Script Python ejecutable
- **Timeline**: Línea de tiempo de la reproducción
- **CVSS Score**: Puntaje CVSS v3.1 estimado
- **CWE Mapping**: Mapeo a Common Weakness Enumeration
- **CAPEC Mapping**: Mapeo a Common Attack Pattern Enumeration
- **OWASP Category**: Categoría OWASP Top 10
- **MITRE ATT&CK**: Técnicas MITRE relevantes
- **Report Readiness Score**: Score de 0-100 indicando qué tan listo está para reporte

---

## 4. API Endpoints

### POST /api/offensive/probe

Ejecuta AttackPlanner + ProbeEngine.execute_plan() en un solo paso.

### POST /api/offensive/promote

Ejecuta probe + EvidenceComposer + Finding creation + Knowledge Graph recording en un solo paso.

### POST /api/offensive/plan

Solo genera el plan sin ejecutarlo (útil para revisión previa).

### POST /api/offensive/analyze

Analiza endpoint con todos los reasoners, genera hipótesis priorizadas.

---

## 5. Flujo completo recomendado

```bash
# 1. Analizar endpoint
curl -X POST http://localhost:8000/api/offensive/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/api/users/{id}", "method": "GET", "host": "https://target.com"}'

# 2. Ver el plan antes de ejecutar
curl -X POST "http://localhost:8000/api/offensive/plan?path=/api/users/{id}&vulnerability_type=idor"

# 3. Ejecutar probe multi-payload
curl -X POST http://localhost:8000/api/offensive/probe \
  -H "Content-Type: application/json" \
  -d '{
    "vulnerability_type": "idor",
    "endpoint": "/api/users/{id}",
    "method": "GET",
    "host": "https://target.com",
    "parameters_of_interest": ["id"],
    "auth_token": "eyJ..."
  }'

# 4. Si se confirma, promover a finding
curl -X POST http://localhost:8000/api/offensive/promote \
  -H "Content-Type: application/json" \
  -d '{
    "vulnerability_type": "idor",
    "endpoint": "/api/users/{id}",
    "host": "https://target.com",
    "parameters_of_interest": ["id"],
    "summary": "IDOR in /api/users/{id} - user ID enumeration"
  }'
```

---

## 6. Integración con el Scheduler

El Attack Pipeline se integra con el scheduler autónomo:

```
Ciclo del scheduler:
  DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT

Attack Pipeline (bajo demanda o desde VALIDATE):
  Hypothesis → AttackPlanner → ProbeEngine → Evidence
```

Cuando el scheduler ejecuta la etapa VALIDATE, ahora puede:
1. Tomar hipótesis de alta prioridad
2. Generar AttackPlan
3. Ejecutar probe
4. Si se confirma → crear finding + evidencia automáticamente

---

## 7. Learning Loop

Cada resultado del pipeline alimenta el aprendizaje:

```
ProbeResult
    ↓
record_outcome(vuln_type, hypothesis_id, confirmed)
    ↓
Reasoner stats actualizadas (hits, misses, accuracy)
    ↓
RewardLearner ajusta pesos por tipo de vulnerabilidad
    ↓
Future hypotheses priorizan tipos con mejor ratio de confirmación
```

Endpoint: `POST /api/offensive/reasoners/{vuln_type}/outcome?hypothesis_id=...&confirmed=true`
