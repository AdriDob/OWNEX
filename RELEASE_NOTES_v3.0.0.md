# RELEASE NOTES — CATEYE v3.0.0 STABLE

> Fecha: Julio 2026
> Versión: 3.0.0
> Arquitectura: v3.0 STABLE
> Estado: ✅ LISTA PARA USO DIARIO

---

## Resumen

CATEYE v3.0.0 es la primera versión estable para uso diario en bug bounty. Marca el fin del ciclo de desarrollo intensivo y el comienzo del uso real en programas de bug bounty.

**Filosofía**: Esta versión no agrega features nuevas. Estabiliza, corrige bugs, y documenta lo que ya existe.

---

## Novedades respecto a v2.0.0

### Estabilidad

- **393 tests pasan** (antes 359, se agregaron tests de seguridad)
- `test_security.py` ahora incluido en el suite (34 tests, todos verdes)
- CSRF middleware verificado con tests HTTP reales via TestClient
- Rate limit middleware con tests de integración HTTP

### Correcciones

| Bug | Fix |
|---|---|
| 3 tests CSRF fallaban | Reescribir tests con TestClient real. Middleware intacto. |
| HealthSystems contradictorios | Solo `SystemHealthEngine` publica eventos al EventBus. `HealthMonitor` solo alimenta `RecoveryEngine`. |
| Memory threshold 60% vs 80% | Unificado a 80% en `SystemHealthEngine`. |
| Rate limit middleware sin tests | 3 tests HTTP nuevos. |
| Sin versión en código | `VERSION` → 3.0.0, `pyproject.toml` con `[project] version`. |

### Documentación

| Documento | Descripción |
|---|---|
| `FUNCTIONAL_SPEC.md` | Capacidades verificadas del sistema (988 líneas, actualizado a v3.0.0) |
| `USER_GUIDE.md` | Manual práctico en español para uso diario |
| `DAILY_WORKFLOW.md` | Rutina diaria, semanal, mensual |
| `RELEASE_NOTES_v3.0.0.md` | Este documento |

---

## Qué es estable

- ✅ Pipeline E2E completo (DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT)
- ✅ ORION con priorización, contexto, aprendizaje y control de scheduler
- ✅ EventBus persistente en SQLite
- ✅ Scheduler adaptativo con cooldown y priorización
- ✅ 5-stage pipeline automático
- ✅ Auto-report (finding confirmado → borrador)
- ✅ Discovery automático (6 fuentes + web scan)
- ✅ Recon con 10 herramientas (3 modos: FAST / DEEP / API)
- ✅ 8 generadores de hipótesis rule-based
- ✅ Validación con RequestReplayer + LLM
- ✅ Reportes con 4 formatos de exportación
- ✅ Tracking financiero con TruthLayer
- ✅ 4 conectores blockchain (BTC, ETH, SOL, TRX)
- ✅ Auth con JWT + session store cifrado
- ✅ CSRF middleware (double-submit cookie)
- ✅ Rate limiting por identity
- ✅ Audit log persistente
- ✅ Identity Vault (AES-256-GCM)
- ✅ License Ed25519
- ✅ Frontend Vue 3 + TypeScript (57 páginas)
- ✅ Build Linux vía PyInstaller

---

## Limitaciones conocidas

| Limitación | Detalle |
|---|---|
| Single-user | No soporta múltiples usuarios ni SaaS |
| Local-first | Requiere ejecución local, no es cloud |
| Dependencia de herramientas externas | subfinder, httpx, katana, etc. deben instalarse por separado |
| Las oportunidades en RAM se pierden al reiniciar | Deben regenerarse vía `opportunity:refresh` |
| Algunas herramientas (crtsh) requieren aiohttp | No instalado por defecto |

---

## Trabajo diferido a v3.1

| Feature | Motivo del deferimiento |
|---|---|
| `UnifiedHealthMonitor` | Refactor completo. El fix mínimo (solo SystemHealthEngine publica) es suficiente. |
| `DuplicateDetector` → `DedupTracker` | No bloquea uso diario. |
| Frontend API keys → IdentityVault | No bloquea, evaluar en uso real. |
| Frontend dependency audit | No bloquea. |
| Pre-commit hooks | No bloquea. |
| Windows/macOS builds | Agregar cuando el pipeline de releases lo justifique. |

---

## Breaking changes

**Ninguno.** v3.0.0 es 100% retrocompatible con v2.0.0. No se modificaron interfaces públicas, rutas de API, ni esquemas de base de datos.

---

## Tests

```bash
# Suite completo
pytest --timeout=60
→ 393 passed, 2 xfailed

# Sin test_security.py (misma suite que v2.0.0)
pytest --timeout=60 --ignore=tests/test_security.py
→ 359 passed, 2 xfailed

# Lint
ruff check .
→ Sin errores
```

---

## Instalación

```bash
# Linux
git clone <repo>
cd rastro
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
python run.py --setup

# Seed data (opcional)
python scripts/seed_real.py

# Iniciar
python run.py --browser
```

Ver `USER_GUIDE.md` para instrucciones detalladas.

---

## Build Linux

```bash
scripts/build_linux.sh
→ dist/CATEYE/CATEYE

desktop/build/install_linux.sh --user
→ Instalado en ~/.local/bin/CATEYE
```

---

## Créditos

CATEYE es un sistema de inteligencia operativa privada para bug bounty.
Hecho en 🇦🇷.
