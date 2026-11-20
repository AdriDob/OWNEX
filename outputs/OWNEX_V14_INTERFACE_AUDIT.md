# OWENEX V14 — UNIFIED EXPERIENCE ARCHITECTURE

## Vision

OWNEX debe ser utilizable por cualquier persona sin conocer su arquitectura, tecnologías, módulos internos ni conceptos técnicos. La complejidad permanece detrás de la interfaz. Tres interfaces (Desktop + TUI + Mobile) comparten un único backend, dominio, persistencia, permisos y estado.

## Principio Fundacional

**Cualquier persona debe poder utilizar OWNEX sin conocer su arquitectura, sus tecnologías, sus módulos internos ni los conceptos técnicos que hacen funcionar el sistema.**

La complejidad debe permanecer detrás de la interfaz.

## Estado Actual V12.1 (Foundation)

### Cambios Completados V12.1:
- ✅ Upwork removido de `core/platform_connectors.py`
- ✅ Upwork removido de `core/opportunity/discovery_to_workbank.py`
- ✅ `platform_support` actualizado en `core/revenue/models.py` (sin upwork)
- ✅ Remote Job Matcher integrado en `frontend/src/pages/Discovery.vue`
- ✅ 5 tests nuevos en `tests/test_remote_job_integration.py` (5/5 passing)
- ✅ `make check`: 100 passed + typecheck

### Arquitectura Verificada:
- Un único backend FastAPI
- Una única base de datos (SQLite/PostgreSQL)
- Un único sistema de permisos
- Una sola persistencia de estado
- Adaptadores canónicos definidos y testados

## Arquitectura de Tres Interfaces

### 1. OWENEX Desktop
- Aplicación principal con toda la funcionalidad
- Interf gráfica Vue 3 + Tauri v2
- Acceso completo a todos los módulos
- Configuración y onboarding
- Ejecución de automatizaciones completas
- Gestión de agentes y conexiones

### 2. OWENEX TUI (Terminal User Interface)
- Interactiva, navegación por teclado
- No requiere memorizar comandos
- Menús, paneles, tablas, indicadores, formularios
- Tecnologías candidatas: Textual, Rich, Typer
- Mismo backend, presentación diferente
- Estados simplificados, acciones guiadas

### 3. OWENEX Mobile
- Aplicación Android (Capacitor/PWA evaluado)
- Supervisión y control remoto
- No reproduce toda la complejidad Desktop
- Enfoque en operaciones sencillas y seguras
- Notificaciones configurables
- Autenticación segura (OAuth, tokens cortos)
- Acciones remotas autorizadas

## Contrato Compartido (Unico Backend)

### Lo que COMPARTEN las tres interfaces:
- ✅ Mismo backend FastAPI
- ✅ Mismo dominio de negocio
- ✅ Misma base de datos/persistencia
- ✅ Mismo sistema de permisos
- ✅ Mismo estado de usuario
- ✅ Mismo EventBus / flujo de eventos
- ✅ Mismo conjunto de servicios (Work Bank, Discovery, Finance, etc.)
- ✅ Mismo sistema de auditoría

### Lo que NO comparten (presentación únicamente):
- ✅ Distinta UI/UX por plataforma
- ✅ Distintas restricciones de dispositivo
- ✅ Distinto nivel de detalle mostrado
- ✅ Distinto tipo de interacción (mouse/touch/teclado)
- ✅ Distinto formato de notificaciones

## Principio de Simplicidad Radical

OWNEX debe poder utilizarse sin conocer términos como:
- Adapter
- Provider
- Registry
- Scheduler
- Engine
- Orchestrator
- MCP
- API
- Repository
- Worktree
- Pipeline

### Traducciones Técnicas a Acciones:

| Término Técnico | Acción de Usuario |
|-----------------|-------------------|
| "Ejecutar discovery_to_workbank" | "Buscar oportunidades y guardarlas en tu lista de trabajo" |
| "Provider authentication failed" | "No pudimos conectar esta cuenta. Revisá el acceso e intentá nuevamente" |
| "Scheduler job blocked" | "Esta tarea no pudo comenzar porque falta una autorización" |
| "Run agent pipeline" | "Iniciar análisis" |

### Indicadores de Calidad V14:

| Indicador | Objetivo |
|-----------|----------|
| Clics para tareas frecuentes | Los mínimos posibles |
| Funciones con botones inoperantes | 0 |
| Acciones sin explicación | 0 |
| Estados técnicos incomprensibles | 0 en vistas normales |
| Datos contradictorios entre interfaces | 0 |
| Operaciones sensibles sin confirmación | 0 |
| Configuración obligatoria innecesaria | 0 |

## Fases de Implementación V14

| Fase | Enfoque | Entregable |
|------|---------|------------|
| **F0** | Auditoría de arquitectura y tecnologías | `outputs/OWNEX_V14_INTERFACE_AUDIT.md` |
| **F1** | Definición de contratos compartidos y permisos | `outputs/OWNEX_V14_SHARED_CONTRACTS.md` |
| **F2** | TUI funcional conectada al backend real | `outputs/OWNEX_V14_TUI_IMPLEMENTATION.md` |
| **F3** | Mobile dashboard de solo lectura | `outputs/OWNEX_V14_MOBILE_IMPLEMENTATION.md` |
| **F4** | Autenticación y conexiones remotas seguras | `outputs/OWNEX_V14_REMOTE_SECURITY.md` |
| **F5** | Acciones remotas autorizadas | `outputs/OWNEX_V14_REMOTE_ACTIONS.md` |
| **F6** | Notificaciones y sincronización en tiempo real | `outputs/OWNEX_V14_NOTIFICATIONS.md` |
| **F7** | Onboarding y simplificación global de UX | `outputs/OWNEX_V14_USER_GUIDE.md` |
| **F8** | Tests integrales, accesibilidad y rendimiento | `outputs/OWNEX_V14_TESTS.md` |

## No-Build Rules (Critical)

- **No crear un segundo backend** ni duplicar lógica de negocio
- **No modificar módulos compartidos sin coordinación**
- **No implementar tres versiones independientes** de: Work Bank, Opportunity Discovery, Financial Hub, Revenue Ledger, Investment Engine, Connection Framework, Scheduler, Agent Management, Notifications, Permissions
- Las operaciones deben producir resultados coherentes independientemente de la interfaz utilizada
- La tecnología debe adaptarse a las personas, no las personas a la tecnología

## Acceptance Criteria (V14 Initial)

La primera versión debe permitir:
1. Abrir OWENEX Desktop normalmente
2. Iniciar la TUI y navegar sin memorizar comandos
3. Consultar los mismos datos desde ambas interfaces (Desktop + TUI)
4. Instalar o abrir la versión móvil
5. Consultar OWENEX remotamente con autenticación segura
6. Recibir alertas importantes
7. Ejecutar acciones remotas autorizadas
8. Revocar dispositivos
9. Consultar resultados y errores
10. Utilizar las funciones principales sin conocimientos técnicos

No declarar completa una interfaz que solamente muestre datos de demostración.

## Integración con V12.1

Los cambios ya realizados en V12.1 son **compatibles y forman la base**:

- ✅ Upwork removal — ya limpio de superficies activas
- ✅ Remote Job Matcher — integración Discovery→WorkBank lista
- ✅ Tests passing — 100% con `make check`
- ✅ Typecheck — mypy sin errores
- ✅ Sin referencias a Upwork en `core/` ni `api/`

Estos cambios V12.1 son la base sobre la cual V14 construirá las tres interfaces unificadas.

## Próximos Pasos Inmediatos

1. Auditar arquitectura actual (F0)
2. Definir contratos compartidos (F1)
3. Implementar TUI conectada al backend (F2)
4. Crear dashboard móvil de solo lectura (F3)
5. Implementar autenticación segura (F4)
6. Habilitar acciones remotas autorizadas (F5)
7. Notificaciones y sincronización (F6)
8. Onboarding simplificado (F7)
9. Tests integrales (F8)

OWNEX V14: Arquitectura definida, foundation V12.1 validada, principios claros. Próximo: F0 - Auditoría.