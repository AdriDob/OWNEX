# CATEYE — Modelo de Monetización

## Filosofía Económica

CATEYE NO es un SaaS comercial. CATEYE es un **SaaS PRIVADO**.

Esto significa:
- **Código abierto (MIT)** — cualquiera puede usarlo, modificarlo, redistribuirlo
- **Sin suscripciones** — no hay planes ni pagos recurrentes
- **100 % local** — no dependés de servidores externos
- **Tus datos son tuyos** — nada sale de tu máquina

El sistema se paga solo generando ingresos por bug bounties.

---

## Cómo CATEYE Genera Ingresos

### 1. Priorización Inteligente (ORION Score)

El algoritmo ORION Score (0.0–1.0) rankea programas por:
- **Potencial de recompensa** (30 %) — bounty máximo del programa
- **Éxito histórico** (20 %) — tasa de aceptación en programas similares
- **Competencia** (15 %) — menos competencia = mejor oportunidad
- **Eficiencia temporal** (15 %) — esfuerzo estimado vs. recompensa
- **Experiencia previa** (10 %) — afinidad con tecnologías del target
- **Diversidad tecnológica** (10 %) — experiencia en el stack del programa

**Impacto:** Enfocás tu tiempo en los programas con mayor retorno esperado. En lugar de trabajar 10 programas al azar, trabajás los 3 con mejor score.

### 2. Expected Value per Hour (EVH)

```
EVH = (max_reward × 0.6 × ORION_Score × 0.7) / max(effort_hours, 0.5)
```

**Impacto:** Sabés exactamente cuánto vale tu hora en cada programa. Si un programa tiene EVH < 20 USD/h, no vale la pena.

### 3. Automatización de Bajo Valor

CATEYE automatiza las tareas que no generan ingreso directo pero consumen tiempo:
- Descubrimiento de programas nuevos
- Reconocimiento (subdominios, endpoints, tecnologías)
- Generación de hipótesis de vulnerabilidades
- Drafts de reportes con IA
- Tracking de pagos y estados

**Impacto:** Recuperás 10–15 h/semana que antes dedicabas a tareas manuales.

### 4. Reward Learning

CATEYE analiza las respuestas de las plataformas (aceptado, rechazado, duplicado, triaged) y aprende patrones:
- "Los IDOR en fintechs tienen 80 % de aceptación"
- "Los reports de XSS stored pagan 2× más que reflected"
- "Bugcrowd es 40 % más lento que HackerOne en triage"

**Impacto:** Mejorás tu tasa de aceptación con el tiempo. Cada rechazo es una lección para el sistema.

### 5. Report Queue Intelligence

Los reportes se priorizan por expected value:
- **Immediate** — > 1000 USD estimados
- **Today** — > 300 USD
- **This Week** — > 100 USD
- **This Month** — < 100 USD o baja probabilidad

**Impacto:** No perdés tiempo en reportes de bajo valor cuando hay oportunidades grandes pendientes.

---

## ROI Esperado

### Costos Operativos

| Concepto | Costo mensual estimado |
|---|---|
| Electricidad (servidor 24/7) | ~15–30 USD |
| API keys OSINT (freemium) | 0 USD (nivel gratuito) |
| Gemini API (IA principal) | 0 USD (free tier) / ~5 USD (uso moderado) |
| OpenRouter / Ollama | 0 USD (local) |
| VPS (opcional, 24/7 cloud) | ~10–20 USD |
| **Total mensual** | **~25–50 USD** |

### Ingresos Potenciales

| Perfil | Ingreso mensual estimado | Con CATEYE (estimado) |
|---|---|---|
| Principiante (< 6 meses) | 200–500 USD | 500–1.500 USD |
| Intermedio (6–18 meses) | 500–2.000 USD | 1.500–5.000 USD |
| Avanzado (> 18 meses) | 2.000–8.000 USD | 5.000–15.000 USD |
| Profesional (full-time) | 5.000–20.000 USD | 10.000–30.000 USD |

**Multiplicador estimado:** 2–3× en ingresos por hora efectiva, gracias a la priorización y automatización.

### Tiempo Recuperado

| Actividad | Sin CATEYE | Con CATEYE |
|---|---|---|
| Descubrimiento de programas | 2 h/sem | Automatizado |
| Reconocimiento | 5 h/sem | Automatizado |
| Drafts de reportes | 3 h/sem | 30 min/sem |
| Tracking de pagos | 1 h/sem | Automatizado |
| **Total** | **11 h/sem** | **0,5 h/sem** |

---

## Estrategia Recomendada

### Fase 1 — Configuración Inicial (Día 1)
1. Instalar CATEYE y conectar API keys
2. Agregar 5–10 programas al Money Radar
3. Revisar ORION Scores
4. Iniciar cacería autónoma

### Fase 2 — Ajuste Fino (Semana 1)
1. Analizar patrones de earnings iniciales
2. Ajustar thresholds de severidad
3. Configurar proveedor IA preferido
4. Conectar cuentas de cobro

### Fase 3 — Operación Estable (Semana 2+)
1. Revisar Money Radar diariamente
2. Validar findings generados automáticamente
3. Revisar drafts de reportes antes de enviar
4. Analizar Reward Learning semanalmente

---

## KPI de Monetización

Monitoreá estos indicadores en el panel económico:

| KPI | Qué mide | Target |
|---|---|---|
| USD/hora | Eficiencia económica | > 100 USD/h |
| Tasa de aceptación | Calidad de reportes | > 60 % |
| Tiempo a pago | Velocidad de plataforma | < 30 días |
| ORION Score promedio | Calidad del portfolio | > 0.6 |
| Findings activos | Carga de trabajo | 10–20 |
| Reportes pendientes | Cuello de botella | < 5 |

---

## Notas Importantes

- **CATEYE es una herramienta, no un reemplazo.** No genera ingresos sin un operador que valide findings y revise reportes.
- **La calidad del reporte importa.** Invertí tiempo en revisar drafts de IA. Un reporte bien escrito se paga mejor.
- **Diversificá plataformas.** No dependas de una sola. Conectá HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack.
- **El aprendizaje es continuo.** Cuanto más usás CATEYE, mejores son sus predicciones y recomendaciones.
- **No hay atajos.** CATEYE optimiza tu tiempo, pero el conocimiento técnico y la habilidad de encontrar vulnerabilidades reales siguen siendo tuyos.
