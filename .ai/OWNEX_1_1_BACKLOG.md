# OWNEX 1.1 BACKLOG — Capital OS + Capas Ortogonales (post v1.0)

> **Origen**: razonamiento del owner (2026-08-26). Regla: NADA de esto entra a la
> Alpha 1.0 (release freeze). Se registra ahora para no perder la visión ni usarla
> como excusa para seguir desarrollando antes de cerrar.

## Principio rector

OWNEX pasa de **Income OS** a **Personal Economic OS**:

```
tiempo → trabajo → ingreso → capital → capacidad → nuevo ingreso
```

El diferenciador NO es otra planilla financiera (eso lo resuelven OwnFin/OpenCoffer):
es la capa superior — *¿cómo convierto capital y tiempo en más capacidad económica?*

## Los 5 motores 1.1 (en orden de valor)

| # | Motor | Qué hace | Base existente (NO reconstruir) |
|---|---|---|---|
| 1 | **Net Economic Value Engine** | `NET_EXPECTED_VALUE_PER_HUMAN_HOUR` nominal≠real (qualification, rechazo, cash delay, disponibilidad) | `economics.compute_expected_human_value()` + HTROI-V1 + availability monitor |
| 2 | **Capital Allocation Engine** | "¿Dónde produce más mi próximo dólar?" — compara skill/hardware/trading/reserva/publi | `payment_compat` (76 cuentas curadas) + `financial_intelligence/argentina_payout_methods` |
| 3 | **Economic Learning/Calibration** | predicho vs real → modelo personal | `calibration.py` JSONL + platform_factor YA EXISTE — extender a $/h |
| 4 | **Risk & Diversification** | concentración por plataforma/categoría/país/provider | revenue metrics por plataforma (proyección SSOT nueva) |
| 5 | **Self-Optimization Engine** | ¿qué construir esta semana para +ingreso futuro? | STRATEGIC_AUDIT framework + evolution layer |

## Capas ortogonales evaluadas (decisión)

| Capa | Veredicto | Razón / base |
|---|---|---|
| Autonomous Control Plane | 🟡 1.1 parcial | HealthCenter + scheduler run ledger ya observan; falta correlación cross-dominio |
| Reality Engine | ✅ YA EXISTE | calibration.py predicho-vs-real (Fase D Income Multiplier) |
| Permission & Safety Kernel | 🟡 consolidar | human gates + approvals wear-os + SafeWriter authorized=True existen dispersos |
| Overnight Runtime | 🟡 casi existe | scheduler 49 jobs + workbank daily_cycle ya corren solos; falta brief matinal consolidado (daily_companion existe) |
| Digital Twin / Scenario Sim | 🔴 1.2 | sin datos suficientes aún; requiere calibration acumulada |
| Agent Swarm roles | ❌ NO | lección LESSONS #12: consolidación > expansión; guardería de LLMs |
| OWNEX como API personal (MCP) | 🟡 evaluar 1.1 | OpenAPI 1006 paths ya es contrato; MCP = wrapper fino |

## Superficies (decisión coherente con auditoría previa)

- **Desktop** = cerebro (Tauri canónico, decisión convergencia 2026-08-24).
- **Mobile** = bolsillo: consolidar android/ APK (ai.rastro.app) + páginas Companion
  del frontend sobre contratos reales; offline-first queue = gap REAL a cerrar en 1.1.
- **Watch** = SOLO el contrato backend existente (`/api/wear-os/*`: notifications,
  approvals, status). NO se construye cliente watch nuevo — AUD-14 descartó el build
  WearOS por ROI negativo; el teléfono relaiea al reloj si algún día existe.

## Regla de entrada a 1.1

Solo después de: Alpha 1.0 instalada en Windows limpio → ciclo económico REAL
completo ejecutado por el owner → freeze respetado ≥ 2 semanas de uso operativo.
