# CATEYE — Tutorial de Uso

## Primeros Pasos

### 1. Instalación

```bash
git clone https://github.com/AdriDob/Rastro.git
cd Rastro

pip install -r requirements.txt
cd frontend && npm install && cd ..

cp .env.example .env
python launcher/start.py
```

### 2. Inicio

```bash
python launcher/start.py
```

Esto inicia backend (`:8000`) y abre el frontend en el navegador (`:5173` en dev). La pantalla de login aparece primero — el sistema genera un token automático en modo local.

---

## Flujo de Trabajo Diario

### 1. Panel Económico (`/`)

La home responde las 5 preguntas clave:
- **¿Cuánto dinero tengo?** — KPIs de earnings totales, pendientes, cobrados
- **¿Cuánto puedo cobrar?** — Pipeline de findings con estimación
- **¿Dónde está el mejor dinero?** — Money Radar con ORION Score
- **¿Qué debo hacer ahora?** — Next Action card con la tarea de mayor impacto
- **¿Cuánto tiempo invertir?** — EVH por programa, priorización por ROI

**Consejo:** Revisá esta pantalla cada vez que abrís CATEYE. En <20s sabés tu estado financiero.

### 2. Money Radar (`/money-radar`)

Programas rankeados por ORION Score (0.0–1.0). Factores:
- Potencial de recompensa (30 %)
- Éxito histórico (20 %)
- Competencia (15 %)
- Eficiencia temporal (15 %)
- Experiencia previa (10 %)
- Diversidad tecnológica (10 %)

**Consejo:** Trabajá primero los programas con ORION Score > 0.7 y EVH > 50 USD/h.

### 3. Cacería Autónoma

```bash
# Iniciar desde API
curl -X POST http://localhost:8000/api/hunt/start

# Estado
curl http://localhost:8000/api/hunt/status

# Pausar
curl -X POST http://localhost:8000/api/hunt/pause
```

El scheduler ejecuta etapas automáticamente:
| Etapa | Cada | Qué hace |
|---|---|---|
| DISCOVER | 1 h | Scrapea programas nuevos |
| RECON | 30 min | Subfinder, httpx, katana, nuclei, gau |
| HYPOTHESIS | 15 min | Genera hipótesis con IA |
| VALIDATE | 2 h | Valida hallazgos |
| REPORT | 1 h | Genera drafts de reporte |

### 4. Findings Pipeline (`/findings`)

Visualiza el flujo completo: `Detectado → Validado → Confirmado → Reportado → Pagado`.

Cada finding tiene:
- Severidad (Critical, High, Medium, Low, Info)
- CVSS score
- Evidencia asociada
- Estado del pipeline
- Acciones: validar, generar reporte, exportar

**Consejo:** Priorizá findings Critical/High con evidencia sólida. Son los que pagan mejor.

### 5. Report Center (`/reports`)

- **Generar draft:** IA genera PoC, impacto, remediación y CVSS
- **Exportar:** Markdown, PDF, HTML, TXT
- **Enviar:** Directo a HackerOne/Bugcrowd/Intigriti via API keys (requiere aprobación humana)
- **Reward Learning:** CATEYE aprende de respuestas de plataformas para mejorar reportes futuros

**Consejo:** Siempre revisá el draft antes de enviar. La IA es asistente, no reemplazo.

### 6. AI Copilot (`Ctrl+B`)

Chat contextual con el sistema. Podés preguntar:
- "¿Cuál es mi mejor programa hoy?"
- "Mostrame los findings críticos sin reporte"
- "¿Qué debo hacer ahora?"
- "Generame un plan de cacería para [programa]"

El Copilot conoce:
- Tu estado económico actual
- Findings activos
- Programas y sus ORION Scores
- Patrones aprendidos

---

## OSINT Intelligence

CATEYE integra 16 APIs OSINT. Para consultar:

```bash
# Listar fuentes disponibles
GET /api/osint/sources

# Consultar dominio
POST /api/osint/query
{"sources": ["shodan", "censys", "virustotal"], "query": "ejemplo.com"}
```

Fuentes: Shodan, Censys, VirusTotal, SecurityTrails, AlienVault OTX, URLScan.io, Hunter.io, BuiltWith, Have I Been Pwned, GreyNoise, IntelX, Pulsedive, ThreatFox, IPInfo, SpoofCheck.

---

## Conexiones y Plataformas

### Agregar cuenta de plataforma

1. `/connections` → Agregar conexión
2. Seleccionar plataforma (HackerOne, Bugcrowd, etc.)
3. Ingresar API key (se almacena cifrada en Identity Vault)
4. Probar conexión

### Cuentas de cobro

Agregá wallets para recibir pagos: USDT, BTC, ETH, PayPal.

---

## Configuración

`/settings` permite:
- **General:** Tema, idioma, atajos
- **IA:** Seleccionar proveedor (Gemini, Ollama, OpenAI, OpenRouter)
- **Herramientas:** Activar/desactivar herramientas de recon
- **API Keys:** Gestionar keys de OSINT y plataformas

---

## Consejos de Productividad

1. **Dejá la cacería autónoma corriendo 24/7** — CATEYE trabaja mientras dormís
2. **Revisá el Money Radar cada mañana** — Los scores cambian con nuevos datos
3. **No auto-enviés reportes** — Siempre revisión humana antes de enviar
4. **Usá el Copilot para dudas rápidas** — Ctrl+B, preguntá en lenguaje natural
5. **Alimentá el Identity Vault** — Conectá todas tus plataformas para tracking completo
6. **Dejá que el Reward Learning actúe** — Con cada reporte, CATEYE mejora
