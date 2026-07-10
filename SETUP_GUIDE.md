# SETUP GUIDE — CATEYE v3.0.0

> Guía de configuración óptima para usar CATEYE en bug bounty real.
> Elegí el perfil que mejor se adapte a tu equipo y necesidades.

---

## Perfiles de configuración

| Perfil | Hardware | Automatización | Ideal para |
|--------|----------|----------------|------------|
| **Mínima** | 4GB RAM, 2 cores | Solo scheduler básico | Probar CATEYE por primera vez |
| **Recomendada** | 8GB RAM, 4 cores | Scheduler completo + LLM local | Uso diario |
| **Profesional** | 16GB RAM, 8 cores | Full pipeline + LLM local + recon tools | Uso intensivo |
| **Máxima** | 32GB+ RAM, 16+ cores | Todo activo + múltiples LLMs | Producción pesada |

---

## Configuración mínima

### Qué instalar
```bash
# Solo lo esencial para que CATEYE funcione
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
python run.py --setup
```

### Qué activar
- Scheduler: ON (intervalo 60 min)
- Modo scan: API (no requiere herramientas externas)
- LLM: OpenAI o Gemini (API key remota)

### Qué dejar desactivado
- Recon tools externas (subfinder, nuclei, etc.)
- Crypto sync
- OSINT APIs
- Discovery Monitor (ejecutar manual cuando se necesite)

### Impacto
- ✅ CATEYE funciona completamente
- ❌ No hay recon profundo (solo httpx + katana + nuclei vía API)
- ❌ No hay detección de pagos automática
- ❌ Las oportunidades en RAM se pierden al reiniciar

---

## Configuración recomendada

### Qué instalar

```bash
# Backend + frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
python run.py --setup

# Herramientas de recon (esencial)
./scripts/install_tools.sh
```

### Qué activar
- Scheduler: ON (intervalo 30 min)
- Modo scan: FAST (subfinder + katana + wayback)
- LLM local: Ollama con modelo como `llama3` o `mistral`
- Discovery Monitor: ON
- Financial Sync: ON
- Health Monitor: ON
- API keys: Shodan, Censys, VirusTotal (mejoran el recon)

### Qué dejar desactivado
- Modo DEEP scan (usar solo cuando sea necesario)
- Crypto wallets (si no operás con crypto)
- Plaid bank sync (si no tenés cuenta US)

### Verificar instalación de herramientas
```bash
# Cada herramienta debe responder
subfinder -version
httpx -version
katana -version
nuclei -version
amass -version
gau -version
ffuf -version
```

### Impacto
- ✅ Pipeline E2E completo
- ✅ Recon automático con resultados reales
- ✅ ORION aprende de tus findings
- ✅ Tracking financiero automático
- ~200-500MB RAM en reposo

---

## Configuración profesional

### Qué instalar
```bash
# Todo lo de la configuración recomendada +
# Herramientas adicionales
pip install aiohttp  # necesario para crtsh

# LLM local con buen modelo
ollama pull llama3
ollama pull mistral
ollama pull codellama  # para análisis de código
```

### Qué activar
- Todo lo de la configuración recomendada +
- Modo DEEP scan nocturno
- Crypto wallets (BTC, ETH, SOL, TRX)
- OSINT APIs completas (Shodan, Censys, VirusTotal, SecurityTrails, etc.)
- Plataformas: HackerOne + Bugcrowd + Intigriti + YesWeHack APIs
- Auto-report: ON (revisar borradores antes de enviar)
- Wallet Connect si usás mobile wallets

### Qué ajustar
- Scheduler intervalo: 15 min (más agresivo)
- Cooldown entre scans: mantener 3600s (evita rate limiting)
- Temperature del LLM: 0.3 (más preciso para validación)

### Hardware recomendado
- 16GB RAM (Ollama + backend + frontend)
- 4+ cores CPU
- 20GB+ disco disponible
- Conexión a internet estable

### Impacto
- ✅ Automatización casi completa
- ✅ Recon profundo diario
- ✅ Tracking financiero multiplataforma
- ✅ ORION con aprendizaje continuo
- ~1-2GB RAM con Ollama corriendo
- ~10-20GB disco para datos + herramientas

---

## Configuración máxima

### Qué instalar
```bash
# Todo lo profesional +
ollama pull mixtral  # modelo más grande y preciso

# Herramientas de recon pesadas
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest

# ZAP (escaneo pasivo opcional)
# Descargar de https://www.zaproxy.org/download/
```

### Qué activar
- Todo lo profesional +
- Modo DEEP como default nocturno
- ZAP integration para escaneo pasivo
- Multiple LLM providers (Ollama para local + OpenAI/Gemini como fallback)
- Discovery Monitor cada 12h
- Financial Sync cada 10 min

### Hardware recomendado
- 32GB+ RAM
- 8+ cores CPU
- 50GB+ disco (SSD recomendado)
- GPU (opcional, para Ollama con modelos grandes)

### Impacto
- ✅ Automatización total del pipeline
- ✅ Múltiples LLMs para validación cruzada
- ✅ Recon más completo (naabu, dnsx, ZAP)
- ✅ Sincronización en tiempo real
- ~3-8GB RAM dependiendo del modelo LLM
- ~30-50GB disco para datos acumulados

---

## Optimización por recurso

### Si tenés poca RAM (4-8GB)
1. Usá Ollama con modelos pequeños (`phi3`, `tinyllama`)
2. Desactivá el frontend (usá solo API)
3. Reducí el scheduler a 60 min
4. No uses ZAP integration
5. Limitá los workers de recon a 2

### Si tenés poco CPU (2 cores)
1. Desactivá el modo DEEP
2. Usá mode API para los scans
3. Reducí concurrencia de recon tools
4. No ejecutes validación batch (hacela manual)

### Si tenés poco disco (10-20GB)
1. Configurá WAL checkpoint frecuente (ya configurado)
2. Limitá el histórico de eventos (EventBus guarda todo)
3. Hacé backup y purge de datos viejos mensualmente
4. No instales todas las herramientas de recon

### Si tenés internet limitada
1. Usá Ollama local (no requiere API calls externas)
2. Desactivá OSINT APIs
3. Usá modo FAST con las tools que ya tenés instaladas
4. Desactivá Financial Sync

---

## Checklist post-instalación

Una vez instalado, verificá:

```bash
# 1. Backend responde
curl http://127.0.0.1:8000/api/health

# 2. Versión correcta
curl http://127.0.0.1:8000/api/version
# → {"version":"3.0.0"}

# 3. DB inicializada
python -c "from database.db import init_db; init_db(); print('DB OK')"

# 4. Frontend compila
cd frontend && npm run build && ls dist/index.html && cd ..

# 5. Scheduler inicia
python run.py --dev
# → Ver "ScanScheduler started" en logs

# 6. Seed data (opcional)
python scripts/seed_real.py

# 7. Tests pasan
pytest --timeout=60 --ignore=tests/test_security.py
# → 393 passed, 2 xfailed
```

---

## Errores comunes de configuración

### "ModuleNotFoundError: No module named 'cores'"
```bash
# Ejecutar desde la raíz del proyecto, no desde subdirectorios
cd /ruta/a/Rastro
source .venv/bin/activate
```

### "sqlite3.OperationalError: no such table"
```bash
# Correr setup primero
python run.py --setup
```

### "Address already in use"
```bash
# Puerto 8000 ocupado
lsof -i :8000
kill -9 <PID>
```

### "Command not found: subfinder" (o cualquier tool)
```bash
# Las tools de recon son externas. Instalarlas con:
./scripts/install_tools.sh
# O instalarlas manualmente con go install
```

### "OpenAI API error" / "Gemini API error"
```json
// Verificar API key en Settings > AI
// O directamente en la DB:
// La API key debe ser válida y tener crédito disponible
```

---

## Referencia rápida de settings

| Setting | Dónde se configura | Default | Recomendado |
|---------|-------------------|---------|-------------|
| LLM Provider | Settings > AI | ollama | ollama (local) |
| Scheduler interval | Settings > Runtime | 30 min | 30 min |
| Scan mode | Por request | FAST | FAST (DEEP nocturno) |
| Discovery Monitor | Settings > Runtime | ON | ON |
| Financial Sync | Settings > Runtime | ON | ON |
| Temperature | Settings > AI | 0.7 | 0.3 (validación) |
| Ollama host | Settings > AI | localhost:11434 | localhost:11434 |

---

*Julio 2026 — CATEYE v3.0.0*
