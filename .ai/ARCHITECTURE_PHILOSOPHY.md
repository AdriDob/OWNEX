# ORION Platform — Filosofía Arquitectónica

> **Este documento NO describe la estructura del código.**
> Describe los principios que nunca deben romperse.
> Es más estable que cualquier RFC técnico.

---

## Los 10 Mandamientos

### 1. ORION es un monolito modular
Un solo proceso. Un solo equipo. Cero microservicios.
Los módulos se separan por carpetas, no por procesos.

### 2. Las apps son independientes
Cada app tiene su DB, su API, su scheduler, sus agentes.
Cero imports cruzados entre `apps/*/`.
Si dos apps necesitan comunicarse, usan el EventBus.

### 3. El Core nunca depende de una app
`core/` no importa `apps/`. No sabe qué apps existen hasta que
se registran via `AppRegistry`. El Core es infraestructura pura.

### 4. Toda comunicación entre apps pasa por eventos
Nunca una app llama a otra app directamente.
`EventBus.publish("app:event")` es la únca vía.
El receptor decide si reacciona.

### 5. El estado crítico siempre es persistente
Nada importante vive solo en RAM. Si el proceso muere,
los eventos, decisiones, y configuraciones sobreviven en SQLite.

### 6. La IA razona antes de ejecutar
Los agentes proponen acciones. El `DecisionEngine` las evalúa.
Si hay riesgo, pide confirmación humana.
Nunca una decisión irreversible se ejecuta sin supervisión.

### 7. La automatización nunca decide por sí sola
`AutomationEngine` ejecuta. No piensa.
Retry, timeout, logging, error handling.
Pero nunca decide qué hacer ni cuándo.

### 8. CATEYE investiga como un científico
Hipótesis → Auto-refutación → Explicaciones alternativas →
Experimentos → Evidencia → Confianza → Reporte → Aprendizaje.
No es un scanner. Es un investigador.

### 9. Toda integración externa es opcional
El sistema funciona con AI provider + SQLite.
Shodan, Binance, Polymarket, etc. son aceleradores, no dependencias.
Nunca una API externa bloquea el startup.

### 10. El conocimiento se comparte, el estado se aísla
La memoria global es compartida entre apps.
Las bases de datos son privadas por app.
Los eventos son públicos. Los datos son privados.

---

## Reglas de oro

| Situación | Respuesta |
|---|---|
| ¿App A necesita datos de App B? | `EventBus` o `HTTP localhost` |
| ¿App A y App B comparten lógica? | Extraer a `core/domain/` |
| ¿Sabemos que en el futuro necesitaremos X? | Reservar espacio, no implementar |
| ¿Duda entre simplicidad y flexibilidad? | Elegir simplicidad. Siempre. |
| ¿Duda entre código nuevo y refactor? | Escribir código nuevo. No refactorizar estable. |
| ¿CATEYE necesita un cambio? | NO. Envolverlo, no modificarlo. |

---

## Definiciones

| Término | Significado |
|---|---|
| **Core** | Infraestructura compartida. No contiene lógica de negocio. |
| **Domain** | Lógica de negocio reutilizable (futuro: `core/domain/`). |
| **App** | Producto de negocio con valor para el usuario. |
| **Provider** | Integración externa (opcional, conectable via connector). |
| **Agent** | Entidad de IA que razona y decide en un dominio. |
| **Automation** | Ejecución mecánica sin razonamiento (retry, timeout, logs). |
| **EventBus** | Único canal de comunicación inter-app. |
| **Decision Journal** | Registro inmutable de todo razonamiento del sistema. |
| **Hermes Agent** | Herramienta externa (Nous Research) para automatización transversal. |

---

## Lo que ORION no es

ORION **no** es:
- Una plataforma SaaS
- Un sistema multi-empresa
- Un reemplazo de CATEYE
- Un bot de trading automático
- Un framework genérico de agentes
- Un producto para vender

ORION **sí** es:
- Una plataforma personal local-first
- Un orquestador de herramientas de productividad
- Un asistente de investigación semiautónomo
- Un gestor de riesgo y patrimonio
- Un sistema que aprende con el uso

---

> "Si un principio no se puede explicar en una línea,
> probablemente sea demasiado complejo."
