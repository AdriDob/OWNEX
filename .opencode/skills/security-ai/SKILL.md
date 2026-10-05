---
name: security-ai
description: Úsala cuando una tarea de seguridad (hacking ético autorizado) necesite IA — revisión de código, priorización de hallazgos, redacción de PoC o reporte. Elige el modelo con evidencia medida, aplica pooling y respeta los límites donde la IA no es autoridad.
compatibility: opencode
metadata:
  audience: developer
  workflow: security
---

# Security AI — modelo correcto, con sus límites conocidos

## Qué modelo y por qué (medido, no opinado)

Dos benchmarks independientes de 2026, sobre corpus distintos:

**TrustedSec** — seguridad ofensiva self-hosted, 800 runs por modelo, 8 challenges:

| Modelo | Pass rate | Turnos | Latencia |
|---|---|---|---|
| **`gemma-4-31b`** | **98.5%** (788/800) | 2.6 | 68 s |
| `qwen3.5:27b` | 97.5% (780/800) | 2.7 | 92 s |
| `devstral-small-2:24b` | 95.6% (765/800) | **1.7** | **23 s** |
| `qwen3-coder` | 86.5% | 3.2 | 19 s |

**Aikido** — descubrimiento sobre 32 CVEs reales, 11.7B tokens:

| Modelo | Recall 1 pasada | Recall pooled (3) |
|---|---|---|
| **`deepseek-v4-pro`** | 17/32 | **28/32** |
| `qwen3.8` | 19/32 | 26/32 |
| `kimi-k3` | 17/32 | 25/32 |

**Conclusión operativa:** el ranking dice `gemma-4-31b` para ejecutar y
`deepseek-v4-pro` para descubrir. **Ninguno de los dos te sirve**, y por eso
el perfil elige distinto:

| Rol | Modelo | Por qué | Provider |
|---|---|---|---|
| **ejecución** | `qwen3.8-27b` | 26/32 pooled en Aikido; 2º detrás de DeepSeek | Groq (FreeLLMAPI) |
| **descubrimiento** | `nemotron-3-super-120b` | 92.0% pass en TrustedSec (736/800) | NVIDIA NIM (free) |
| **triage masivo** | `gpt-oss-20b` | costo/volumen | Groq (FreeLLMAPI) |

> **Medido hoy en tu máquina, no de la tabla:** `gemma-4-31b-it` **no te sirve** —
> Google responde HTTP 500 para los modelos `gemma-4-*`. Por eso **no** puede ser
> el perfil de ejecución aunque gane el benchmark: un 98.5% de un modelo que da
> 500 es un 0% con buena prensa.
>
> `deepseek-v4-pro-0813` es el mejor del ranking de recall **pero no lo podés usar**:
> no tenés provider con key configurada para ese modelo. La key de NVIDIA da la
> familia **Nemotron**.
>
> **Lección que no sabías: el catálogo de 253 modelos NO son 253 modelos disponibles.**
> Sólo responde lo que tiene provider + key + provider sano. Probé 8: 2 funcionaron.
> **Verificá antes de asumir que un modelo del catálogo existe para vos** — y no
> declares en tu reporte el score de un modelo que no podés llamar.

## Cómo usarlo

```python
from cores.ai.security_profile import profile_for, pool_runs

p = profile_for("exploit")       # → qwen3.8-27b (Groq), offensive_execution
req = AIRequest(messages=[...], task_type=TaskType.CODE, model=p.model)
```

## La regla que más importa: **pooling > una pasada buena**

DeepSeek encontró 17 vulns en una pasada y **28 en tres**. Repetir con otra lente recupera
alcance; una sola pasada lo pierde. Cuando la respuesta importe, corré 2-3 y consolidá con
`pool_runs()`.

`pool_runs()` **no** elige el mejor resultado — eso sería cherry-picking. Reporta el
**consenso** y la disidencia. Con `agreement < 0.67` el veredicto es `SPLIT`: **no se
presenta como confirmado**.

## Lo que la IA NO puede hacer aquí

El benchmark es explícito y OWNEX lo respeta:

- **Explotación multi-paso: 0% en todos los modelos probados.** UNION injection, blind
  boolean, enumeración de columnas: nadie mantiene 10+ tool calls encadenados donde cada
  paso depende del anterior. **La IA propone; `ProbeEngine` verifica.**
- **El scaffolding importa más que el modelo.** Un arnés bueno con un modelo mediocre le
  gana a un modelo fuerte sin herramientas. Si esto falla, primero sospechá del arnés.
- **Sabe más de lo que ejecuta.** Modelos describen IDOR correctamente pero no cambian el
  ID en la práctica. Conocimiento ≠ acción.

## IA es complementaria, nunca autoridad

| La IA **no** decide | Quién decide |
|---|---|
| Si un target está in-scope | `cores/scope_enforcement.py` (fail-closed en UNKNOWN) |
| Si algo es una vulnerabilidad confirmada | `ProbeEngine` + validadores + tu ojo |
| Si se envía un reporte | **Vos** — Human Gate |
| Si una payout es real | `RevenueTracker`, sólo desde PAID |

`advisory_only=True` y `require_tool_verification=True` están puestos a propósito en el
perfil: son el recordatorio de que esto es un asistente, no un juez.

## El gap conocido que define el diseño

La IA sabe enumerar clases de ataque pero no las ejecuta en cadena. Por eso OWNEX separa
**razonamiento** (IA, barato y rápido) de **ejecución** (`ProbeEngine`, determinista y
verificable). Una decisión de seguridad que no pase por ejecución verificada no sale de
OWNEX — sin importar qué tan bueno sea el modelo.

## Referencia

- Benchmark TrustedSec: *Benchmarking Self-Hosted LLMs for Offensive Security* (2026-04-14)
- Benchmark Aikido: *We burned 11.7bn tokens to find the best cyber AI model* (2026-08-21)
- Detección web: *Evaluating LLMs for Real-World Web Vulnerability Detection* (arXiv 2606.21397)
  — MiniMax M2.5 open-weightemps de Gemini/Codex; Qwen self-hosted 35%; y un dato que
  confirma el diseño: **scoped prompts ganan sobre open-ended**, que es lo mismo que
  dice pooling — reducir el espacio de búsqueda mejora el resultado.
