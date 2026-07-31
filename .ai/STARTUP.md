# Agent Startup Protocol — "Ponte a trabajar"

> **Objetivo:** Cualquier agente (OpenCode, Cline, Copilot, futuro) puede decir "ponte a trabajar" y retomar el desarrollo de OMEGA de forma óptima, sin intervención humana.

## 1. SECUENCIA DE ARRANQUE (OBLIGATORIA)

Antes de escribir cualquier línea de código, el agente DEBE ejecutar esta secuencia:

### Paso 1: Version Check
```bash
python -m core.system.version_engine info
```
Verificar que VERSION.txt, pyproject.toml, frontend/package.json, core/__init__.py y apps/*/manifest.py están sincronizados. Si no, corregir con `python -m core.system.version_engine sync`.

### Paso 2: State Snapshot
Leer en orden:
1. `.ai/SESSION_CHECKPOINT.md` — ¿qué se hizo en la última sesión?
2. `.ai/TASK_QUEUE.md` — ¿qué está pendiente con prioridad?
3. `.ai/CURRENT_STATE.md` — ¿qué features están DONE vs WIP?
4. `.ai/KNOWN_DEBT.md` — ¿qué deuda técnica conocida?
5. `.ai/DO_NOT_TOUCH.md` — ¿qué está congelado?

### Paso 3: Health Check
```bash
python -m ruff check core/ api/ cores/ 2>&1 | tail -5
python -m pytest tests/ -x -q --timeout=15 --tb=no 2>&1 | tail -5
```
Si hay errores críticos (imports rotos, tests fallando), priorizar arreglos sobre nuevas features.

### Paso 4: Quick Wins Scan
```bash
python -c "from cores.opportunity.auto_scanner import run_scan; r = run_scan(); print(r)" 2>/dev/null
```
¿Hay oportunidades nuevas detectadas que no están siendo procesadas?

### Paso 5: Decide Next Action
Seleccionar la tarea de mayor impacto de TASK_QUEUE.md que:
- NO esté marcada como DONE
- NO requiera tocar archivos en DO_NOT_TOUCH.md
- Aumente alguna métrica de Revenue Rule

## 2. PRE-WORK CHECKLIST

Antes de modificar código, verificar:

- [ ] ¿La feature ya existe? Buscar en `cores/`, `core/`, `api/` antes de crear.
- [ ] ¿Hay un test que cubra esto? Buscar en `tests/`.
- [ ] ¿El cambio es atómico? < 200 líneas, < 1 archivo idealmente.
- [ ] ¿No rompe compatibilidad? No cambiar APIs públicas sin migración.
- [ ] ¿Respeta el Revenue Rule? Aumenta detección, evidencia, aceptación o aprendizaje.

## 3. POST-WORK PROTOCOL

Después de cada cambio:

1. **Lint:** `ruff check <archivos_modificados>`
2. **Tests:** `pytest tests/ -x -q --timeout=15` (al menos los relacionados)
3. **Version bump:** Si es un release, `python -m core.system.version_engine bump patch --auto-sync`
4. **Changelog:** `python -m core.system.version_engine bump patch -c "Descripción del cambio"`
5. **Checkpoint:** Actualizar `.ai/SESSION_CHECKPOINT.md` con:
   - Qué archivos modificé
   - Por qué
   - Evidencia (tests pasan, lint limpio)
   - Qué sigue

## 4. CONTINUITY RULES

- **Nunca asumir estado.** Siempre leer .ai/ antes de actuar.
- **Nunca crear duplicado.** Buscar antes de crear.
- **Nunca tocar lo congelado.** DO_NOT_TOUCH.md es obligatorio.
- **Siempre dejar rastro.** Si modificás código, actualizá la documentación en .ai/.
- **Siempre verificar.** Ruff + pytest después de cada cambio.

## 5. AGENT COMMANDS

| Comando | Acción |
|---------|--------|
| `make work` | Ejecuta startup protocol + muestra next action |
| `make lint` | Ruff check en todo el proyecto |
| `make test` | Pytest suite completa |
| `make version-info` | Muestra estado de versionado |
| `make version-sync` | Sincroniza VERSION.txt a todos los archivos |
| `make version-bump` | Bump de patch + sync + changelog |
| `make checkpoint` | Genera resumen de cambios desde el último commit |
| `make status` | Health check completo del sistema |
