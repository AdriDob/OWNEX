# NEXT SESSION START — Julio 2026

> Handoff document. Lee esto antes de cualquier acción.

---

## CURRENT STATE

| Métrica | Valor |
|---------|-------|
| Tests totales | 1401+ (45 nuevos Command System) |
| Último commit | `b14fbd8` — Command System Fase 1 |
| Rama | `main` |
| Working tree | Clean (commit realizado) |
| Ruff | Clean (0 errores en código nuevo) |
| Push pendiente | Sí — no se ha hecho push |

---

## PRIMERA TAREA RECOMENDADA

**FASE 1 — Cerrar Offensive Intelligence gaps (prioridad máxima por Revenue Rule):**

```yaml
prioridad: ALTA
impacto: Aumenta detección de vulnerabilidades
tiempo: ~2h
```

### Subtareas:
1. `core/offensive/contradiction.py` — Implementar `_attack_ssrf()`, `_attack_xss()`, `_attack_sqli()`, `_attack_auth_bypass()` (cada uno con 3-5 contradicciones tipo-específicas)
2. `core/offensive/reasoners/*.py` — Poblar `why_triager_might_reject` en los 5 reasoners
3. `core/offensive/reasoners/__init__.py` — Exportar los 5 reasoners
4. `tests/test_offensive.py` — Tests para las nuevas contradicciones

---

## BLOQUEADORES

| Bloqueador | Alternativa |
|------------|-------------|
| Router IP `172.29.176.1` es WSL virtual switch | Ejecutar `ip route` en Windows para obtener gateway real |
| Hermes tools tests requieren Windows nativo | No correr en Linux, skip condicional |
| Obsidian Syncthing requiere instalación Windows | Preguntar al usuario si lo instaló |
| Nobara requiere USB + reboot | No se puede hacer desde WSL |

---

## DECISIONES PENDIENTES

| Decisión | Opciones | Recomendación |
|----------|----------|---------------|
| ¿Freqtrade o Hummingbot? | Freqtrade (92/100), Hummingbot (85/100), ambos | Freqtrade first — más documentado, Python puro |
| ¿Evidence Critic en evidence o en offensive? | `core/evidence/critic.py` vs `core/offensive/triager.py` | Crear `core/evidence/critic.py` (está en el módulo correcto) |
| ¿Dashboard redesign ahora o después de cerrar gaps? | Ahora (UX) vs Después (funcionalidad) | Después — funcionalidad > estética |

---

## ARCHIVOS CRÍTICOS LEER ANTES DE COMENZAR

| Archivo | Por qué |
|---------|---------|
| `.ai/SESSION_CONTINUITY_AUDIT.md` | Gap analysis completo |
| `.ai/CURRENT_STATE.md` | Estado verificado actual |
| `.ai/TASK_QUEUE.md` | Tareas priorizadas |
| `core/offensive/contradiction.py` | Target #1 de implementación |
| `core/offensive/reasoners/*.py` | Target #2 (poblar why_triager_might_reject) |

---

## OBJETIVO PERMANENTE

> **Cada semana ORION debe depender menos del desarrollador y más de su propia memoria, automatización y capacidad de recomendación.**

No agregues funcionalidades sin verificar que:
- ✅ realmente funcionan
- ✅ están testeadas
- ✅ están documentadas
- ✅ aportan valor medible
- ✅ simplifican el sistema
- ✅ aumentan ingresos, productividad o calidad
