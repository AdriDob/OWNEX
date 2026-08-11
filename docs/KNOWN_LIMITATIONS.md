# Known Limitations — CATEYE Validation Engine

> Documentación honesta de lo que CATEYE **no** hace.
> v4.6.0 STABLE — Julio 2026.

## Validation Engine

CATEYE valida hipótesis comparando respuestas HTTP (baseline vs probe) y aplicando reglas heurísticas + análisis LLM opcional.

**Lo que sí hace:**
- Reproducibilidad (3+ intentos)
- Comparación de respuestas (status, body, headers)
- Confidence scoring ponderado
- Detección de rate limiting, WAF, timeouts
- Generación de reporte borrador

**Lo que NO hace:**

### 1. Refutación activa
El sistema busca **confirmación**, no refutación. No existe una fase que intente explícitamente demostrar que la hipótesis es falsa.

*Ejemplo*: Si un endpoint devuelve 200 sin autenticación, el sistema lo marca como posible auth bypass. No pregunta "¿y si el recurso es público?".

### 2. Explicaciones alternativas
No evalúa escenarios como:
- Recurso público (ambos accesos son legítimos)
- Caché de CDN o proxy
- Datos mock o stub de endpoint
- Respuesta genérica de error
- Comportamiento esperado del negocio

### 3. Verificación de ownership
No diferencia entre:
- "El recurso existe y es mío" (pero probé sin auth → 200)
- "El recurso existe y es de otro" (IDOR real)
- "El recurso no existe" (respuesta genérica 404)

### 4. Verificación de RBAC
No prueba diferentes roles. Solo compara dos contextos (baseline vs probe), no N contextos con N permisos.

### 5. Aprendizaje de falsos positivos
El `FeedbackLearner` existe pero **no está conectado al pipeline principal**. Los pesos del ConfidenceScorer son fijos. El sistema no mejora con la experiencia.

### 6. Razonamiento sobre incertidumbre
El confidence score es numérico. No incluye:
- "Esto NO se verificó"
- "Esto podría tener otra explicación"
- "La siguiente prueba que reduciría más la incertidumbre es X"

### 7. ReportGate adaptativo
El umbral (confidence ≥ 0.6) es fijo para todo tipo de vulnerabilidad. Una IDOR replicable con 0.55 de confianza puede ser válida; un XSS con 0.95 puede ser falso positivo.

## Implicaciones

- **Falsos positivos**: El sistema puede reportar auth bypasses que son realmente recursos públicos.
- **Falsos negativos**: El sistema puede rechazar hipótesis válidas por inconsistencia estadística sin entender la causa.
- **Dependencia humana**: Todo finding debe ser revisado manualmente antes de reportar. CATEYE produce borradores, no conclusiones.

## Próximos pasos (v3.1+)

Ver `.ai/ROADMAP.md` — ORION Reasoning Layer.
