# AUDITORÍA DEL REPOSITORIO — PRIMER INGRESO REAL VERIFICADO

Fecha: 2026-10-29
Realizado por: OpenCode (inspección manual + tests + ruff + import checks)

## 1. RESUMEN EJECUTIVO

| Pregunta | Resultado |
|---|---|
| ¿Existe un adaptador funcional para AgentHansa? | **No.** Solo existe un bloque corrupto en `core/opportunity/adapters/forge/__init__.py` que termina en `from .algora import AgnthansaAdapter` y `__all__` duplicado. |
| ¿Existe un adaptador funcional para Agent Bounties? | **No.** El repo no implementa `agentbounties.app` como adaptador, solo registra métricas on-chain en tests. |
| ¿El repo tiene un flujo de descubrimiento → cobro verificable? | **No.** Tiene adaptadores de otros pilotos (Algora, Opire, Superteam) y routes para ejecución de tareas, pero no una cadena end-to-end con registro financiero. |
| ¿El repo tiene un estado financiero con transiciones explícitas? | **Parcial.** `core/opportunity/scoring.py`, `core/opportunity/models.py` y `cores/financial/*` existen, pero no una máquina de estados unificada para "detección → cobro → retiro". |
| ¿El repo tiene tests que verifican la cadena real? | No. Los tests existentes son mocks de lógica (HTTP, ejecución) y no verifican un primer pago real. |
| ¿El repo tiene seguridad (aprobaciones humanas) implementada? | Parcial. `core/execution/optimizers/approval.py` existe, pero la cadena de "necesidad humana → aprobación → ejecución → verificación" no está documentada ni probada. |

## 2. ESTADO DE LOS COMPONENTES CLAVE

| Componente | Estado comprobado | Evidencia | Bloqueo | Próxima acción mínima |
|---|---|---|---|---|
| `core/opportunity/adapters` | Solo `forge`, `forge_legacy`, `opire`, `superteam`, `algora` (función), `issuehunt`, `freelancer`, `opencollective`, `opyre`, `pulse`, `security`, `security_bounty`, `vault`, `atlas`, `base` | `ls core/opportunity/adapters/` | No hay `agenthansa.py` ni `agentbounties_adapter.py` | Crear `agenthansa.py` (solo si hay credenciales reales y API verificada) o registrar bloqueo. |
| `core/opportunity/engine.py` | Motor de motores (WorkCycle/Passage) existente. | `core/opportunity/engine.py` (520 líneas) | El motor no gestiona estados de "pago verificado → retiro". | Reutilizar `engine` para registrar la cadena de validación, no reimplementar. |
| `core/opportunity/scoring.py` | Scoring de oportunidades. | `core/opportunity/scoring.py` | No expone `pago_recibido`, `retirado`, `verificado`. | Agregar en un flujo existente sin duplicar (ver `core/financial`). |
| `core/financial/*` | Sistema de pago, payout, retiro. | `core/financial/` (7 archivos) | El retiro no verifica en la red; depende de third-party. | Usar el método oficial de verificación (hash TX en la red correspondiente). |
| `api/routers/opportunity.py` | Routers de descubrimiento y ejecución. | `api/routers/opportunity.py` | No expone "registro de pago verificado". | Agregar endpoint de "verificar pago" con hash TX y red. |
| `api/routers/control.py` | Gateway de controles. | `api/routers/control.py` | No implementa "human gate" para pago. | Usar `core/execution/optimizers/approval.py` como punto de aprobación. |
| `core/sandbox_mode.py` | Modo sandbox. | `core/sandbox_mode.py` | No aplica a la cadena de pago; requiere permisos. | No lo usa para pago; pero define "modo offline" para pruebas. |
| Tests | 1367 detectados; `test_opportunity_engine_comprehensive.py` y `test_opportunity_core.py` pasan (52 tests). | `pytest tests/test_opportunity_engine_comprehensive.py tests/test_opportunity_core.py -q` → 52 passed | No hay test de cadena de pago. | Escribir test de "cadena simulada con estado correcto". |
| Ruff | OK. | `ruff check .` | Advertencias en `work/ownex-economy-active-earn/` y `api/routers/bank_payout.py` | No afectan a la misión; no corregir sin queja. |
| JSON Schema / docs | No hay especificación de "cadena de pago" para el repo actual. | N/A | No hay guía de implementación. | Documentar en `.ai/` o en `docs/` si se implementa. |

## 3. POSIBILIDAD DE FUENTES VIABLES

| Fuente | Viabilidad | Evidencia | Bloqueo |
|---|---|---|---|
| **AgentHansa** | **NO verificable.** Solo "223.635 requests/día" y "US$50.669 pagados" publicados. Sin API verificada, sin credenciales, sin endpoint documentado en el repo. | `awesome-agent-venues` GitHub (2026-10-05). | Falta API key, registro, verificación de elegibilidad argentina, y prueba de ejecución. |
| **Agent Bounties** | **MEJOR para monitoreo.** 46 events on-chain verificados (dev.to, oct 6 2026). Payout on-chain verificable, no garantizado. | `dev.to` artículos y `agentbounties.app`. | Waitlist/state desconocido; requiere wallet y conexión a red. |
| **Algora** | **Segunda candidata.** $143K distribuidos (Ziverge), bounties $50-2.500. | gigs.sh, gigs.sh (2026-05-18). | Política de automatización no clara, pagos desde Argentina no verificados. |
| **MCPize** | No como fuente activa. "Fee 20%", "payout mínimo $100", "Stripe Connect mensual". | mcpize.com/blog (2026-10). | Requiere crear Actor, verifier, y obtener subscritos. |
| **Apify** | No como fuente activa. "Modelo pay-per-event desde 1 oct 2026. Sin suscripción." | Apify Documentation. | Requiere publicar Actor, obtener trafico, y cobrar. |
| **MuleRun** | "Revenue share ~100%", "hosting incluido", "billing incluido". | blog.mulerun.com (2025-12). | No es un bounty; es un marketplace de agentes. |
| **AgenticMarket** | "80-90% revenue share", "setup 10 min". | agenticmarket.dev | No hay prueba de demanda o pagos recibidos. |
| **BNTY** | Waitlist. 12 payouts verificados ($450-2500). | bnty.market | No está abierto. |

## 4. DECISIÓN DE FUENTE

- **Primera fuente viable** (en el repo): **Agent Bounties** como monitoreo, no como fuente primaria de cobro.
- **Segunda fuente** (si AgentBounties no avanza): **AgentHansa** con adaptador simulado (solo si hay credenciales). **No implementar** sin API documentada.
- **No implementar** MCPize, Apify, MuleRun, AgenticMarket, BNTY como fuente activa hasta demostrar demanda y pagos verificados.

## 5. PLAN DE PRUEBAS

| Fase | Objetivo | Método | Resultado esperado |
|---|---|---|---|
| 1 | Auditoría | `git status`, `ruff check`, `pytest tests/test_opportunity_engine_comprehensive.py` | 52 passed, ruff OK |
| 2 | Verificar AgentHansa | `grep -rn "agenthansa"` repo | No existe adaptador. |
| 3 | Verificar Agent Bounties | `grep -rn "agentbounties" tests/` | Métricas on-chain existentes. |
| 4 | Verificar cadena financiera | `cat core/opportunity/models.py`, `core/financial/` | Estados existentes. |
| 5 | Preparar flujo mínimo | Crear `agentbounties_adapter.py` estubado con puertas humanas. | Componente listo para usar. |
| 6 | Tests | `pytest tests/test_agentbounties_adapter.py` | Tests de simulación correctos. |
| 7 | Register | `ruff check`, `pytest` | Verificación. |
| 8 | Reporte | Documentar estado y bloqueos | Entrega completa |

## 6. REGISTRO FINANCIERO (estados canónicos)

| Estado | Método de verificación | Regla |
|---|---|---|
| Oportunidad detectada | `engine.register()` | No se marca PAID hasta que la plataforma acepte. |
| Elegibilidad verificada | Verificación de requisitos (API, credencial, identidad) | No se marca PAID hasta que la verificación es exitosa. |
| Trabajo iniciado | `engine.start()` | No se marca PAID hasta que se completa. |
| Trabajo entregado | `engine.complete()` con evidencia | No se marca PAID hasta que la evidencia es verificable. |
| Aceptación | `engine.accept()` | No se marca PAID hasta que la plataforma confirma. |
| Recompensa devengada | `engine.devengar(reward)` | No se marca PAID hasta que la recompensa es real. |
| Pago recibido | `engine.recibir(payment_tx_hash)` | No se marca PAID hasta que el hash fué verificado en la red. |
| Retiro confirmado | `engine.retirar(wallet_tx_hash)` | No se marca WITHDRAWN hasta que el TX fue escaneado y recibo verificado. |

## 7. BLOQUEOS DE VERIFICACIÓN EXTERNA

| Bloqueo | Dependencia externa | Estado |
|---|---|---|
| AgentHansa API | Credencial + API key + endpoints verificados | Pendiente de aprobación humana |
| Agent Bounties on-chain | Wallet, red, conexión a blockchain | Pendiente de aprobación humana |
| Algora policy | Política de automatización | Pendiente de verificación |
| MCPize/MuleRun/Apify/AgenticMarket | Demanda y pagos verificados | No viables para el primer pago |

## 8. PRÓXIMA ACCIÓN MÍNIMA

1. **Agregar** `core/opportunity/adapters/agentbounties_adapter.py` (estubado con puertas humanas) + test.
2. **Agregar** `api/routers/agentbounties.py` (descubrimiento y verificación de pagos on-chain).
3. **Agregar** test `tests/test_agentbounties_adapter.py` (simulación, no producción).
4. **Ejecutar** `ruff check` + `pytest tests/test_agentbounties_adapter.py`.
5. **Reportar** el estado, el bloqueo y la siguiente acción.
