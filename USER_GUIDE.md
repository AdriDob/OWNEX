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
8. [Troubleshooting completo](#8-troubleshooting-completo)
9. [Backup y restauración](#9-backup-y-restauración)
10. [Mantenimiento](#10-mantenimiento)
11. [Actualización](#11-actualización)

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

---

## 8. Troubleshooting completo

### El backend no inicia

```bash
# 1. Verificar que estás en la raíz del proyecto
ls run.py  # debe existir

# 2. Verificar que el virtualenv está activado
which python  # debe mostrar .venv/bin/python

# 3. Verificar dependencias instaladas
pip list | grep fastapi  # debe mostrar fastapi

# 4. Verificar puerto
lsof -i :8000  # si está ocupado, matar el proceso

# 5. Inicializar DB manualmente
python -c "from database.db import init_db; init_db(); print('DB OK')"

# 6. Iniciar con logs detallados
python run.py --browser --verbose
```

### El frontend queda en blanco

```bash
# 1. Compilar frontend
cd frontend && npm run build

# 2. Verificar que existe el build
ls dist/index.html

# 3. Si faltan dependencias
npm install

# 4. Si hay errores de compilación
npm run dev  # ver errores en terminal
```

### No aparecen programas (discovery no encuentra nada)

```bash
# 1. Ejecutar discovery manual
curl -X POST http://127.0.0.1:8000/api/discovery/scan

# 2. Ver resultados
curl http://127.0.0.1:8000/api/discovery/programs

# 3. Si no hay resultados, verificar conectividad
curl https://hackerone.com  # debe responder

# 4. Importar programas descubiertos
curl -X POST http://127.0.0.1:8000/api/discovery/import-all
```

### No descubre targets (el scraper no encuentra nada)

Posibles causas:

1. **Sin conexión a internet** — El scraper necesita acceder a HackerOne, Bugcrowd, etc.
2. **Las fuentes cambiaron su estructura** — El scraper depende del HTML de cada plataforma
3. **Rate limiting** — Las plataformas pueden bloquear requests masivos

Solución:
```bash
# Verificar que el scraper puede conectarse
python -c "
from cores.bounty_scraper.scraper import BountyScraper
s = BountyScraper()
results = s.scrape_all()
print(f'Encontrados: {len(results)} programas')
"
```

### No encuentra subdominios (recon devuelve vacío)

```bash
# 1. Verificar que las herramientas están instaladas
subfinder -version
httpx -version

# 2. Si faltan, instalarlas
./scripts/install_tools.sh

# 3. Verificar que el target tiene dominio válido
# Ir a Targets → seleccionar target → verificar que tiene URL

# 4. Probar con modo API (no requiere tools externas)
POST /api/targets/{id}/scan?mode=API
```

### Recon tarda demasiado

| Modo | Tiempo estimado | Recomendación |
|------|-----------------|---------------|
| FAST | 2-5 min | Default diario |
| DEEP | 15-30 min | Usar de noche |
| API | 1-3 min | Cuando no hay tools instaladas |

Si aún así tarda:
- Verificar recursos del sistema (CPU, RAM, disco)
- Reducir concurrencia en settings
- Cerrar otras aplicaciones pesadas

### No aparecen findings después de validación

```bash
# 1. Verificar que existen endpoints para validar
curl http://127.0.0.1:8000/api/endpoints

# 2. Verificar que existen hipótesis generadas
curl http://127.0.0.1:8000/api/hypotheses

# 3. Ejecutar validación manual
curl -X POST http://127.0.0.1:8000/api/validation/batch

# 4. Verificar findings generados
curl http://127.0.0.1:8000/api/findings
```

### ORION recomienda poco o nada

ORION necesita datos para recomendar. Si recién empezás:

1. Primero necesitás targets importados
2. Después necesitás endpoints (de al menos 1 scan)
3. ORION empieza a recomendar después de tener contexto

```bash
# Ver qué sabe ORION
curl http://127.0.0.1:8000/api/orion/context

# Ver próxima acción
curl http://127.0.0.1:8000/api/orion/next-action

# Forzar refresco de contexto
curl -X POST http://127.0.0.1:8000/api/orion/context/refresh
```

Si ORION sigue sin recomendar:
- Probablemente no hay suficientes datos
- Usá `scripts/seed_real.py` para cargar datos de ejemplo
- O importá programas reales y ejecutá scans

### No genera reportes (auto-report no funciona)

```bash
# 1. Verificar que hay findings confirmados
curl 'http://127.0.0.1:8000/api/findings?status=confirmed'

# 2. Si no hay, confirmar algún finding manualmente
# Ir a Findings → seleccionar → Confirm

# 3. Verificar que el subscriber de auto-report está activo
# En los logs debe aparecer:
# "[AutoReport] Finding X confirmed → generating draft"

# 4. Generar reporte manualmente
curl -X POST http://127.0.0.1:8000/api/reports
```

### El scheduler parece detenido

```bash
# 1. Verificar estado del scheduler
curl http://127.0.0.1:8000/api/system/status

# 2. Buscar "scheduler" en el response
# Debe mostrar: "running", última ejecución, próxima ejecución

# 3. Si no está corriendo, revisar logs del backend
# Buscar: "ScanScheduler started" al iniciar

# 4. Verificar que el pipeline no está paused
# Ir a Settings > Runtime → Scheduler debe estar ON

# 5. Como fallback, reiniciar el backend
# Ctrl+C y volver a iniciar
```

### SQLite bloqueada ("database is locked")

```bash
# 1. Si aparece "database is locked", esperar unos segundos
# SQLite se desbloquea solo (WAL mode)

# 2. Si persiste, verificar que no hay otro proceso usando la DB
lsof ~/.orion/catseye.db

# 3. Forzar checkpoint WAL
python -c "
from database.db import get_db
with get_db() as session:
    session.execute(text('PRAGMA wal_checkpoint(TRUNCATE)'))
    session.commit()
    print('WAL checkpoint OK')
"

# 4. Como último recurso, reiniciar el backend
```

### Error "401 Unauthorized" en todas las requests

```bash
# 1. Obtener token nuevo
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"device_id": "mi-equipo"}'
# → {"data":{"token":"..."}}

# 2. Usar el token en todas las requests
curl http://127.0.0.1:8000/api/health \
  -H "Authorization: Bearer <token>"
```

### Error "CSRF token missing"

Si usás la API directamente (sin frontend), necesitás el header CSRF:

```bash
# 1. Obtener CSRF token desde cookie
curl -c cookies.txt http://127.0.0.1:8000/api/health

# 2. Enviar request con el token
curl -X POST http://127.0.0.1:8000/api/targets \
  -b cookies.txt \
  -H "X-CSRF-Token: $(grep csrf cookies.txt | awk '{print $7}')" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "url": "https://example.com"}'
```

O deshabilitar CSRF para desarrollo (no recomendado en producción):
```bash
export CATEYE_CSRF_DISABLED=1
```

### Error con herramientas de recon (permission denied)

```bash
# Las tools instaladas con go install quedan en ~/go/bin/
# Asegurate de tener ~/go/bin/ en el PATH

export PATH=$PATH:~/go/bin

# O instalalas en /usr/local/bin/
sudo cp ~/go/bin/subfinder /usr/local/bin/
```

### Error "Address already in use" al iniciar

```bash
# Puerto 8000 ocupado por otro proceso
lsof -i :8000
kill -9 <PID>

# O usar otro puerto
python run.py --browser --port 9000
```

### Error al hacer seed de datos

```bash
# Si seed_real.py falla, puede ser por:
# 1. DB no inicializada
python run.py --setup

# 2. Puerto no disponible
# Asegurate que el backend está corriendo

# 3. Datos ya existentes (no es error, el seed es idempotente)
# Simplemente ignora duplicados
```

### Error en la instalación de npm

```bash
cd frontend

# Si npm install falla, probar:
npm install --legacy-peer-deps

# O limpiar cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Error con PyInstaller (build desktop)

```bash
# Si el build falla, probar:
python run.py --build

# Errores comunes:
# - PyInstaller no instalado → pip install pyinstaller
# - Faltan imports ocultos → revisar .spec file
# - Versión de Python incompatible → usar 3.10 o 3.11
```

### La base de datos crece demasiado

```bash
# 1. Verificar tamaño
ls -lh ~/.orion/catseye.db

# 2. Hacer backup y vacuum
python -c "
from database.db import get_db
from sqlalchemy import text
with get_db() as session:
    session.execute(text('VACUUM'))
    session.commit()
    print('VACUUM OK')
"

# 3. Verificar WAL no crece (ya hay checkpoint automático)
# Si crece mucho, hacer checkpoint manual
```

---

## 9. Backup y restauración

### Backup manual

```bash
# 1. Detener CATEYE
# Ctrl+C en la terminal donde corre

# 2. Copiar la base de datos
cp ~/.orion/catseye.db ~/.orion/catseye.db.backup.$(date +%Y%m%d)

# 3. Copiar archivos de configuración
cp -r ~/.orion ~/.orion.backup.$(date +%Y%m%d)

# 4. Copiar audit log (opcional)
cp ~/.orion/audit.jsonl ~/.orion/audit.jsonl.backup.$(date +%Y%m%d)
```

### Restauración

```bash
# 1. Detener CATEYE

# 2. Restaurar DB
cp ~/.orion/catseye.db.backup.20260708 ~/.orion/catseye.db

# 3. Restaurar configuración
cp -r ~/.orion.backup.20260708/* ~/.orion/

# 4. Iniciar CATEYE
python run.py --browser
```

### Backup automático (recomendado)

Agregar al crontab:
```bash
# Diario a las 3 AM
0 3 * * * cp ~/.orion/catseye.db ~/.orion/backups/catseye.db.$(date +\%Y\%m\%d)
# Trimestral (primer día de cada trimestre)
0 3 1 1,4,7,10 * cp ~/.orion/catseye.db ~/.orion/backups/catseye.db.trimestral.$(date +\%Y\%m\%d)
```

---

## 10. Mantenimiento

### Diario
- Revisar findings nuevos
- Confirmar o rechazar findings pendientes
- Revisar auto-reports generados

### Semanal
- Revisar oportunidades nuevas
- Verificar health del sistema
- Sync earnings de plataformas

### Mensual
- Hacer backup de la DB
- Revisar targets inactivos
- Limpiar findings cerrados viejos
- Verificar que ORION está aprendiendo correctamente
- Revisar logs por errores recurrentes

### Trimestral
- Actualizar CATEYE (si hay nueva versión)
- Reinstalar tools de recon (pueden tener actualizaciones)
- Verificar que todas las integraciones siguen funcionando
- Hacer backup completo (DB + config + audit log)

---

## 11. Actualización

```bash
# 1. Guardar estado actual
git log --oneline -1  # registrar commit actual

# 2. Pull de cambios
git pull origin main

# 3. Actualizar dependencias
source .venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Recompilar frontend
cd frontend && npm install && npm run build && cd ..

# 5. Ejecutar migraciones (si hay)
python run.py --setup

# 6. Iniciar
python run.py --browser
```

Si algo falla después de la actualización:
```bash
# Revertir al commit anterior
git reset --hard <commit-anterior>
```
