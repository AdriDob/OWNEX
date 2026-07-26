# Personal Intelligence OS — Roadmap

> Design document. No implementation yet.

## Visión

Un sistema que Adriel pueda usar durante años, que aumente su capacidad de tomar mejores decisiones y acelere su camino hacia independencia financiera.

## Arquitectura Oficial

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
           |                |                |
           └────────────────┼────────────────┘
                            |
                    Integraciones
              EventBus / Knowledge Graph / Memory
                            |
                     Hermes One (EXTERNO)
                   Control y automatización del PC
```

## Fases de Evolución

### FASE 0 — Ecosystem Audit (completada ✅)
- Mapa completo de componentes
- Documentación de límites
- Deuda técnica identificada
- **Arquitectura corregida**

### FASE 1 — Memory Engine
**Objetivo**: MERLIN recuerda todo lo útil

Tres capas:

| Capa | Alcance | Almacenamiento | Expiración |
|------|---------|----------------|------------|
| Working | Sesión actual, tareas activas | RAM | Sesión |
| Long Term | Preferencias, historial, patrones | SQLite | Indefinido |
| Strategic | Objetivos, visión, decisiones clave | SQLite + export | Permanente |

**Qué existe**: `core/memory/` — store por namespaces, CRUD, tags, prioridad, expiración
**Qué falta**: Memoria working, memoria strategic, promoción automática entre capas

### FASE 2 — MERLIN Evolution
**Objetivo**: De alias a inteligencia estratégica real

- Identidad real como módulo de ORION
- Generación de Daily Brief
- Automatización de Weekly Review
- Reality Engine (pesimista/probable/optimista)

**Límites**:
- MERLIN razona y recomienda
- MERLIN NO ejecuta
- MERLIN NO mueve dinero
- MERLIN vive dentro de ORION

### FASE 3 — Mission Control
**Objetivo**: Visualización centralizada

- Salud del sistema
- Progreso financiero
- Misiones activas
- Oportunidades
- Alertas

**Principio**: CLI primero, TUI segundo, web tercero

### FASE 4 — Wealth Intelligence
**Objetivo**: Simular antes de actuar

- Scenario engine (what-if)
- Reality Check (proyecciones honestas)
- Expected Revenue por target/vuln/programa
- Simulaciones realistas con escenarios pesimista/probable/optimista

### FASE 5 — Security & Self-Improvement
**Objetivo**: El sistema mejora dentro de límites seguros

**Puede hacer**:
- Aprender preferencias
- Mejorar recomendaciones
- Detectar patrones
- Sugerir mejoras

**No puede hacer**:
- Cambiar arquitectura
- Instalar software crítico
- Mover dinero
- Modificar seguridad

## Orden de Implementación

| Prioridad | Fase | Dependencias | Esfuerzo |
|-----------|------|-------------|----------|
| 0 | Audit | None | ✅ Hecho |
| 1 | Memory Engine | `core/memory/` existente | Medio |
| 2 | MERLIN Evolution | Memory Engine | Grande |
| 3 | Mission Control | MERLIN | Medio |
| 4 | Wealth Intelligence | Atlas, Revenue Pipeline | Grande |
| 5 | Security & Self-Improvement | Todo lo anterior | Continuo |

## Reglas

1. **Nunca asumir éxito** — toda proyección debe incluir escenarios pesimista/probable/optimista
2. **Authority Layer** — el sistema analiza, simula, recomienda, pero nunca ejecuta sin aprobación
3. **Límites estrictos** — ORION (ecosistema), MERLIN (inteligencia dentro de ORION), Atlas (finanzas dentro de ORION), Hermes (externo)
4. **Estabilidad > Features** — no crear nuevo módulo hasta que los existentes estén endurecidos
5. **Memoria antes que inteligencia** — MERLIN necesita recordar antes de poder razonar
6. **Hermes es externo** — no fusionar, solo integrar vía APIs/eventos
