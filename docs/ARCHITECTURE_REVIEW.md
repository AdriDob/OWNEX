# Architecture Review — July 2026

## Jerarquía Oficial (NO modificar)

```
                         ADRIEL
                      (Usuario/Arquitecto)
                      Dueño, decisor final
                            |
                            |
                       ORION CORE
                    (Ecosistema principal)
                  Inteligencia ofensiva y estratégica
                            |
           ┌────────────────┼────────────────┐
           |                |                |
        MERLIN           Atlas          Revenue
    (Copiloto IA)    (Finanzas)      (Multiplicadores)
    Estratégico      Simulación      Ingresos
    Razonamiento     Riesgo          Pipeline
    Planificación    Portfolio       Métricas
                            |
                    Integraciones
                    EventBus / KG / Memory
                            |
                     Hermes One (EXTERNO)
                   Control y automatización del PC
                   NO pertenece al código de ORION
```

## Responsabilidades

### ADRIEL
- Autoridad máxima del sistema
- Dueño, arquitecto de objetivos
- Toma decisiones finales
- El sistema aumenta sus capacidades, no lo reemplaza

### ORION (Rastro repo)
- **Rol**: Ecosistema principal de inteligencia
- **Responsable de**: Bug bounty intelligence, offensive security, gestión estratégica, automatización de ingresos, coordinación interna
- **Status**: Core estable, no agregar features nuevas sin justificación

### MERLIN (dentro de ORION)
- **Rol**: Copiloto estratégico interno de ORION
- **Responsable de**: Razonamiento, análisis, planificación, memoria contextual, comunicación, estrategia diaria
- **NO es un proyecto separado** — vive dentro de ORION
- **Status**: Por construir — actualmente solo existe como alias en `run.py --merlin`

### Atlas (dentro de ORION)
- **Rol**: Módulo financiero del ecosistema ORION
- **Responsable de**: Inteligencia financiera, simulaciones, estadísticas, portfolio tracking, análisis de riesgo
- **Regla**: No ejecutar acciones financieras reales sin aprobación humana
- **Status**: Base existente en `ecosystem/atlas/`, por integrar como módulo de ORION

### Revenue (dentro de ORION)
- **Rol**: Pipeline de ingresos
- **Responsable de**: Revenue pipeline, métricas, payout tracking, submission management
- **Status**: Completo en `core/revenue/`

### Hermes One (EXTERNO a ORION)
- **Rol**: Herramienta externa independiente
- **Responsable de**: Controlar PC, automatizar Windows/Linux, ejecutar comandos, administrar aplicaciones
- **NO pertenece al código de ORION**
- Puede comunicarse con ORION mediante APIs/eventos/comandos
- **Status**: Independiente en `ecosystem/hermes/`

### COPILOT (dentro de ORION)
- **Rol**: Agente senior de apoyo a decisiones de hunting
- **Status**: Estable en `core/copilot/`

### Knowledge Graph (dentro de ORION)
- **Rol**: Almacenamiento de relaciones entre entidades (21 tipos de nodo, 16 tipos de arista)
- **Status**: Estable en `core/knowledge/`

### Memory System (dentro de ORION)
- **Rol**: Almacenamiento de memoria por namespaces (10 namespaces)
- **Status**: Base en `core/memory/`, lista para evolucionar

### Command System (dentro de ORION)
- **Rol**: 107 comandos, 14 categorías, 5 niveles de permiso
- **Status**: Fase 1 completa en `core/commands/`

---

## Lo que NO debe mezclarse

| Esto | Con esto | Riesgo |
|------|----------|--------|
| ORION | Hermes | 🛑 ALTO — Hermes es externo, no debe fusionarse |
| MERLIN | Proyecto separado | 🛑 ALTO — MERLIN vive dentro de ORION |
| Atlas | ORION core | 🟡 Medio — Debe ser módulo, no fusionar lógica |
| Revenue | Atlas | 🟢 Bajo — Dominios diferentes (ingresos vs finanzas) |

---

## Estado Real

| Componente | Estado | Producción |
|------------|--------|------------|
| ORION core | ✅ Estable | Sí |
| MERLIN | ⏳ Por construir | No — solo alias |
| Atlas | 🟡 Base existente | Parcial |
| Revenue | ✅ Completo | Sí |
| COPILOT | ✅ Estable | Sí |
| Knowledge Graph | ✅ Estable | Sí |
| Memory | ✅ Base lista | Sí, para expandir |
| Command System | ✅ Fase 1 | Sí |
| Hermes (ecosystem) | ✅ Funcional | Sí — externo |
| Hermes (apps/hermes) | ⚠️ Revisar | Dentro de Rastro — evaluar si debe estar |

---

## Recomendaciones

1. **Mantener ORION congelado** — solo fixes de estabilidad
2. **No fusionar Hermes con ORION** — mantener separación estricta
3. **MERLIN se construye dentro de ORION** — no como proyecto externo
4. **Atlas se integra como módulo de ORION** — no como proyecto separado
5. **Inicializar DB principal** — `cateye.db` no tiene tablas
6. **Limpiar DBs huérfanas** — 1183 archivos, 79MB
