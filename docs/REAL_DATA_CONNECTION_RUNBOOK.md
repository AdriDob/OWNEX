# RUNBOOK — Instalación limpia + conexión a datos reales de revenue

Estado: PLAN — para ejecutar el día de la instalación limpia.
Generado: 2026-08-04. Verificado contra código real (adapters, DB, .env).

## 1. Lo que ya está construido y verificado (no tocar)

| Componente | Ubicación | Estado |
|---|---|---|
| Discovery de oportunidades | core/opportunity/engine.py + adapters/ | 8 runs reales, 135 fuentes por run |
| Adapters de plataformas | core/opportunity/adapters/ (atlas, forge, freelancer, github→issuehunt/opire/opyre, linkedin, opencollective, pulse, security, vault) | Presentes |
| Scoring/priorización | mercenary_filter, prioritizer (usd/hour), economic_scorer | Presentes |
| Pipeline findings→reportes | database (findings, reports, verdicts, evidence) | Tablas creadas, vacías |
| Rastreador económico | revenue_events, revenue_payouts, financial_metrics, bank-payout (Plaid) | Tablas creadas, vacías |
| Seed demo (NO usar en prod) | scripts/seed_real.py | Programas reales + findings SIMULADOS — solo testing |

## 2. Lo que FALTA para conectar datos reales (el gap real)

### 2.1 Credenciales de plataforma — HALLazgo CLAVE

El sistema NO usa el .env para plataformas de pago. Todo vive en un vault central:
- Módulo: `core/credentials/vault.py` (define 29 claves de plataforma)
- Archivo de credenciales: `~/.config/ownex/opportunity.env` (Este NO existe hoy — por eso 0 configuradas)
- El `.env` actual solo tiene claves de AI (OpenRouter/Gemini/NVIDIA/OMNIROUTE/OpenCode/FCC)

Verificado hoy (2026-08-04): 0 de 29 credenciales de plataforma configuradas.
`python scripts/validate_credentials.py` saca la lista exacta de faltantes.

Plataformas que el vault soporta (desde vault.py, listado real):
- FORGE (dev bounty / open source): ALGORA, FREELANCER, GITHUB, ISSUEHUNT, ISSUEHAND, OPIRE, OPENCOLLECTIVE, SUPERTEAM
- PULSE (microtasks / AI data): OUTLIER, MINDRIFT, DATAANNOTATION, REMOTASKS, FREELANCER_MICRO, LINKEDIN, OPYRE_MICRO
- Bug bounty: HACKERONE, BUGCROWD, INTIGRITI, SYNACK, YESWEHACK, IMMUNEFI, CODE4RENA, CANTINA, SHERLOCK, CODEHAWKS
- AI: OPENAI, ANTHROPIC, OMNIROUTE, FCC, OLLAMA

Pasos:
```bash
# 1. Ver qué falta
python scripts/validate_credentials.py

# 2. Crear el archivo de credenciales desde el template
mkdir -p ~/.config/ownex
cp docs/opportunity.env.example ~/.config/ownex/opportunity.env
# 3. Editar ~/.config/ownex/opportunity.env y llenar SOLO lo que usarás esta semana
#    NUNCA committear este archivo.
# 4. Re-validar
python scripts/validate_credentials.py   # debería bajar "Configuradas ahora: N"
```

### 2.2 Programas con scope real (hoy: 2515 targets, 0 scopes/programs)
El sistema necesita programas con scope_documents para poder cazar. Cargar desde:
- HackerOne/Bugcrowd públicos vía API (policy.json / scope.json)
- core/setup/steps/integrations_step.py (wizard) si configura cuentas

### 2.3 Config de AI funcional
Verificar que el provider AI (OpenRouter/Gemini/FCC) responde — el sistema usa LLM para análisis y reportes.

## 3. Orden de ejecución el día de la instalación limpia

```bash
# 1. Backup del estado actual (si hay algo que conservar)
python run.py --backup

# 2. Instalación limpia
python scripts/install.py          # o el flujo oficial de instalación
python scripts/bootstrap.py        # primer arranque

# 3. Verificar salud
make check                         # ruff + tests rápidos
curl http://localhost:8000/api/health

# 4. Cargar credenciales de plataformas (2.1) — NUNCA commitear
python scripts/validate_credentials.py        # ver qué falta
mkdir -p ~/.config/ownex
cp docs/opportunity.env.example ~/.config/ownex/opportunity.env
#    Editar ~/.config/ownex/opportunity.env (ver 2.1)



# 5. Cargar programas reales con scope (2.2)
python scripts/seed_real.py        # ⚠ SOLO si se quiere dataset de referencia (demo)
#    O cargar scopes reales desde las APIs de las plataformas

# 6. Validación end-to-end
python scripts/real_world_validation.py   # valida que el pipeline corre con datos reales
```

## 4. Primeros pagos — estrategia por velocidad

| Vía | Tiempo al 1er pago | Monto típico | Prioridad |
|---|---|---|---|
| Dev bounty (GitHub/IssueHunt/Opire/OnlyDust) | 1-3 semanas | $50-500/tarea | PRIMERA |
| Data annotation (Toloka/DataAnnotation/Appen) | días | $50-400/mes | PRIMERA (flujo) |
| Bug bounty (HackerOne/Bugcrowd públicos) | 3-8 semanas | $200-2.000/aceptado | EN PARALELO |
| Freelance (adapters/freelancer.py) | 2-4 semanas | $100-1.000/proyecto | OPCIONAL |

## 5. Criterio de éxito post-instalación (medible, no opinión)

- [ ] /api/stability/status responde con tools.active > 0 y sin broken
- [ ] Al menos 1 programa con scope cargado (programs > 0, scope_documents > 0)
- [ ] 1 discovery run completado con datos reales (no seed demo)
- [ ] 1er payout registrado en revenue_payouts (aunque sea $10)
- [ ] Scheduler corre solo: 2+ runs de discovery automáticos/semana
