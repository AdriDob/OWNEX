# ORION Command System — Lenguaje Operativo v2

> **Propósito**: Lenguaje conversacional de alto nivel para que el agente (OpenCode, COPILOT, Companion) ejecute flujos completos de trabajo con comandos cortos, consistentes y memorables.
>
> No es CLI del sistema operativo. Es un protocolo agente-agente y agente-usuario con capa de inteligencia.

---

## Arquitectura

```
Usuario / COPILOT / Companion
       │
       ▼
┌──────────────────────────────┐
│   Command Intelligence Layer │  ← traduce intención → comandos
│   (COPILOT como frontend)    │
└──────────┬───────────────────┘
           │ /id
           ▼
┌──────────────────────────────┐
│      Command Parser          │  ← extrae comando + args + flags
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│   Permission Validator       │  ← PUBLIC / OPERATOR / ADMIN / SYSTEM / DANGEROUS
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│    Cost Evaluator            │  ← ¿alcanza el budget? ¿simular?
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│   Command Dispatcher         │  ← resuelve handler (simple / chain / macro / goal)
└──────────┬───────────────────┘
           ▼
┌──────────────────────────────┐
│  Execution Platform / Direct │  ← workflow compilado o handler directo
└──────────┬───────────────────┘
           ▼
    Event Bus: command:executed / command:failed / command:rejected
           ▼
    Knowledge Graph: registra decisión + resultado
           ▼
    COPILOT: aprende del outcome
```

---

## Modelo de comando (definitivo)

```yaml
command:
  name: /recon
  aliases: [/rc]
  category: bugbounty
  description: "Recon inteligente: subfinder → katana → wayback → KG → COPILOT"
  permission: OPERATOR        # PUBLIC | OPERATOR | ADMIN | SYSTEM | DANGEROUS
  interactive: false          # true = abre wizard, false = respuesta directa
  silent: false               # true = solo eventos, sin output UI

  cost:
    time: 3 min
    cpu: medium
    network: yes
    tokens: 15000
    money: 0.04 usd

  params:
    - name: target
      type: string
      required: true
      description: "Dominio o URL objetivo"

  flags:
    - name: silent
      alias: -s
      description: "Ejecutar sin output, solo eventos"
    - name: dry-run
      alias: -d
      description: "Mostrar qué haría sin ejecutar"

  events_published:
    - command:recon:started
    - command:recon:completed
    - command:recon:failed

  capabilities_used:
    - recon:subfinder
    - recon:katana
    - recon:wayback
    - kg:search
    - copilot:analyze

  chains: []                  # Si es compuesto, lista de sub-comandos
  expands_to: []              # Si es macro, comandos a expandir
  risk: low                   # low / medium / high / critical
  why: "Explica la decisión del dispatcher cuando se usa --why"
```

---

## Permission levels

| Nivel | Quién | Ejemplos |
|-------|-------|----------|
| **PUBLIC** | Cualquier agente, sin restricción | `/status`, `/help`, `/docs`, `/setup`, `/health` |
| **OPERATOR** | Usuarios avanzados, COPILOT autónomo | `/recon`, `/idor`, `/report`, `/validate`, `/evidence`, `/poc` |
| **ADMIN** | Administradores del sistema | `/refactor`, `/rollback`, `/ship`, `/setup repair`, `/clean`, `/migrate` |
| **SYSTEM** | Solo auto-operaciones del sistema | `/self-heal`, `/prune`, `/vacuum`, `/reindex`, `/checkpoint` |
| **DANGEROUS** | Requiere confirmación explícita | `/delete`, `/reset`, `/purge`, `/drop` |

---

## Command Flags (universales)

| Flag | Alias | Aplica a | Efecto |
|------|-------|----------|--------|
| `--silent` | `-s` | Todos | No genera output UI. Solo eventos en Event Bus. Ideal para automatización y chains. |
| `--dry-run` | `-d` | Todos | Muestra qué haría sin modificar nada. Preview completo. |
| `--simulate` | `-sim` | Ejecución | Ejecuta en Simulation Runtime (sin APIs reales, sin costo). |
| `--preview` | `-p` | Report/Evidence | Muestra resultado antes de generarlo definitivamente. |
| `--why` | `-w` | Todos | Explica por qué se eligió este comando/acción/prioridad. |
| `--interactive` | `-i` | Soportados | Abre wizard interactivo en vez de respuesta directa. |
| `--format` | `-f` | Todos | Formato de salida: text, json, markdown, html |
| `--context` | `-c` | Todos | Contexto adicional (target, program, finding_id) |

---

## Modes (Perfiles de trabajo)

```
/mode developer       → comandos: /test, /ruff, /refactor, /quality
/mode hunter          → comandos: /recon, /idor, /api, /attack, /validate
/mode architect       → comandos: /audit, /review, /debt, /score, /simplify
/mode admin           → comandos: /status, /setup, /doctor, /repair, /ship
/mode auditor         → comandos: /audit all, /security, /quality, /ready
```

Cada perfil cambia:
- Comandos favoritos y prioritarios
- Briefing de `/morning`
- Output preferido
- Permisos elevados según necesidad

---

## Persistent Context

El sistema recuerda automáticamente:

```
current_target     → /recon lo usa sin especificar dominio
current_program    → /report sabe a qué plataforma enviar
current_workflow   → /run sabe qué ejecutar
current_report     → /evidence sabe de qué finding hablar
current_branch     → /ship sabe qué mergear
```

Se setea con:
```
/target acme.com           → context.target = "acme.com"
/program hackerone         → context.program = "hackerone"
```

Y se consulta con:
```
/context                  → muestra contexto actual
```

---

## Autocompletado inteligente

Basado en:
- Coincidencia de prefijo
- Historial de comandos del usuario
- Perfil activo
- Contexto actual

```
/rep  →  report  (hunter mode)
/rep  →  replay  (developer mode)
/rep  →  repair  (admin mode)
```

---

## Command Chains

Secuencias declarativas de comandos. Cualquier usuario puede crear una.

```yaml
chain:
  name: morning
  description: "Briefing matutino completo"
  steps:
    - /health
    - /status --brief
    - /priorities --top 3
    - /improve --quick
    - /next
```

```yaml
chain:
  name: ship
  description: "Release gate completo"
  steps:
    - /ruff --fix
    - /test --full
    - /audit quick
    - /security --quick
    - /docs update
    - /quality
    - /changelog
    - /notify "Release ready for review"
```

Ejecución:
```
/morning              → ejecuta la chain "morning"
/ship --dry-run       → preview de release gate sin ejecutar
```

---

## Macros

Expansión automática de un comando a múltiples.

```yaml
macro:
  name: hunt
  description: "Ciclo completo de caza para un target"
  expands_to:
    - /recon {target}
    - /api {target}
    - /idor {target}
    - /auth {target}
    - /businesslogic {target}
    - /attack
    - /validate
    - /evidence
    - /report
```

```yaml
macro:
  name: quick_test
  description: "Validación rápida post-cambio"
  expands_to:
    - /ruff {path}
    - /test quick {path}
```

Ejecución:
```
/hunt acme.com        → expande a 9 comandos secuenciales
/quick_test core/x/   → ruff + test quick en ese path
/hunt --dry-run       → muestra los 9 comandos sin ejecutar
```

---

## Objectives (Goals)

ORION recibe un objetivo y construye el workflow automáticamente.

```
/goal first_bounty
```

COPILOT interpreta:
```
1. /money → ¿qué programa/vuln tiene mayor expected revenue?
2. /priorities → elegir target
3. /recon → descubrir superficie
4. /api + /idor + /auth → análisis ofensivo
5. /validate → validar hallazgos
6. /evidence → generar pruebas
7. /report → enviar
8. /learn → aprender del outcome
```

```yaml
goal:
  name: first_bounty
  description: "Conseguir la primera recompensa en bug bounty"
  workflow:
    - /money
    - /priorities
    - /recon {context.target}
    - /api {context.target}
    - /idor {context.target}
    - /auth {context.target}
    - /businesslogic {context.target}
    - /attack
    - /validate
    - /evidence
    - /report
    - /learn

  success_metric: "report accepted with bounty > 0"
```

```
/goal optimize_recon          → ORION decide cómo mejorar recon pipeline
/goal learn_from_outcomes     → ORION extrae lecciones de todos los outcomes recientes
/goal improve_acceptance     → ORION optimiza reportes para aumentar tasa de aceptación
```

---

## Taxonomía completa

### A — Arquitectura & Calidad (10)

| Comando | Alias | Permiso | Costo (est.) | Flags |
|---------|-------|---------|-------------|-------|
| `/audit` | `/a` | ADMIN | 5min, 20K tokens | --quick, --why, --format |
| `/audit quick` | `/aq` | OPERATOR | 1min, 5K tokens | --why, --format |
| `/review` | `/rv` | ADMIN | 3min, 10K tokens | --module, --why |
| `/refactor` | `/rf` | ADMIN | 5min, 30K tokens | --dry-run, --why |
| `/clean` | `/cl` | ADMIN | 2min, 5K tokens | --dry-run |
| `/optimize` | `/op` | ADMIN | 3min, 10K tokens | --dry-run, --why |
| `/simplify` | `/sp` | ADMIN | 2min, 8K tokens | --dry-run |
| `/score` | `/sc` | PUBLIC | 30s, 2K tokens | --format |
| `/roadmap` | `/rm` | PUBLIC | 10s, 1K tokens | --phase |
| `/debt` | `/db` | ADMIN | 2min, 5K tokens | --priority, --why |

### B — Bug Bounty & Ofensivo (12)

| Comando | Alias | Permiso | Costo (est.) | Flags |
|---------|-------|---------|-------------|-------|
| `/recon` | `/rc` | OPERATOR | 5min, $0.05 | --silent, --quick, --dry-run |
| `/idor` | `/id` | OPERATOR | 3min, $0.03 | --endpoint, --dry-run |
| `/api` | `/ap` | OPERATOR | 4min, $0.04 | --endpoint, --graphql, --rest |
| `/auth` | `/au` | OPERATOR | 3min, $0.03 | --url, --dry-run |
| `/businesslogic` | `/bl` | OPERATOR | 4min, $0.04 | --flow, --dry-run |
| `/attack` | `/at` | OPERATOR | 5min, $0.05 | --entry, --simulate |
| `/validate` | `/va` | OPERATOR | 2min, $0.02 | --finding, --quick |
| `/poc` | `/pc` | OPERATOR | 3min, $0.03 | --finding, --preview |
| `/evidence` | `/ev` | OPERATOR | 2min, $0.02 | --finding, --preview, --format |
| `/report` | `/rp` | OPERATOR | 3min, $0.03 | --finding, --platform, --preview |
| `/acceptance` | `/ac` | OPERATOR | 1min, $0.01 | --finding, --why |
| `/attack graph` | `/ag` | OPERATOR | 3min, $0.03 | --entry, --depth |

### C — COPILOT (8)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/copilot think` | `/ct` | OPERATOR | 2min, 10K tokens | --context, --why |
| `/copilot plan` | `/cp` | OPERATOR | 3min, 15K tokens | --target, --dry-run |
| `/copilot explain` | `/ce` | PUBLIC | 1min, 5K tokens | --what, --format |
| `/copilot decide` | `/cd` | OPERATOR | 2min, 10K tokens | --options, --why |
| `/copilot critique` | `/cc` | OPERATOR | 2min, 8K tokens | --what |
| `/copilot learn` | `/cl` | SYSTEM | 3min, 20K tokens | --outcome, --why |
| `/copilot simulate` | `/cs` | OPERATOR | 2min, 10K tokens | --strategy, --simulate |
| `/copilot status` | `/cst` | PUBLIC | 5s, 500 tokens | --format |

### D — Execution Platform (9)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/workflow` | `/wf` | OPERATOR | 1min | --list, --create, --inspect |
| `/workflow run` | `/wfr` | OPERATOR | variable | --simulate, --dry-run |
| `/compile` | `/cp` | OPERATOR | 30s | --workflow, --validate |
| `/validate wf` | `/vw` | OPERATOR | 20s | --workflow |
| `/run` | `/rn` | OPERATOR | variable | --simulate, --dry-run |
| `/replay` | `/rp` | ADMIN | 30s | --execution, --step |
| `/checkpoint` | `/ch` | SYSTEM | 10s | --list, --save, --restore |
| `/rollback` | `/rb` | DANGEROUS | 30s | --to |
| `/metrics` | `/mt` | PUBLIC | 10s | --execution, --format |

### E — Runtime & Sistema (8)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/status` | `/st` | PUBLIC | 5s | --brief, --format |
| `/health` | `/h` | PUBLIC | 10s | --brief, --why |
| `/jobs` | `/jb` | OPERATOR | 5s | --active, --queue |
| `/resources` | `/rs` | ADMIN | 5s | --resource |
| `/events` | `/ev` | OPERATOR | 10s | --recent, --type, --format |
| `/journal` | `/jn` | ADMIN | 10s | --execution |
| `/queue` | `/qu` | OPERATOR | 5s | --status |
| `/scheduler` | `/sc` | ADMIN | 5s | --jobs, --workers |

### F — Knowledge Graph (5)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/kg search` | `/ks` | PUBLIC | 10s | --type, --pattern, --limit |
| `/kg explain` | `/ke` | PUBLIC | 15s | --node, --depth |
| `/kg neighbors` | `/kn` | PUBLIC | 10s | --node, --type, --depth |
| `/kg path` | `/kp` | PUBLIC | 15s | --from, --to |
| `/kg stats` | `/kg` | PUBLIC | 5s | --format |

### G — Event System (5)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/events recent` | `/er` | PUBLIC | 5s | --limit, --type |
| `/events replay` | `/erp` | ADMIN | 20s | --correlation, --execution |
| `/events search` | `/es` | OPERATOR | 10s | --type, --source, --from, --to |
| `/events trace` | `/et` | OPERATOR | 15s | --correlation |
| `/events stats` | `/est` | PUBLIC | 5s | --period, --format |

### H — Testing (7)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/test` | `/t` | OPERATOR | 2min | --module, --quick, --format |
| `/test quick` | `/tq` | OPERATOR | 30s | --path |
| `/test module` | `/tm` | OPERATOR | 1min | --module |
| `/test runtime` | `/tr` | OPERATOR | 1min | --runtime |
| `/test security` | `/ts` | ADMIN | 3min | --quick |
| `/test regression` | `/tg` | ADMIN | 5min | --baseline |
| `/test coverage` | `/tc` | OPERATOR | 30s | --module, --format |

### I — Linting & Quality (7)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/ruff` | `/r` | OPERATOR | 30s | --fix, --path |
| `/lint` | `/l` | OPERATOR | 30s | --fix, --path |
| `/types` | `/ty` | OPERATOR | 1min | --module, --strict |
| `/security` | `/sec` | ADMIN | 3min | --quick, --format |
| `/performance` | `/perf` | ADMIN | 2min | --benchmark |
| `/coverage` | `/cov` | OPERATOR | 30s | --module |
| `/quality` | `/q` | OPERATOR | 2min | --gate, --format |

### J — Documentation (5)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/docs` | `/d` | PUBLIC | 5s | --module, --format |
| `/docs build` | `/db` | ADMIN | 2min | --all, --module |
| `/docs module` | `/dm` | PUBLIC | 10s | --module |
| `/docs api` | `/da` | PUBLIC | 10s | --format |
| `/docs search` | `/ds` | PUBLIC | 5s | --query |

### K — Setup & Config (6)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/setup` | `/s` | PUBLIC | 5s | --status, --format |
| `/setup wizard` | `/sw` | OPERATOR | 2min | --step, --resume |
| `/setup doctor` | `/sd` | ADMIN | 1min | --quick, --repair |
| `/setup repair` | `/sr` | DANGEROUS | 2min | --dry-run, --what |
| `/setup validate` | `/sv` | PUBLIC | 30s | --all, --module |
| `/setup context` | `/sctx` | PUBLIC | 5s | --get, --set, --clear |

### L — Integraciones (7)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/integrations` | `/i` | PUBLIC | 10s | --status, --category, --format |
| `/integrations test` | `/it` | OPERATOR | 30s | --name |
| `/integrations setup` | `/is` | OPERATOR | 1min | --name, --guide |
| `/outlook` | `/ol` | OPERATOR | 10s | --status, --sync |
| `/arca` | `/ar` | OPERATOR | 10s | --status, --sync |
| `/mode` | `/m` | PUBLIC | 5s | nomode |
| `/profile` | `/pf` | PUBLIC | 5s | --set, --show |

### M — Inteligencia & Estrategia (9)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/strategy` | `/stg` | OPERATOR | 2min, 10K tokens | --why, --format |
| `/priorities` | `/pr` | PUBLIC | 10s, 1K tokens | --top, --why |
| `/revenue` | `/$` | OPERATOR | 1min, 5K tokens | --target, --type, --program |
| `/opportunities` | `/op` | OPERATOR | 1min, 5K tokens | --target, --top |
| `/improve` | `/im` | OPERATOR | 2min, 8K tokens | --quick, --why |
| `/learn` | `/lr` | SYSTEM | 3min, 20K tokens | --outcome, --period |
| `/decisions` | `/dc` | PUBLIC | 10s, 1K tokens | --recent, --outcome, --format |
| `/next` | `/nx` | OPERATOR | 30s, 5K tokens | --why |
| `/goal` | `/g` | OPERATOR | variable | --list, --set, --status |

### N — Comandos Inteligentes (Compuestos) (9)

| Comando | Alias | Permiso | Costo | Flags |
|---------|-------|---------|-------|-------|
| `/ship` | `/sh` | ADMIN | 5min, $0.05 | --dry-run, --quick |
| `/audit all` | `/aa` | ADMIN | 5min, 25K tokens | --dry-run, --why, --format |
| `/ready` | `/rd` | ADMIN | 3min, 15K tokens | --why, --format |
| `/money` | `/$$` | OPERATOR | 2min, 10K tokens | --why, --format |
| `/doctor` | `/dr` | ADMIN | 3min, 10K tokens | --quick, --repair |
| `/morning` | `/am` | PUBLIC | 30s, 5K tokens | --brief, --format |
| `/hunt` | `/ht` | OPERATOR | 15min, $0.20 | --target, --dry-run, --simulate |
| `/quick_test` | `/qt` | OPERATOR | 30s | --path |
| `/changelog` | `/cl` | ADMIN | 10s | --since, --format |

---

## Objetivos predefinidos

| Goal | Dispara | Éxito |
|------|---------|-------|
| `/goal first_bounty` | money → priorities → recon → attack → validate → evidence → report → learn | Reporte aceptado con bounty |
| `/goal optimize_recon` | audit recon → improve → learn → deploy | Cobertura de recon mejorada |
| `/goal learn_from_outcomes` | kg search outcomes → copilot learn → strategy | Modelos de decisión actualizados |
| `/goal improve_acceptance` | audit reports → acceptance → copilot learn → strategy | Tasa de aceptación ↑ |
| `/goal reduce_false_positives` | audit validation → gate → challenger → learn | FP rate ↓ |
| `/goal scale_hunting` | strategy → priorities → workflows → automate | Targets/hora ↑ |

---

## Macros predefinidas

| Macro | Expande a |
|-------|-----------|
| `/hunt {target}` | recon → api → idor → auth → businesslogic → attack → validate → evidence → report |
| `/quick_test {path}` | ruff {path} --fix → test quick {path} |
| `/full_test` | ruff --fix → test → types → security --quick |
| `/deploy_check` | quality → audit quick → security → docs build → changelog |
| `/context_set {target}` | target {target} → program → workflow |
| `/daily_brief` | health → status --brief → priorities --top 3 → next |

---

## Chains predefinidas

| Chain | Pasos |
|-------|-------|
| `morning` | health → status --brief → priorities --top 3 → improve --quick → next |
| `ship` | ruff --fix → test --full → audit quick → security --quick → docs update → quality → changelog → notify |
| `deploy` | quality → audit quick → security → ship |
| `weekly_review` | audit all → debt → learn --period 7d → strategy → priorities → money |
| `incident_response` | status → health → events recent --limit 50 → journal --last → doctor |

---

## Formatos de salida

Todos los comandos aceptan `--format`:

| Formato | Uso |
|---------|-----|
| `text` | Default. Legible para humanos en chat. |
| `json` | Para consumo programático (Companion, COPILOT). |
| `markdown` | Para documentación o exportación. |
| `html` | Para dashboard o reporte visual. |
| `silent` | Solo eventos, sin output. Equivalente a --silent. |

---

## Fases de implementación

### Fase 0 — Command Registry (Chat-only, inmediato)
- Registro de comandos en Capability Registry como `command:*`
- Parser simple: el agente reconoce `/comando` y ejecuta el flujo
- Sin infraestructura nueva — solo documentación + convención + AGENTS.md
- Cost: estimado, no real
- Permissions: validados por el agente, no por código

### Fase 1 — Command Dispatcher (Runtime)
- `core/commands/` módulo con dispatcher real
- Permission Validator usando COPILOT authority levels existentes
- Cost Evaluator con budget tracking
- Publicación de eventos `command:*` en Event Bus
- Registro en Knowledge Graph como nodos DECISION
- LOGS en audit log

### Fase 2 — Execution-backed commands
- Handlers complejos compilados como workflows de Execution Platform
- `/ship`, `/audit all`, `/hunt` como workflows
- Simulation mode para `--simulate` y `--dry-run`

### Fase 3 — Command SDK + Intelligence Layer
- Extension SDK: `manifest.py` → `commands: [...]`
- COPILOT como Command Intelligence Layer: lenguaje natural → comandos
- Goals: COPILOT construye workflow automático desde objetivo
- Macros y chains declarativas en YAML
- Profiles, contexto persistente, autocompletado

---

## Integración con lo existente

| Sistema | Rol |
|---------|-----|
| **Event Bus** | Cada comando publica `command:executed` / `command:failed` / `command:rejected` |
| **Capability Registry** | Comandos registrados como `command:<name>` |
| **Knowledge Graph** | Comandos ejecutados = nodos DECISION con resultado |
| **COPILOT** | Frontend del Command Intelligence Layer. Traduce intención → comandos. Aprende de outcomes. |
| **Execution Platform** | Handlers complejos como workflows compilados |
| **Documentation** | Auto-generada desde el registry |
| **Setup Wizard** | Comandos ejecutables desde wizard steps |
| **IdentityVault** | Tokens y credenciales para comandos que requieren APIs externas |
| **Health Center** | Comandos de diagnóstico usan health checks |
| **Metrics Engine** | Cost tracking por comando |

---

## Resumen

| Dimensión | Valor |
|-----------|-------|
| Total comandos | 102 |
| Categorías | 14 |
| Permission levels | 5 (PUBLIC / OPERATOR / ADMIN / SYSTEM / DANGEROUS) |
| Flags universales | 8 (--silent, --dry-run, --simulate, --preview, --why, --interactive, --format, --context) |
| Modes (perfiles) | 5 (developer, hunter, architect, admin, auditor) |
| Objetivos predefinidos | 5 |
| Macros predefinidas | 6 |
| Chains predefinidas | 5 |
| Fases implementación | 4 |
| Modo "Language First" | Sí — COPILOT interpreta intención y traduce a comandos |
