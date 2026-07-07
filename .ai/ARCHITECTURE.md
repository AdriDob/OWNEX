# Architecture — Rastro / CATEYE

## Visión General

El sistema sigue una arquitectura de núcleo modular con API REST, frontend SPA, y planificador autónomo. Los módulos de `cores/` contienen toda la lógica de negocio y se comunican a través de llamadas directas (singletons) y un bus de eventos ligero.

## Flujo de Datos Principal

```
Frontend (Vue 3)
    │
    ▼ HTTP/JSON
API (FastAPI) ─── middleware: [CSRF → RateLimit → Auth → ErrorHandler]
    │
    ├── Routers: auth, license, platforms, targets, scans, findings, reports, settings, system
    │
    ▼
cores/
    ├── auth/         → AuthManager → SessionStore + TokenService
    ├── license/      → LicenseValidator (Ed25519) + LicenseStore
    ├── identity_vault/ → Bóveda cifrada AES-256-GCM
    ├── bounty_scraper/  → BountyScraper → Target
    ├── orchestrator/ → ScanService → ReconRunner → Pipeline
    ├── intelligence/ → RewardLearner, PriorityEngine
    ├── analysis/     → DuplicateDetector, NoiseReduction, InvestigationGraph
    └── recovery/     → CircuitBreaker, HealthMonitor, RecoveryStore (SQLite)
    │
    ▼
database/ (SQLAlchemy → SQLite/PostgreSQL)
```

## Módulos Principales

### API (`api/`)
- FastAPI con middleware en cadena
- Autenticación por token JWT-signed + device binding
- Rate limiting por identity (device_id o IP)
- CSRF por double-submit cookie

### Núcleo (`cores/`)
- **auth/**: AuthManager facade sobre SessionStore + TokenService. Todo cifrado en disco.
- **license/**: Validación Ed25519. Clave pública embebida. Formato 25 caracteres.
- **identity_vault/**: Credenciales cifradas con AES-256-GCM. Clave aleatoria en disco (chmod 600).
- **bounty_scraper/**: Scraping multi-plataforma con dedup propio + DB-level dedup.
- **orchestrator/**: ScanService (single-shot), Pipeline (coordinador de agentes).
- **recovery/**: Circuit breakers con persistencia SQLite, health monitoring.
- **intelligence/**: RewardLearner con ajustes persistidos, PriorityEngine.
- **knowledge/**: Base de conocimiento con fingerprint SHA-256 + upsert.
- **dedup.py**: DedupTracker unificado con fingerprints normalizados.

### Planificador Autónomo (`api/scheduler.py`)
- 6 etapas: discover → recon → hypothesis → scope_check → validate → report
- Intervalos configurables por etapa
- Per-target cooldown (1 hora)
- Priorización por RewardLearner adjustments
- Cooldown evita re-escanear targets recién procesados

### Frontend (`frontend/`)
- Vue 3 + TypeScript + Pinia + Vite
- API keys separadas en sessionStorage (no localStorage)
- Comunicación con backend via HTTP API

## Patrones Arquitectónicos

- **Singleton con lazy initialization**: `get_*()` functions (get_auth_manager, get_identity_vault, etc.)
- **Middleware pipeline**: Starlette BaseHTTPMiddleware en cadena
- **Strategy**: OAuth2Provider abstracto para cada plataforma
- **Circuit Breaker**: Per-component, con persistencia
- **Dedup por fingerprint**: SHA-256 de campos normalizados

## Config Compiler (Diseño Conceptual — NO IMPLEMENTAR)

### Problema
Cada agente/herramienta (OpenCode, Cline, Copilot) requiere configuración en formatos distintos. Mantenerlas sincronizadas manualmente crea duplicación y desviación.

### Solución Propuesta
Un **config compiler** que lee `.ai/` como fuente de verdad única y genera configuraciones para cada herramienta:

```
.ai/ (source of truth)
  ├── AGENT_CHARTER.md     → reglas universales
  ├── PRODUCTION_RULES.md  → reglas de producción
  ├── CODE_QUALITY.md      → estándares de calidad
  ├── TESTING_POLICY.md    → política de tests
  └── CONFIG_TEMPLATES/    → (futuro) templates por herramienta
        ↓
   Config Compiler (futuro script)
        ↓
  ├── opencode.json        → instrucciones + skills
  ├── .cline/rules/        → reglas específicas
  └── ... (otros formatos)
```

### Reglas de Diseño
- **NUNCA** editar configuraciones generadas manualmente
- **SIEMPRE** editar `.ai/` y regenerar
- El compiler debe ser **determinístico** (mismo input → mismo output)
- Debe validar que todas las referencias existen antes de generar
- Debe preservar formato específico de cada herramienta sin perder información

### NO Implementar Hasta
- [ ] Haya al menos 3 herramientas con configuraciones distintas
- [ ] Se detecte desviación confirmada entre configs
- [ ] El mantenimiento manual sea un problema documentado

### Alternativa Descartada
Mantener un archivo de configuración centralizado (YAML/JSON) y generar desde ahí. Se descartó porque agrega otra capa de abstracción sin eliminar el problema raíz: la fuente de verdad debe ser `.ai/` en markdown legible por humanos y agentes.

## Puntos de Integración Críticos

| Punto | Módulos | Propósito |
|---|---|---|
| IdentityVault → TokenService | `cores/identity_vault` → `cores/auth/token_service` | Cifrado de tokens |
| IdentityVault → SessionStore | `cores/identity_vault` → `cores/auth/session` | Cifrado de sesiones |
| AuthHub → IdentityVault | `cores/authhub/` → `cores/identity_vault` | Almacenamiento OAuth2 |
| License → Store | `cores/license/validator` → `cores/license/store` | Persistencia de licencia |
| Scheduler → ScanService | `api/scheduler` → `cores/orchestrator/scan_service` | Lanzamiento de scans |
| Scheduler → RewardLearner | `api/scheduler` → `cores/intelligence/reward_learning` | Priorización de targets |
| CircuitBreaker → RecoveryStore | `cores/recovery/circuit_breaker` → `cores/recovery/persistence` | Persistencia de estado |
| RewardLearner → RecoveryStore | `cores/intelligence/reward_learning` → `cores/recovery/persistence` | Persistencia de ajustes |
