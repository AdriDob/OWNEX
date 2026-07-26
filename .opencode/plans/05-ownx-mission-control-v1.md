# 🚀 OWNEX PHASE 3 — Mission Control UI/UX

> **Estado**: PENDING
> **Prioridad**: ⭐⭐⭐⭐⭐ (máxima)
> **Depende de**: Frontend consolidation completada, OWNEX branding completado
> **Riesgo**: Medio — cambios visuales extensos, sin tocar lógica de negocio existente

## Instrucciones para OpenCode

Lee este plan completo antes de modificar código. No implementes hasta tener aprobación explícita.

---

## OBJETIVO PRINCIPAL

Crear **OWNEX Mission Control v1** — una interfaz que responda:

> "¿Qué está haciendo OWNEX hoy para aumentar mi capacidad de generar valor?"

La métrica principal del sistema será **THROUGHPUT**:

```
Valor generado / tiempo humano requerido
```

---

## DESIGN SYSTEM OWNEX

Mantener identidad existente (`frontend/src/style.css`):

| Elemento | Valor |
|----------|-------|
| Base | `#050505` (negro profundo) |
| Primario | Azul OWNEX |
| Texto | Blanco |
| Valor/importancia | Dorado |
| Éxito | Verde |
| Error/peligro | Rojo |
| Atención | Amarillo |

**NO USAR**: estética militar, CRT, phosphor glow, exceso de efectos, dashboards saturados.

**Inspiraciones**: Discord (navegación), VS Code (paneles), Linear (claridad), Obsidian (conocimiento).

**Sensación objetivo**: "Centro de comando moderno, oscuro, profesional."

---

## ARQUITECTURA VISUAL

```
OWNEX
│
├── Mission Control (dashboard principal)
│
├── Work Cycles
│   ├── Security (antes Rastro)
│   ├── Forge (Dev Bounty)
│   ├── AI Work (Pulse)
│   └── Wealth (Vault)
│
├── Knowledge (antes Copilot/Memoria)
│
├── Agents (infraestructura IA)
│
└── System (operaciones, settings)
```

---

## DASHBOARD PRINCIPAL — 6 Módulos

### 1. Throughput Core (métrica principal)
Tarjeta dominante, primera información visible.
- Valor generado (tendencia ↑)
- Oportunidades detectadas → analizadas → priorizadas → ejecutadas → resultados
- Efficiency %

### 2. Opportunity Radar
Lista de oportunidades con scoring.
- Fuente, tipo, recompensa estimada, dificultad, prioridad, score
- Preparado para datos futuros (no conectar APIs todavía)

### 3. Work Cycles
4 tarjetas grandes, cada una con estado y descripción.
- Security: ACTIVE
- Forge: MONITORING
- AI Work: AVAILABLE
- Wealth: TRACKING

### 4. Agent Fleet
Panel de infraestructura IA.
- Hermes, OpenCode, Cline, Ollama, FCC
- Estados: ONLINE / OFFLINE / LIMITED

### 5. Next Best Action
Una sola acción recomendada con botón Execute.
- Título, motivo, tiempo estimado, recompensa esperada

### 6. Knowledge Feed
Feed de nuevos aprendizajes, patrones, decisiones.

---

## UX PRINCIPLES

1. Menos información, más decisiones.
2. El usuario debe saber qué hacer en <5 segundos.
3. Todo módulo debe tener estado visible.
4. Todo preparado para automatización futura.
5. No hay pantallas muertas — cada módulo tiene estado aunque sea "sin datos".

---

## IMPLEMENTACIÓN

### Antes de escribir código:
1. Analizar `frontend/src/` completa
2. Identificar componentes reutilizables
3. Mapear deuda visual existente
4. Proponer plan de archivos afectados

### Durante implementación:
- NO eliminar funcionalidades existentes
- Migración progresiva, no rewrite
- Compatibilidad con rutas existentes (las 79 redirecciones deben seguir funcionando)
- Componentes reutilizables + código limpio

### Archivos esperados:
- `frontend/src/pages/MissionControl.vue` → refactor completo
- Posibles nuevos componentes en `frontend/src/components/dashboard/`
- Ajustes en `frontend/src/style.css` si es necesario
- Router no debería cambiar (ya consolidado)

---

## PREPARACIÓN FUTURA

Dejar interfaces preparadas (props, slots, composables vacíos) para:
- API real de oportunidades
- Agentes autónomos
- Scheduler status
- Notificaciones
- Knowledge Engine
- Memoria semántica

No crear mockups desechables. Construir la base del sistema.

---

## CRITERIO DE ÉXITO

Al abrir OWNEX, el usuario siente:

> "No estoy viendo una aplicación. Estoy viendo mi centro de operaciones digital."

### Checklist de verificación:
- [ ] Throughput Core visible sin scroll
- [ ] Opportunity Radar muestra estructura aunque sea con datos placeholder
- [ ] Work Cycles tienen estados visibles
- [ ] Agent Fleet muestra infraestructura
- [ ] Next Best Action es obvio (una sola acción)
- [ ] Knowledge Feed tiene espacio preparado
- [ ] Diseño responsivo
- [ ] Sin regresiones en rutas existentes
- [ ] Sin errores de compilación
- [ ] Ruff check pasa

---

## PRÓXIMOS PASOS (post-implementación)

1. Conectar Opportunity Radar con datos reales
2. Hacer que Next Best Action ejecute algo real
3. Work Cycles navegan a sus dashboards específicos
4. Knowledge Feed se conecta a UnifiedMemoryStore
