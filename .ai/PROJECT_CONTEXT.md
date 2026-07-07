# Project Context — Rastro / CATEYE

## Descripción General

Rastro (anteriormente CATEYE) es una plataforma de bug bounty automatizada. Escanea programas de bug bounty públicos y privados, ejecuta reconocimiento pasivo y activo, genera hipótesis de vulnerabilidades, valida hallazgos, y gestiona el ciclo de vida de reportes.

## Stack Tecnológico

- **Backend**: Python 3.10+, FastAPI
- **Frontend**: Vue 3 + TypeScript + Vite (PyWebView para desktop)
- **Base de datos**: SQLite (desarrollo/desktop), con soporte para PostgreSQL
- **ORM**: SQLAlchemy + Alembic para migraciones
- **Cifrado**: `cryptography` (AES-256-GCM, Ed25519)
- **Testing**: pytest, pytest-timeout, pytest-cov
- **Linter/Formatter**: Ruff
- **Type Checker**: MyPy (strict mode parcial)
- **Desktop**: PyInstaller + PyWebView

## Estructura del Proyecto

```
Rastro/
├── .ai/                 ← Memoria permanente del proyecto (este directorio)
├── .cline/rules/        ← Reglas para Cline
├── api/                 ← FastAPI (rutas, middleware)
│   ├── main.py          ← Punto de entrada de la API
│   ├── scheduler.py     ← Planificador autónomo
│   ├── middleware/       ← Auth, CSRF, rate-limit, error handling
│   └── routers/         ← Endpoints organizados por dominio
├── cores/               ← Lógica de negocio
│   ├── auth/            ← Autenticación, sesiones, tokens
│   ├── authhub/         ← Integraciones OAuth2 (Gmail, WhatsApp, Telegram)
│   ├── bounty_scraper/  ← Scraping de plataformas bug bounty
│   ├── crypto/          ← Integraciones crypto (EVM, BTC, Solana, Tron)
│   ├── discovery/       ← Descubrimiento de programas y endpoints
│   ├── engine/          ← Motor de scoring, ROI, hipótesis
│   ├── financial/       ← Pagos y finanzas
│   ├── health/          ← Sistema de salud (métricas, scoring)
│   ├── intelligence/    ← Aprendizaje por refuerzo, priorización
│   ├── knowledge/       ← Base de conocimiento con dedup por fingerprint
│   ├── license/         ← Sistema de licencias (Ed25519)
│   ├── orchestrator/    ← Orquestación de scans, pipeline
│   ├── recovery/        ← Circuit breakers, recuperación, persistencia
│   ├── analysis/        ← Análisis de hallazgos, detección de duplicados
│   ├── audit_log.py     ← Auditoría persistente de eventos de seguridad
│   ├── dedup.py         ← Tracker de dedup unificado
│   ├── identity_vault.py ← Bóveda cifrada de credenciales
│   └── vault_crypto.py  ← Utilidad de cifrado compartida
├── database/            ← Modelos SQLAlchemy, sesiones DB
├── desktop/             ← Aplicación de escritorio
├── frontend/            ← Interfaz de usuario Vue 3
├── tests/               ← Tests (355 tests, 2 xfailed)
└── scripts/             ← Scripts de build, instalación, release
```

## Estado Actual

- Versión: 2.0 (post-audit)
- Tests: 355 pasan, 2 xfailed (test de rate limit preexistente)
- Lint: Ruff limpio
- Seguridad: 8 vulnerabilidades críticas resueltas (ver SECURITY_POLICY.md)
- Cobertura de CI: pytest + ruff en GitHub Actions

## Convenciones

- **Idioma**: Código en inglés. Documentación operativa en español.
- **Imports**: Usar `from __future__ import annotations` en archivos Python.
- **Tipos**: Anotaciones de tipo en todas las funciones públicas.
- **Logging**: Usar `logger = logging.getLogger("catseye.<modulo>")`.
- **Tests**: Ubicados en `tests/`, usando pytest.
- **Commits**: Prefijo convencional (feat:, fix:, security:, refactor:, docs:).
