# GUÍA DE USUARIO — CATEYE

**Sistema de Inteligencia Económica para Bug Bounty**

Versión: 1.8.0 | Stack: Python 3.10+ · FastAPI · Vue 3 · SQLite/PostgreSQL

---

## Índice

1. [Introducción](#1-introducción)
2. [Instalación](#2-instalación)
3. [Primeros Pasos](#3-primeros-pasos)
4. [Flujo de Trabajo Diario](#4-flujo-de-trabajo-diario)
5. [Money Radar — Priorización Económica](#5-money-radar--priorización-económica)
6. [Radar de Oportunidades](#6-radar-de-oportunidades)
7. [Pipeline de Validación](#7-pipeline-de-validación)
8. [Reportes y Envíos](#8-reportes-y-envíos)
9. [Sistema Financiero](#9-sistema-financiero)
10. [Money-Impact Modules (v1.7.2)](#10-money-impact-modules-v172)
11. [Scripts de Automatización](#11-scripts-de-automatización)
12. [Conexiones y Plataformas](#12-conexiones-y-plataformas)
13. [Configuración](#13-configuración)
14. [Solución de Problemas](#14-solución-de-problemas)
15. [Referencia Rápida](#15-referencia-rápida)

---

## 1. Introducción

### 1.1 Qué es CATEYE

CATEYE es un sistema de inteligencia artificial que automatiza el ciclo completo de bug bounty: **descubrir programas → analizar targets → validar vulnerabilidades → generar reportes → tracking de cobros**.

No es un escáner. Es un **sistema de decisión económica** que te dice dónde, cuándo y cómo invertir tu tiempo de investigación para maximizar ingresos reales.

### 1.2 Filosofía

| Principio | Significado |
|-----------|-------------|
| Automatización progresiva | Opera en segundo plano, intervenís cuando importa |
| Inteligencia económica | Cada recomendación tiene un número: EVH, ORION Score, ROI |
| Privacidad primero | Datos y credenciales encriptados localmente |
| Degradación elegante | Si algo falla, el resto sigue funcionando |
| Sin humo | No inventa datos. Lo que no sabe, lo marca como desconocido |

### 1.3 Puertos y Acceso

```
Frontend:   http://localhost:5173   (desarrollo)
API:        http://localhost:8000
Docs API:   http://localhost:8000/docs
```

---

## 2. Instalación

### 2.1 Local (desarrollo)

```bash
git clone <repo>
cd CATEYE

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Configuración
cp .env.example .env
# Editar .env con tu configuración (ver sección 13)

# Iniciar
python run.py
```

### 2.2 Dependencias externas (opcionales)

```bash
# Escáneres (mejoran detección pero no son obligatorios)
chmod +x scripts/install_tools.sh
./scripts/install_tools.sh
```

### 2.3 AI local (Ollama)

```bash
# Instalar Ollama: https://ollama.ai
ollama pull llama3.2:3b  # mínimo recomendado
ollama pull mistral:7b   # mejor calidad

# Configurar en .env:
OLLAMA_HOST=http://localhost:11434
```

---

## 3. Primeros Pasos

### 3.1 Inicio del sistema

```bash
python run.py              # modo browser (full stack)
python run.py --browser    # idem
python run.py --tray       # solo bandeja (backend en background)
```

El sistema arranca con una máquina de estados que **nunca crashea**: si algo falla, degrada a modo seguro y abre el navegador.

### 3.2 Pantalla de login

La primera vez, el sistema puede pedir activación de licencia (depende de la configuración). En modo local, genera un token automático.

### 3.3 Dashboard principal (`/`)

La home responde 5 preguntas en <20 segundos:

| Pregunta | Lo ves en |
|----------|-----------|
| ¿Cuánto dinero tengo? | KPIs de earnings totales, pendientes, cobrados |
| ¿Cuánto puedo cobrar? | Pipeline de findings con estimación |
| ¿Dónde está el mejor dinero? | Money Radar con ORION Score |
| ¿Qué hago ahora? | Next Action card |
| ¿Cuánto tiempo invertir? | EVH por programa |

### 3.4 Navegación principal

```
/mission-control      → Panel de control principal
/money-radar          → Programas rankeados por ORION Score
/radar                → Oportunidades por EVH
/bounties             → Bounties activos
/findings             → Hallazgos pendientes
/reports              → Reportes generados
/connections          → Conexiones con plataformas
/wallets              → Gestión de billeteras y cobros
/settings             → Configuración del sistema
```

---

## 4. Flujo de Trabajo Diario

### 4.1 Mañana (<5 min)

```
1. Abrí CATEYE → python run.py
2. Mirá el Dashboard → ¿qué cambió desde ayer?
3. Revisá Money Radar → ¿hay nuevos programas mejor rankeados?
4. Checkeá Next Action → ¿qué recomienda el sistema?
5. Revisá Report Queue → ¿hay reportes listos para submit?
```

### 4.2 Investigación (1-4 h)

```
1. Elegí un target del Money Radar (top 3 por EVH)
2. Usá el plan de misión → /programs/:id/plan
3. Seguí los endpoints recomendados
4. Validá findings con el pipeline
5. Generá reporte con PoC Engine
6. Optimizá con Feedback Engine antes de submit
```

### 4.3 Cierre (<5 min)

```
1. Marcá findings como enviados / aceptados / rechazados
2. Revisá earnings synced → /wallets
3. Checkeá próximos cobros → /connections/withdrawals
4. Cerrá sesión → el sistema guarda todo automáticamente
```

---

## 5. Money Radar — Priorización Económica

### 5.1 Qué es

El Money Radar (`/money-radar`) rankea todos los programas activos por **ORION Score** (0.0–1.0). Este score combina:

| Factor | Peso | Qué mide |
|--------|------|----------|
| Potencial de recompensa | 30% | Historial de pagos del programa |
| Éxito histórico | 20% | Findings aceptados previamente |
| Competencia | 15% | Cuántos investigadores activos |
| Eficiencia temporal | 15% | Payout por hora estimado |
| Experiencia previa | 10% | Tecnologías que ya conocés |
| Diversidad tecnológica | 10% | Stack moderno = más oportunidades |

### 5.2 Cómo usarlo

```text
ORION 0.82 → 🔥 prioritize
ORION 0.55 → 👀 consider
ORION 0.30 → 💀 skip
```

1. Ordená por ORION Score descendente
2. Examiná los top 10
3. Click en un programa para ver su **Plan de Misión**
4. El plan te dice: por dónde empezar, qué endpoints revisar, tiempo estimado, EVH

### 5.3 Target Radar (v1.7.2)

El Target Radar refina el Money Radar con **Expected Value (EV)**:

```
EV = P(bug) × payout_avg × exploit_ease
```

Cada target recibe:
- 🔥 **Hot** → EV ≥ 0.4 (priorizar)
- 👀 **Cold** → EV entre 0.15 y 0.4 (considerar)
- 💀 **Waste** → EV < 0.15 (no perder tiempo)

Accedé via API:
```bash
curl http://localhost:8000/api/economic/money-radar
```

---

## 6. Radar de Oportunidades

### 6.1 Opportunity Radar (`/radar`)

Lista todas las oportunidades disponibles rankeadas por EVH (Expected Value per Hour).

Cada oportunidad muestra:
- **EVH** → valor esperado por hora
- **Payout estimado** → rango de recompensa posible
- **Probabilidad de éxito** → basada en datos históricos
- **Esfuerzo estimado** → horas hasta encontrar algo

### 6.2 Categorías

| Categoría | Cómo identificarla |
|-----------|-------------------|
| Independiente | Programas propios, menor competencia |
| Web3 | Alto riesgo, alto payout potencial |
| Plataforma | HackerOne, Bugcrowd, etc. |
| Emergente | Nuevos, poca data, oportunidad temprana |
| Research | Investigación abierta, sin programa formal |

### 6.3 Fast ROI y Low Competition

El sistema genera listas inteligentes:
- **Fast ROI** → alta recompensa + poca competencia
- **Low Competition** → programas con poca actividad de otros investigadores
- **Long Term** → programas estables para inversión a largo plazo

---

## 7. Pipeline de Validación

### 7.1 Ciclo de validación

```
Endpoint descubierto → Hipótesis → Prueba → Comparación → Veredicto → Hallazgo
```

### 7.2 Modos de escaneo

| Modo | Velocidad | Profundidad | Cuándo usarlo |
|------|-----------|-------------|---------------|
| **Lightning** ⚡ | Segundos | Superficial | Primera pasada, buscar low-hanging fruit |
| **Normal** | Minutos | Media | Investigación estándar |
| **Deep** | Horas | Completa | Targets de alto valor |

### 7.3 Lightning Scanner (v1.7.2)

Escaneo rápido enfocado en bugs de alto ROI:

```bash
# Desde la API:
POST /api/scan/lightning
{"target_url": "https://ejemplo.com/api", "check_auth_bypass": true, "check_idor": true}
```

Detecta en segundos:
- **Auth bypass** → endpoints accesibles sin credenciales
- **IDOR directos** → IDs secuenciales en parámetros
- **Misconfiguraciones** → `.env`, `/admin`, `/debug` expuestos
- **Logic flaws** → parámetros tamperables

### 7.4 Duplicate Detector (v1.7.2)

Antes de escribir un reporte, compará tu finding contra el historial:

```python
from cores.analysis.duplicate_detector import DuplicateDetector

dd = DuplicateDetector()
dd.load_history(findings_historial)
assessment = dd.assess(mi_finding)
# assessment.risk → 0.72 → no enviar
# assessment.verdict → "high" / "medium" / "low"
```

---

## 8. Reportes y Envíos

### 8.1 Generación de reportes

CATEYE tiene dos formas de generar reportes:

**1. PoC Engine (v1.7.2)** — genera cadenas curl listas para submit:

```python
from cores.exploit.poc_engine import PoCEngine

poc = PoCEngine()
output = poc.generate(finding)
# output.curl_chain → ["curl -X GET '...'", "curl -X POST '...'"]
# output.steps → [Paso 1: baseline, Paso 2: ataque, ...]
# output.ready_for_submit → True/False
```

**2. Report Engine** — formato estructurado completo:

| Campo | Descripción |
|-------|-------------|
| Título | Claro y descriptivo |
| Vulnerabilidad | Clase CWE |
| Severidad | Critical / High / Medium / Low / Info |
| Impacto | Qué puede hacer un atacante |
| Reproducción | Pasos exactos para replicar |
| PoC | Curl commands o video |
| Evidencia | Screenshots, request/response |
| Mitigación | Cómo arreglarlo |

### 8.2 Acceptance Optimizer (Feedback Engine, v1.7.2)

**Antes de enviar** cualquier reporte, ejecutá el Feedback Engine:

```python
from cores.validation.feedback_engine import FeedbackEngine

fe = FeedbackEngine()
feedback = fe.analyze(finding)

print(feedback.triager_perspective)
# → "A triager would likely reject or mark as needs-more-info:"
# → "  - Reproduction steps too short or missing"
# → "  - Business impact not clearly articulated"

print(feedback.priority_fixes)
# → ["IMPROVE: Report quality below threshold — do not submit as-is",
#     "Simplify reproduction to ≤3 curl commands",
#     "Add a concrete business impact scenario"]
```

Si `feedback.acceptance_probability < 0.65`, **no enviés**. Mejorá el reporte primero.

### 8.3 Formato de salida

CATEYE exporta reportes en:
- **JSON** → integración programática
- **Markdown** → lectura directa
- **Plantillas por programa** → adaptadas a cada plataforma

---

## 9. Sistema Financiero

### 9.1 Financial Truth Layer

El Financial Truth Layer (v1.8.0) provee una fuente única de verdad para todos los ingresos del bug bounty. Se accede via `/financial-truth` en la UI o `/api/financial/*` en la API.

Clasifica cada valor en una de 5 categorías:

| Categoría | Descripción | Confianza |
|-----------|-------------|-----------|
| `VERIFIED_REAL` | Pagos confirmados por API de plataforma o blockchain | 1.0 |
| `PENDING` | Reportes aceptados no pagados aún | 0.7–1.0 |
| `ESTIMATED` | Estimaciones basadas en promedios históricos | 0.3–0.5 |
| `MANUAL` | Ingresos cargados manualmente por el usuario | 0.6 |
| `UNKNOWN` | Sin fuente de datos disponible | 0.0 |

**Dashboard:** 6 KPI cards (verified/pending/withdrawn/estimated/manual/disputed), barra proporcional, pestañas de Resumen, Plataformas, Retiros y Reconciliación.

### 9.2 Wallet y retiros (WithdrawalTracker)

`/financial-truth` (pestaña Retiros) gestiona el ciclo completo de retiros:

| Estado | Descripción |
|--------|-------------|
| `initiated` | Retiro solicitado |
| `pending` | En proceso de confirmación |
| `completed` | Confirmado por API o manualmente |
| `failed` | Rechazado o cancelado |

Cada retiro puede confirmarse via:
- `API_VERIFIED` — confirmación automática por API de plataforma
- `MANUAL_PROOF` — confirmación manual con evidencia adjunta
- `RECONCILIATION` — coincidencia contra ledger automática
- `UNCONFIRMED` — sin confirmación aún

### 9.3 Crypto Wallets

`/accounts-hub` → monitoreo unificado de billeteras crypto:

| Conector | Fuente | Soporta |
|----------|--------|---------|
| EVMConnector | RPC (Infura/Alchemy) + Explorer API | Ethereum, Polygon, BSC, Arbitrum, Optimism |
| ExchangeConnector | REST API firmada HMAC | Binance, Coinbase, Kraken, Bybit |

Cada wallet muestra balance en USD, último sync, y estado de conexión (CONNECTED/DEGRADED/ERROR/UNKNOWN). Los balances se obtienen on-chain, nunca se asumen.

### 9.4 SyncPipeline

El SyncPipeline orquesta la sincronización automática de todas las fuentes:
- **Rate limiting** token-bucket por plataforma
- **Cache** con TTL configurable por tipo de dato
- **Retry** con backoff exponencial (hasta 5 intentos)
- **Delta detection** — clasifica cada entrada como NEW / UPDATED / REMOVED

### 9.5 ReconciliationEngine

Compara automáticamente los datos externos (API de plataforma + blockchain) contra el ledger interno:

| Discrepancia | Acción |
|--------------|--------|
| `MISSING_PAYOUT` | Flaggea en disputa para revisión manual |
| `ORPHAN_ENTRY` | Entrada en ledger sin correspondencia externa |
| `AMOUNT_MISMATCH` | Diferencia de monto entre fuente y ledger |
| `UNKNOWN_SOURCE` | Entrada sin fuente identificable |

Discrepancias con confianza ≥ 0.9 se resuelven automáticamente.

### 9.6 ROI tracking

Cada sesión de investigación registra:
- Tiempo invertido
- Findings encontrados
- Reportes enviados
- Aceptados / rechazados
- Pago recibido

Esto alimenta el **MoneyRadar** (EV = P(acceptance) × real_payout_history × exploit_ease) y mejora predicciones futuras.

---

## 10. Money-Impact Modules (v1.7.2)

Esta versión agrega 5 módulos diseñados específicamente para **aumentar ingresos reales**:

### 10.1 TargetRadar

Ordena targets por Expected Value: `EV = P(bug) × payout × exploit_ease`

```
🔥 Top: ejemplo.com (EV 0.72)
💀 Skip: otro-ejemplo.com (EV 0.08)
```

**Ubicación:** `cores/targeting/radar.py`

### 10.2 LightningScanner

Escaneo superficial en segundos. Busca solo bugs de alto ROI:

| Bug class | Tiempo estimado |
|-----------|-----------------|
| Auth bypass | 5 min |
| IDOR directo | 10 min |
| Misconfiguration | 5 min |
| Logic flaw | 10-15 min |

**Ubicación:** `cores/scanning/lightning.py`

### 10.3 DuplicateDetector

Compara tu finding contra el historial. Si `risk > 0.7`, no lo enviés.

**Ubicación:** `cores/analysis/duplicate_detector.py`

### 10.4 FeedbackEngine

Simula la revisión del triager antes de enviar:

```text
Acceptance probability: 42%
BLOCKER: Probable out-of-scope finding — verify before proceeding
Fix: Add missing evidence: Screenshots of the vulnerability
Fix: Simplify reproduction to ≤3 curl commands
```

**Ubicación:** `cores/validation/feedback_engine.py`

### 10.5 PoCEngine

Genera cadenas curl completas con impacto demostrado.

**Ubicación:** `cores/exploit/poc_engine.py`

---

## 11. Scripts de Automatización

### 11.1 CLI integrado

```bash
# Diario
cateye daily start      → inicia sesión, recomienda targets
cateye daily end        → cierra sesión, resume earnings

# Targets
cateye recon <target>   → reconocimiento completo
cateye analyze <target> → análisis de superficie
cateye surface <target> → mapeo de ataque

# Validación
cateye validate idor    → test de IDOR
cateye validate auth    → test de auth bypass
cateye validate xss     → test de XSS
cateye validate logic   → test de lógica

# Reportes
cateye report generate   → genera reporte desde finding
cateye report optimize   → optimiza con FeedbackEngine

# Finanzas
cateye earnings sync     → sincroniza ledger
cateye payout check      → verifica pagos pendientes
cateye roi calculate     → calcula ROI de sesión

# Sistema
cateye healthcheck       → verifica integridad del sistema
cateye cleanup           → limpia caché y datos temporales
cateye reset session     → reinicia sesión actual
```

### 11.2 Scripts de mantenimiento

```bash
# Tests
python -m pytest tests/ -v --tb=short

# Lint
python -m ruff check .

# Type check
python -m mypy cores/ api/ desktop/

# Build
python scripts/build_release.py

# Smoke test
python scripts/smoke_test.py
```

---

## 12. Conexiones y Plataformas

### 12.1 Plataformas soportadas

| Plataforma | API | Estado |
|------------|-----|--------|
| HackerOne | Sí | ✅ Producción |
| Bugcrowd | Sí | ✅ Producción |
| Intigriti | Sí | ✅ Beta |
| Synack | Sí | ✅ Beta |
| YesWeHack | Sí | ✅ Beta |

### 12.2 Configurar conexión

`/connections` → cada plataforma requiere:
1. API token o credenciales
2. Verificar identidad
3. Sincronizar programas activos

**Seguridad:** las credenciales se almacenan en `identity_vault` con AES-256-GCM.

### 12.3 Sincronización de earnings

```bash
cateye earnings sync
```

O automático: el sistema sincroniza earnings cada vez que abrís el dashboard.

---

## 13. Configuración

### 13.1 Variables de entorno (`.env`)

```bash
# Server
CATEYE_PORT=8000
CATEYE_HOST=0.0.0.0

# Database
DATABASE_URL=sqlite:///$HOME/.cateye/cateye.db  # SQLite
# DATABASE_URL=postgresql://user:pass@localhost/cateye  # PostgreSQL

# AI Providers
OLLAMA_HOST=http://localhost:11434
# OPENAI_API_KEY=sk-...
# OPENROUTER_API_KEY=...

# Features
CATEYE_DEBUG=0
CATEYE_DRY_RUN=0
```

### 13.2 Directorios de datos

```
Linux:   ~/.local/share/CATEYE/
macOS:   ~/Library/Application Support/CATEYE/
Windows: %APPDATA%/CATEYE/
```

### 13.3 Modos de operación

| Modo | Flag | Qué hace |
|------|------|----------|
| Browser | `--browser` | Backend + frontend + navegador |
| Tray | `--tray` | Solo bandeja de sistema |
| Service | `--service` | Servicio de Windows |
| Safe mode | `--safe-mode` | Modo degradado (solo browser) |
| Dry run | `CATEYE_DRY_RUN=1` | No ejecuta acciones reales |

---

## 14. Solución de Problemas

### 14.1 El sistema no arranca

```bash
python run.py --safe-mode
```

Esto saltea la mayoría de las validaciones y abre solo el navegador.

### 14.2 No se ven programas en Money Radar

```
1. Verificá que el backend esté corriendo → http://localhost:8000/health
2. Chequeá que haya datos → ¿corriste seed?
   python scripts/seed_real.py
3. Revisá los logs → ~/.cateye/logs/
```

### 14.3 Los reportes no se generan

```bash
# Verificá el AI provider
curl http://localhost:11434/api/tags  # Ollama
# o checkeá OPENAI_API_KEY en .env
```

### 14.4 Errores de validación

La mayoría de los errores se deben a:
1. LLM no disponible → CATEYE usa Ollama por defecto
2. Timeout en escaneo → ajustá `timeout_seconds` en el profile
3. Faltan herramientas externas → `scripts/install_tools.sh`

### 14.5 Healthcheck rápido

```bash
python -c "
from cores.env.config import CATEYEConfig
cfg = CATEYEConfig()
print(f'Port: {cfg.port}')
print(f'DB: {cfg.database_url}')
print('Config OK')
"
```

---

## 15. Referencia Rápida

### 15.1 Atajos del teclado (frontend)

```
Ctrl+K → Paleta de comandos
Ctrl+B → Toggle sidebar
Ctrl+J → Toggle copilot
Esc    → Cerrar modal / panel
```

### 15.2 API endpoints clave

| Endpoint | Método | Qué hace |
|----------|--------|----------|
| `/api/economic/money-radar` | GET | Todos los programas con ORION Score |
| `/api/economic/financial-summary` | GET | Resumen financiero completo |
| `/api/economic/programs/{id}/plan` | GET | Plan de misión para un programa |
| `/api/opportunity/evh` | GET | Oportunidades rankeadas por EVH |
| `/api/connections/withdrawals` | GET/POST | Retiros |
| `/api/reports` | GET/POST | Reportes |
| `/api/findings` | GET/POST | Hallazgos |
| `/api/financial` | GET | Financial Truth Layer (state, summary, withdrawals, reconciliation) |
| `/api/crypto` | GET/POST | Crypto wallets (list, sync, balance, history) |
| `/api/accounts-hub` | GET | Hub unificado (platforms + wallets + KPIs) |

### 15.3 Comandos útiles

```bash
# Inicio rápido
python run.py

# Ver estado del sistema
python run.py --diagnostics

# Tests
python -m pytest tests/ -x --tb=short -q

# Reconstruir base de datos
rm ~/.local/share/CATEYE/cateye.db && python run.py

# Seed con datos de prueba
python scripts/seed_real.py
```

### 15.4 Arquitectura en una línea

```
Frontend (Vue 3) ↔ API (FastAPI) ↔ Cores (Python) ↔ DB (SQLite/Postgres) ↔ AI (Ollama/OpenAI)
```

### 15.5 Versiones

| Versión | Cambios clave |
|---------|---------------|
| 1.8.0   | Financial Truth Layer + Crypto Sync System: truth_layer, sync_pipeline, withdrawal, reconciliation, EVMConnector (5 chains), ExchangeConnector (4 exchanges), AccountsHub + SyncCenter + TruthInspector frontend, 382 API routes, 165 tests |
| 1.7.2   | 5 money-impact modules: TargetRadar, LightningScanner, DuplicateDetector, FeedbackEngine, PoCEngine |
| 1.7.1   | Hardening: mypy 0 errores, ruff 39 cosmetic, retry handler, logo fix |
| 1.7.0   | 100% backend coverage, test infra, OpenAPI docs, modelo renombrado a CATEYE |
| 1.6.x   | Path unification, config cleanup, UX polish |

---

*CATEYE — inteligencia económica para bug bounty. Cada recomendación tiene un número. Cada número tiene una razón.*
