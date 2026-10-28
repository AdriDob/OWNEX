# OWNEX — Product One Page

> **Autoridad de estado:** verificada contra el código el 2026-10-04.
> **Regla de este documento:** si OWNEX no se puede explicar en una página,
> **no se agrega arquitectura** (stop adding architecture).

---

## WHO

Un solo operador (el dueño). Sin equipo, sin multi-tenant, sin clientes.
Lo que se opera, se opera **para una sola persona**.

## PROBLEM

El trabajo técnico pagable está fragmentado en hundreds de plataformas, con
requisitos de entrada distintos, pagos distintos y ventanas de cobro distintas.
Descubrir, evaluar, preparar, entregar y cobrar es trabajo manual repetitivo,
y el error más caro no es no cobrar: es **cobrar mal** — por ejemplo, aceptar un bounty que no
es elegible, con evidencia que no sostiene el reporte, o tomando una acción
externa bajo tu nombre sin tu aprobación.

## PROMISE

Convertir **objetivos y oportunidades** en **trabajo verificado** y, cuando la
plataforma lo permite, en **ingreso real registrado** — con el máximo de
automatización útil y la mínima intervención humana necesaria.

## PRIMARY JOB

**¿Qué trabajo técnico puedo entregar, es elegible, y lo cobro?**

Todo lo demás en el sistema existe para responder esa pregunta con evidencia.

## INPUT

1. **Fuentes** — 178 `SourceDefinition` registradas (bug bounty, dev bounty,
   AI-eval, open source, research, grants). Entran como **dato + adapter
   genérico**, nunca como un módulo por plataforma.
2. **Objetivo del operador** — capacidad, horas disponibles, restricciones de
   país y cobro.
3. **Un target autorizado** (sólo para el carril security).

## CORE LOOP

```
DESCUBRIR  → fuente produce oportunidad (dato, no motor)
EVALUAR    → elegibilidad + prioridad técnica + prioridad económica (separadas)
PREPARAR   → requisitos, alcance, evidencia necesaria, likelihood de pago
EJECUTAR   → todo lo técnicamente posible, dentro de PolicyEngine
VERIFICAR   → evidencia reproducible → veredicto
HUMAN GATE → acción consequential: siempre humana
DELIVER    → envío, PR, reporte, entrega
REGISTRAR  → estado de aceptación y de cobro
APRENDER   → outcome real → calibración
```

**Nada de esto es un producto por separado.** Security, dev bounty, AI-eval,
open source, research y web3 son **dominios y source types que alimentan el
mismo loop**.

## AUTOMATION

Automatizado por defecto: descubrimiento, evaluación de elegibilidad, ranking,
preparación, ejecución técnica, recolección de evidencia, borrador de reporte,
registro de resultado.

**El estado de autonomía es una política de ejecución**, no un dominio:

```
MANUAL · ASSISTED · AUTO_REVERSIBLE · HUMAN_APPROVAL
```

## HUMAN GATES

Irreversibles o bajo tu nombre — **nunca** automatizados:

- envío externo (bug report, PR, submission)
- aceptación de términos / acceso a credenciales
- pago, transferencia, movimiento de capital
- acción destructiva
- ampliación de scope sobre un target
- publicación

El sistema **prepara** estas acciones por completo y se detiene ahí.

## OUTPUT

- **Reportes y PRs con evidencia reproducible**
- **WorkItems con minutos humanos** (el denominador de `NET $/H`)
- **Ledger**: `EXPECTED → PENDING → REALIZED`. **`REALIZED` sólo con evidencia de pago.**
- **Capital**: liquidez, runway, asignación

## SUCCESS

| Métrica | Regla |
|---|---|
| `PAID` | **única** cifra que cuenta como caja. Sin pago probado, `PAID = 0` y el resto es `UNKNOWN` |
| `P(CASH)` | `UNKNOWN` mientras no haya outcomes reales. **Nunca** inventado |
| `NET $/H` | `UNKNOWN` sin denominador de horas humanas. Sin `WorkItem` no hay métrica |
| Detección | hipótesis **confirmadas con evidencia**, no conteo de hipótesis |
| Autonomía | % de pasos del loop sin intervención, por ciclo |
| Coherencia | un concepto = un módulo canónico. Duplicado = deuda, no capacidad |

## NON-GOALS

Explícitamente fuera del producto:

- **No** es un marketplace (no competimos por precio con freelancers)
- **No** es un producto de seguridad — security es un *dominio* del loop
- **No** es un framework de agentes: la IA es mecanismo, no producto
- **No** es un producto cloud ni multi-tenant
- **No** crece trading durante la consolidación
- **No** claim "100% local": es **local-first** con integraciones externas
  opcionales, y eso se dice con esas palabras

---

---

## OWNEX 1.0 — criterio de salida (fijado 2026-10-04, decisión del owner)

> **OWNEX 1.0 se considera operativo cuando completa al menos una ejecución real
> de extremo a punta, con resultado económico registrado, atravesando
> correctamente sus Human Gates y sin falsificar ni inferir el resultado.**

```
PAID = 0      →  NO es 1.0
PAID >= 1     →  OWNEX 1.0
```

**Un pago. No miles. No $25k.** El primer evento económico distingue *software que
creemos que puede ganar dinero* de *software que ganó dinero*. `EXPECTED` y
`PROJECTED` **no** cuentan: sólo un `REALIZED` con evidencia.

### Los tres niveles, para no confundirlos

| Nivel | Criterio | Naturaleza |
|---|---|---|
| **1 · funciona** | 1 ejecución real pagada | hito |
| **2 · produce** | ingresos repetibles | calibración |
| **3 · escala** | $25k/mes → $100k/mes | negocio |

Bloquear el 1.0 hasta $25k/mes es un error de criterio: son cosas distintas.

### Congelamiento de expansión vigente

Desde 2026-10-04 **no se agrega** un subsistema, motor, agente, framework de
agentes, router, pipeline ni arquitectura nueva. **Excepciones, sólo:**

1. P0/P1 de seguridad o corrección de datos.
2. Desbloqueo directo del loop económico.
3. Duplicación crítica con dos canónicos vivos.

**Medición que sostiene la regla:** 26 de los 27 subsistemas de un plan de
9 etapas propuesto ya existen escritos en `cores/`. Un plan que no chequea el
código antes de proponer construcción, duplica.

### El filtro, para cada cambio

```
¿Acerca a B (loop real) o C (coherencia)?
   NO → ¿Corrige P0/P1, overlap, seguridad, evidencia o deuda crítica?
          NO → NO SE HACE AHORA
```

### Estado medido del bloqueo

| Dato | Valor |
|---|---|
| `GITHUB_TOKEN` en `~/.config/ownex/opportunity.env` | **pendiente (vacío)** |
| `targets` | 722 |
| `pipeline_runs` | 1.621 |
| `endpoints` | 9.922 |
| `missions` | 6 |
| `submission_records` | **0** |
| `revenue_events` | **0** |

El motor de seguridad **corrrió y produjo datos**. El loop económico **nunca se
ejecutó ni una vez**, y se detuvo en el Human Gate — que es exactamente el diseño
correcto. Lo que falta no es capacidad: es la credencial y un rail de cobro.

## LA FRONTERA QUE NO SE CRUZA

> **AI interpreta. La realidad confirma.**

La IA puede generar hipótesis, planear, correlacionar, clasificar y redactar.
**No** puede fabricar evidencia, confirmar un hallazgo por sí sola, autorizar una
acción externa, declarar caja, ni saltear el `PolicyEngine` o el Human Gate.

`Evidence = hechos` · `Finding = interpretación`. Un finding **no existe** sin
su `EvidenceBundle`. Cambiar severidad o título **no** destruye la evidencia
histórica.

---

## EL CICLO, EN CÓDIGO

Los 5 ciclos registrados en `cores/cycles/registry.py`, con su prioridad real:

| Ciclo | Prioridad | Categoría | Qué es |
|---|---:|---|---|
| **security** | 10 | `offensive` | Bug bounty, investigación de vulnerabilidades, pipeline Rastro |
| **forge** | 8 | `development` | Dev bounties, contribuciones OSS, recompensas de code review |
| **pulse** | 6 | `ai_work` | AI training, data annotation, microtask platforms |
| **vault** | 7 | `finance` | Portfolio, cripto, DeFi, análisis financiero |
| **atlas** | 5 | `intelligence` | Research, OSINT, trend analysis, CVE tracking |

Las plataformas de un ciclo son **candidatas de descubrimiento**, noognito
integraciones: pasan por el gate de admisión de fuentes igual que cualquier otra.
`outlier` y `mindrift` figuran en la config de `pulse` pero aparecen 18× y 19×
respectivamente en las exclusiones duras — la config propone, el gate dispone.

## DÓNDE ESTÁ LA DEUDA, EN UNA LÍNEA

`cores/` tiene **194 módulos** para 5 ciclos. El mapa canónico de conceptos
está en [`PRODUCT_MAP.md`](PRODUCT_MAP.md); la lista de solapamientos
verificados, en `.ai/KNOWN_DEBT.md`.

> **Owner: 194 módulos y 126 ficheros en `.ai/`. Ninguno de los dos números es
> una capacidad. Son coste de explicación.**