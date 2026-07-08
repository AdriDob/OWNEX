# USER GUIDE — CATEYE v3.0.0

> Manual práctico para usar CATEYE en bug bounty todos los días.

---

## Índice

1. [Primeros pasos](#1-primeros-pasos)
2. [Configuración inicial](#2-configuración-inicial)
3. [Día típico de bug bounty](#3-día-típico-de-bug-bounty)
4. [Workflow semanal](#4-workflow-semanal)
5. [Workflow mensual](#5-workflow-mensual)
6. [Tips y atajos](#6-tips-y-atajos)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Primeros pasos

### Requisitos

- Python 3.10+
- Node.js 18+
- Git

### Instalación

```bash
git clone <repo> rastro
cd rastro

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..

# Inicializar DB
python run.py --setup
```

### Seed data (opcional pero recomendado)

Para cargar datos de demostración con programas reales:

```bash
source .venv/bin/activate
python scripts/seed_real.py
```

Esto crea 6 programas (Shopify, Discord, GitLab, Slack, WordPress, HackerOne), 14 findings de ejemplo, y un usuario admin.

### Iniciar CATEYE

```bash
# Modo desarrollo (API + frontend por separado)
source .venv/bin/activate
python run.py --browser

# O iniciar backend manualmente
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Y en otra terminal
cd frontend && npm run dev
```

Abrir navegador en `http://127.0.0.1:8000`.

---

## 2. Configuración inicial

### Primera ejecución

Al abrir CATEYE por primera vez, un asistente de 5 pasos te guiará:

1. **Bienvenido** — Ingresá tu nombre
2. **IA** — Configurá el proveedor LLM (Ollama para local, o Gemini/OpenAI/OpenRouter)
3. **API Keys** — Shodan, Censys, VirusTotal, SecurityTrails
4. **Plataformas** — HackerOne, Bugcrowd, Intigriti API keys
5. **Listo** — Resumen y finalizar

Podés saltear cualquier paso y configurarlo después desde `/settings`.

### Qué configurar antes de usar

| Configuración | ¿Dónde? | ¿Obligatorio? |
|---|---|---|
| LLM provider | Onboarding / Settings > AI | Sí (para análisis semántico) |
| HackerOne token | Settings > Platforms | Sí (para sync de programas) |
| Bugcrowd token | Settings > Platforms | Opcional |
| Shodan key | Settings > API Keys | Opcional (mejora recon) |

### Seed data recomendada

Si no usaste `seed_real.py`, CATEYE arranca vacío. Para empezar rápido:

```bash
python scripts/seed_real.py
```

O directamente importá programas desde las plataformas conectadas:

```
POST /api/discovery/scan        # Escanear programas disponibles
POST /api/discovery/import-all   # Importar todos
```

---

## 3. Día típico de bug bounty

### 08:00 — Abrir CATEYE

```
Abrir navegador → http://127.0.0.1:8000
→ Mission Control (dashboard)
```

ORION ya estuvo trabajando durante la noche. Revisá:

- **Oportunidades nuevas** (widget "Top Opportunities")
- **Programas descubiertos** (Discovery Monitor corre cada 24h)
- **Próxima acción recomendada** (ORION Next Action)

### 08:15 — Elegir objetivos

En `/program-catalog` o desde las tarjetas de oportunidad:

1. Revisá programas con mayor EVH (Expected Value per Hour)
2. Hacé clic en "Import" si es un programa nuevo
3. O envialo directamente al scheduler para recon automático

### 08:30 — Lanzar recon

Sobre un target específico:

```
POST /api/targets/{id}/scan?mode=FAST
```

Modos:
- **FAST**: subfinder + katana + wayback (rápido, ~2-5 min)
- **DEEP**: + amass + nuclei + gau + ffuf (~15-30 min)
- **API**: httpx + katana + nuclei (sin herramientas externas)

O esperá al scheduler que corre RECON automáticamente cada 30 min.

### 09:00 — Revisar resultados

En `/attack-surface`:

- Endpoints descubiertos por el scan
- Hipótesis generadas automáticamente (8 generadores rule-based)
- Findings de nuclei

### 09:30 — Validar hallazgos

En `/hypotheses`:

1. Revisá las hipótesis generadas
2. Ejecutá validación automática:

```
POST /api/validation/validate
{ "endpoint_id": "...", "hypothesis_type": "idor" }
```

3. CATEYE ejecuta RequestReplayer + LLM semantic analysis
4. Si el resultado es positivo → se crea un Finding

### 10:00 — Revisar y confirmar findings

En `/findings`:

- Estado: `open` (pendiente revisión) → `confirmed` | `false_positive`
- Findings confirmados → gatillan auto-report automático
- CATEYE genera un borrador de reporte

### 10:30 — Editar y exportar reportes

En `/reports`:

1. Revisá el borrador generado automáticamente
2. Editá con PUT `/api/reports/{id}`
3. Exportá al formato que necesites:

```
GET /api/reports/{id}/export?format=markdown
GET /api/reports/{id}/export?format=html
GET /api/reports/{id}/export?format=pdf
GET /api/reports/{id}/export?format=txt
```

4. Enviá a plataforma:

```
POST /api/reports/{id}/submit
```

### 11:00 — Revisar payouts y tracking

En `/bounties` o `/money-radar`:

- Estado de submissions anteriores
- Earnings sincronizados (FinancialSync cada 30 min)
- Ledger financiero completo

---

## 4. Workflow semanal

### Lunes — Planificación

```bash
# Revisar oportunidades nuevas de la semana
GET /api/opportunity/top

# Ver próxima acción recomendada por ORION
GET /api/orion/next-action

# Planificar objetivos de la semana
# Elegir 2-3 programas para enfocar
```

### Miércoles — Revisión de findings

```bash
# Ver findings pendientes
GET /api/findings?status=open

# Ver hipótesis sin validar
GET /api/hypotheses

# Ejecutar validación batch
POST /api/validation/batch
```

### Viernes — Cierre semanal

```bash
# Revisar reportes generados en la semana
GET /api/reports

# Ver estado financiero
GET /api/financial/state

# Ver métricas del sistema
GET /api/stats

# Ejecutar seed de datos frescos (opcional)
python scripts/seed_real.py
```

---

## 5. Workflow mensual

### Revisión de salud del sistema

```bash
GET /api/system/status    # Estado general
GET /api/system/state     # System State + health
GET /api/health           # Health check
```

### Revisión de aprendizaje de ORION

```bash
GET /api/orion/context    # Contexto completo de ORION
```

ORION aprende de tus resultados. Después de varias semanas:
- Mejora la priorización de programas
- Ajusta estimaciones por tipo de vulnerabilidad
- Recomienda acciones más relevantes

### Limpieza

```bash
# Revisar targets inactivos
# Revisar findings cerrados
# Revisar reports viejos (archivar)
```

---

## 6. Tips y atajos

### Atajos de API

| Acción | Endpoint |
|---|---|
| Descubrir programas | `POST /api/discovery/scan` |
| Importar todo | `POST /api/discovery/import-all` |
| Scan rápido | `POST /api/targets/{id}/scan?mode=FAST` |
| Scan profundo | `POST /api/targets/{id}/scan?mode=DEEP` |
| Exportar finding | `GET /api/findings/{id}/export-markdown` |
| Exportar reporte | `GET /api/reports/{id}/export?format=md` |
| Próxima acción ORION | `GET /api/orion/next-action` |

### Buenas prácticas

- **Usá FAST mode primero** — es rápido y te da una idea del attack surface
- **DEEP mode de noche** — lanzalo antes de dormir, revisá resultados a la mañana
- **Dejá correr el scheduler** — no necesitás estar presente, CATEYE trabaja solo
- **Revisá auto-report** — los borradores automáticos son un buen punto de partida
- **ORION mejora con uso** — mientras más findings confirmés, mejores van a ser sus recomendaciones

### ORION: cómo aprovecharlo al máximo

ORION es el sistema de priorización. Cuanto más uses CATEYE, mejor va a aprender:

- **Confirmá findings** — cada confirmación le enseña a ORION qué buscar
- **Marcá false positives** — ORION aprende a ignorar patrones que no dan resultado
- **Syncéá earnings** — ORION ajusta sus estimaciones basado en pagos reales

ORION NUNCA:
- Envía reportes automáticamente
- Gasta dinero
- Borra evidencia
- Reemplaza tu decisión

---

## 7. Troubleshooting

### Error: "Authorization header required"

El backend requiere autenticación. Si estás en desarrollo:

```
POST /api/auth/login
{ "device_id": "mi-dispositivo" }
→ { "data": { "token": "..." } }
```

Usá ese token como header: `Authorization: Bearer <token>`

### Error: Backend no arranca

```bash
# Verificar que la DB se inicializa
python -c "from database.db import init_db; init_db()"

# Verificar puerto ocupado
lsof -i :8000

# Log de startup
python run.py --browser --verbose
```

### Error: Scheduler no ejecuta scans

Verificar que las herramientas de recon están instaladas:

```bash
./scripts/install_tools.sh
```

O revisá el estado:

```bash
GET /api/system/status
→ Verificar "scheduler" en el response
```

### Error: Frontend no carga

```bash
cd frontend && npm run build
# Verificar que frontend/dist/ existe con index.html
```

### Error: No aparecen programas nuevos

```bash
# Ejecutar discovery manual
POST /api/discovery/scan

# Ver programas descubiertos
GET /api/discovery/programs

# Importar
POST /api/discovery/import-all
```

### Error: ORION no responde

```bash
GET /api/orion/context
GET /api/orion/next-action
```

Si no hay datos, primero necesitás targets y findings. ORION necesita contexto para recomendar.

### Error: Tests fallan

```bash
pytest --timeout=60 --ignore=tests/test_security.py
# 393 tests deben pasar (v3.0.0)
```
