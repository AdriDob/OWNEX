# Decisions — Registro de Decisiones Arquitectónicas

## 2026-08-10: CALM UX — el sistema entero debe sentirse relajante, 0 estresante

- **Problema**: El sistema acumula tonos agresivos/sobre-excitados (exclamaciones, neón, alarmas, métricas de presión, errores duros) que generan estrés en el usuario. Decisión del owner: OWNEX debe sentirse **relajante de usar, 0 estresante** — aplica al sistema en general, no solo a la voz.
- **Directriz global de diseño** (se aplica incrementalmente a todo acceso de OWNEX):
  1. **Voz**: tono grave-medio, ~0.95x, pausas, emoción contenida, framing "Resultado, {verdict}." — ya implementado (`calm_operator`, `VoicePersonality`).
  2. **Textos** (UI, replies, briefs, notificaciones): anunciar resultados con calma, sin exclamaciones ni drama; sin "alerta crítica" innecesaria.
  3. **Errores**: suaves, accionables, sin pánico ("no se pudo X; esto no afecta el resto" > "ERROR CRÍTICO"). Los niveles de severidad solo para lo que es realmente grave.
  4. **Métricas**: mostrar progreso y estado, no presión (evitar contadores rojos, deadline agresivos como "¡URGENTE!").
  5. **UI/animaciones**: movimientos sutiles, sin parpadeos ni efectos de urgencia; densidad visual baja.
- **Impacto**: Los cambios se hacen incrementalmente (nunca un sweep masivo): cada módulo que se toque debe pasar por este filtro. La voz ya cumple; el resto queda como regla permanente para trabajos futuros.
- **Condiciones para reabrir**: Nunca — es state de diseño permanente.

## 2026-08-04: OAR AI Runtime — sistema operativo unificado de providers de IA

- **Problema**: Cada operación de IA se cableaba contra un provider concreto (Ollama local, OpenRouter, Groq, FCC, etc.) de forma ad-hoc. No había un punto único de entrada: rutear por tipo de tarea, presupuesto, failover, caché ni aprendizaje de preferencias. Con 9+ providers disponibles, el routing manual no escala y no respeta el coste (budget diario USD).
- **Alternativas consideradas**:
  1. **OAR (`cores/ai/runtime/`), elegido** — Contenedor único que levanta registry → health → cost → failover → cache → context → learning → router. `SmartRouter` decide por `TaskType` (CODE→local, etc.) priorizando local+gratis (`prefer_local`/`prefer_free`), con confidence y estimación de coste/latencia.
  2. Envolver solo el router de FCC — Dependía de un solo proxy, no del ecosistema completo de providers.
  3. Mantener el cableado ad-hoc — No cierra ningún loop de coste/failover/aprendizaje.
- **Decisión**: OAR como API unificada de IA. 9 factories de adapters (OpenRouter, Groq, Together, DeepInfra, Cerebras, NVIDIA, FCC, OpenCode, LMStudio). `CostTracker` con `daily_budget_usd`, `FailoverEngine` (circuit breaker por provider), `LearningEngine` (preferencias por TaskType), `SemanticCache`.
- **Impacto**:
  - Un solo `OAR.initialize()` → toda la infra de IA lista
  - Routing por tarea + budget + failover + aprendizaje en un solo lugar
  - `tests/test_oar.py` 12 passed; aún **sin** router API (necesita `api/routers/oar.py`)
- **Condiciones para reabrir**: Métricas de coste/latencia por provider observadas en producción, o decisión de exponer OAR vía API REST.

## 2026-08-04: Career Engine — aprendizaje continuo del usuario (skill gaps + roadmap)

- **Problema**: OWNEX encontraba oportunidades pero no cerraba el loop de "cómo el usuario gana la skill que le faltaría para cobrar más". El `UserProfile` del DWE tiene skills, pero nada las comparaba contra lo que cada categoría de mercado realmente pide.
- **Alternativas consideradas**:
  1. **Career Engine (`cores/career_engine.py`), elegido** — `CATEGORY_REQUIRED_SKILLS` curadas de realidad de mercado por las 36 categorías. `detect_skill_gaps()` prioriza "skill compartida por 2+ categorías" como high. Genera roadmap, preguntas de entrevista por categoría, y plan de entrenamiento diario. Todo deriva del `UserProfile` real (nunca inventa).
  2. Solo listar skills — No produce acción (roadmap/entrenamiento/entrevista).
  3. Modelo ML de skill-matching — Sobredimensionado sin datos de entrenamiento reales.
- **Decisión**: Career Engine como motor determinista. Se auto-registra en CapabilityRegistry vía `register_all_capabilities()` (también registra el DWE, idempotente).
- **Impacto**:
  - Cierra el `skill_gap` del Daily Brief del Work Bank: el top pick viene con su plan de aprendizaje
  - `tests/test_career_engine.py` 14 passed
  - Aún **sin** router API (se puede exponer como `/career/*`)
- **Condiciones para reabrir**: Exponer API `/career/*` o integrar el roadmap en Mission Control para que sea visible (regla "si no es visible, no existe").

## 2026-07-06: Ed25519 para licencias

- **Problema**: El sistema de licencias usaba HMAC-SHA256 con una clave hardcodeada en el código fuente. Cualquier persona con acceso al binario podía forjar licencias.
- **Alternativas consideradas**:
  1. RSA-2048 — Claves grandes (512 bytes), dependencia de openssl CLI
  2. ECDSA P-256 — Buen tamaño pero más complejo de implementar
  3. **Ed25519 (elegido)** — Claves pequeñas (32 bytes públicas), verificación rápida, sin dependencias externas
- **Decisión**: Ed25519. Clave pública embebida en el binario, clave privada en servidor de licencias.
- **Impacto**: 
  - Formato de licencia: 25 caracteres (sin cambios en UX)
  - Firma completa almacenada en license.json (64 bytes base64)
  - Migración: licencias HMAC antiguas no son compatibles (deben re-generarse)
- **Condiciones para reabrir**: Si se demuestra que Ed25519 tiene una vulnerabilidad criptográfica.

## 2026-07-06: Clave AES aleatoria en archivo para IdentityVault

- **Problema**: La clave AES se derivaba de `/etc/machine-id`, que es world-readable. Cualquier usuario local podía descifrar la bóveda.
- **Alternativas consideradas**:
  1. **Clave aleatoria en archivo (elegido)** — Generada con `secrets.token_bytes(32)`, chmod 600
  2. Master password + Argon2id — Más seguro pero requiere UX para pedir contraseña
  3. TPM/secure enclave — No portable entre plataformas
- **Decisión**: Clave aleatoria en archivo. El archivo se crea con permisos 600. Migración automática desde vaults existentes.
- **Impacto**: 
  - Bóvedas existentes se migran automáticamente en el primer acceso
  - La clave sobrevive reinicios (persistente en disco)
  - Master password no implementado (pendiente para futura versión)
- **Condiciones para reabrir**: Si se requiere proteger contra acceso root.

## 2026-07-06: Doble-submit cookie para CSRF

- **Problema**: No existía protección CSRF en la API.
- **Alternativas consideradas**:
  1. **Doble-submit cookie (elegido)** — Token en cookie + header. Sin estado en servidor.
  2. CSRF token con sesión — Requiere store server-side
  3. SameSite=Strict — Insuficiente para cross-origin legítimos
- **Decisión**: Doble-submit cookie. Token criptográficamente aleatorio en cookie httponly, mismo token en header X-CSRF-Token.
- **Impacto**:
  - Middleware global con excepciones para endpoints públicos
  - Deshabilitado en dev mode (CATEYE_DESKTOP no configurado)
  - GET requests setean la cookie automáticamente
- **Condiciones para reabrir**: Si se encuentra un bypass del patrón double-submit.

## 2026-07-06: Scheduler adaptativo con cooldown

- **Problema**: El scheduler ejecutaba scans a intervalos fijos sin considerar si un target ya fue escaneado recientemente o si tiene baja prioridad.
- **Alternativas consideradas**:
  1. **Cooldown por target + priorización (elegido)** — Saltar targets escaneados hace < 1 hora, ordenar por prioridad RewardLearner
  2. Intervalos fijos (original) — Simple pero ineficiente
  3. Cola de prioridad con backpressure — Más complejo, mejor para escala
- **Decisión**: Cooldown de 1 hora por target + ordenamiento por prioridad (ajustes de RewardLearner).
- **Impacto**:
  - Targets de alto ROI se escanean primero
  - Targets recién escaneados no se repiten
  - Compatible hacia atrás: misma API
- **Condiciones para reabrir**: Si el número de targets supera ~1000 y se necesita backpressure.

## 2026-07-06: .ai/ como fuente de verdad única

- **Problema**: La documentación del proyecto estaba dispersa en 16 archivos .md en la raíz, sin estructura ni consistencia.
- **Alternativas consideradas**:
  1. **Directorio .ai/ dedicado (elegido)** — Un solo lugar para toda la documentación operativa
  2. Wiki externa — Requiere conexión, fuera del repo
  3. Mantener documentación dispersa — Status quo insostenible
- **Decisión**: .ai/ contiene toda la documentación operativa. Los archivos existentes se consolidan progresivamente.
- **Impacto**:
  - Cualquier agente (OpenCode, Cline, Copilot) tiene un solo lugar que leer
  - Documentación versionada con el código
  - OpenCode configurado via `instructions` + `references`
  - Cline configurado via `.cline/rules/` que referencia .ai/
- **Condiciones para reabrir**: Si las herramientas de IA soportan un mecanismo mejor que archivos locales.

## 2026-07-06: opencode.json estabilizado a formato mínimo válido

- **Problema**: opencode.json.save contenía formato corrupto (2 JSONs concatenados) con campos no soportados (`references`, `instructions` como objetos). OpenCode rechazaba el schema.
- **Alternativas consideradas**:
  1. **Formato mínimo válido (elegido)** — Solo `instructions` array de strings. Sin `$schema` si no es verificado.
  2. Mantener `references` — No soportado por OpenCode, causa errores de schema.
  3. Migrar toda la config a Cline — Perdería integración con OpenCode.
- **Decisión**: opencode.json contiene solo `instructions` array con paths a `.ai/`. No hay lógica duplicada. `.ai/` es la única fuente de verdad.
- **Impacto**:
  - opencode.json.save eliminado
  - OpenCode referencia exclusivamente `.ai/` + skill
  - Sin campos inválidos ni estructuras no soportadas
  - Sistema listo para evolución incremental sin corrupción de config
- **Condiciones para reabrir**: Si OpenCode agrega soporte nativo para `references` o estructura de objetos en `instructions`.

## 2026-07-09: Auditoría de validación — documentar, no implementar antes del release

- **Problema**: El motor de validación no refuta hipótesis, no evalúa explicaciones alternativas, no aprende de falsos positivos.
- **Alternativas consideradas**:
  1. **Documentar limitaciones y posponer (elegido)** — Crear KNOWN_LIMITATIONS.md, agregar deuda a KNOWN_DEBT.md, mover mejoras a v3.1
  2. Implementar detección de recursos públicos + campo uncertainties — Mejora parcial pero aumenta alcance del release
  3. Reescritura del pipeline de validación — Violaría DO-NOT-TOUCH, aumenta complejidad
- **Decisión**: Cerrar v3.0.0 con el pipeline actual. Las mejoras de razonamiento son para v3.1 (ORION Reasoning Layer).
- **Impacto**:
  - Los findings automatizados requieren revisión humana (ya documentado)
  - El pipeline actual es honesto sobre sus limitaciones
  - Los falsos positivos siguen siendo responsabilidad del humano
- **Condiciones para reabrir**: Cuando se inicie v3.1.

## 2026-07-06: API keys del frontend separadas a sessionStorage

- **Problema**: API keys (openai, gemini, wallet, bank) almacenadas en localStorage, exfiltrables via XSS.
- **Alternativas consideradas**:
  1. **sessionStorage (elegido)** — Se limpia al cerrar pestaña. Mitigación parcial.
  2. Backend IdentityVault — La solución correcta pero requiere cambios de API
  3. No cambiar — Riesgo continuo
- **Decisión**: Mover API keys a sessionStorage como mitigación temporal. La solución permanente es almacenarlas en el backend via IdentityVault.
- **Impacto**: Las keys sobreviven refrescos de página pero no a nuevas pestañas.
- **Condiciones para reabrir**: Inmediatamente — esta es una solución temporal. La solución definitiva requiere endpoints de API para gestionar keys.

## 2026-07-09: ORION Hypothesis Challenger — razonamiento previo a validación

- **Problema**: El pipeline de validación ejecutaba hipótesis sin cuestionarlas. No consideraba explicaciones alternativas, no diseñaba contrapruebas, no explicitaba qué no se verificó. El sistema razonaba linealmente (hipótesis → validar → decidir) en vez de cíclicamente (hipótesis → cuestionar → diseñar contraprueba → validar → reinterpretar).
- **Alternativas consideradas**:
  1. **HypothesisChallenger como capa insertada (elegido)** — ~250 líneas nuevas, 0 regresiones, 393 tests pasan. Se inserta entre HypothesisEngine y ValidationLoopEngine. No modifica replayer, rules, ni hypothesis generators.
  2. Refactor del pipeline completo — Violaría DO_NOT_TOUCH (replayer/rules estables). Riesgo alto.
  3. Solo documentar — Deuda existente en KNOWN_DEBT.md, pero la implementación era directa y bajo riesgo.
- **Decisión**: Insertar HypothesisChallenger en loop_engine.evaluate(). El challenger genera alternative_explanations, contradiction_tests con info_gain, missing_verifications, y uncertainty_level antes de la validación. El uncertainty_level se traduce a uncertainty_penalty (0.0–0.12) que descuenta del confidence score.
- **Impacto**:
  - Los reportes ahora incluyen "falta verificar X, considerar Y como explicación alternativa"
  - El confidence score refleja incertidumbre no resuelta (penalización)
  - El humano ve qué no se verificó, no solo el score final
  - 0 regresiones: el parámetro vulnerability_type tiene default "unknown" que da genéricos
- **Condiciones para reabrir**: Si se necesita que el Challenger ejecute los contradiction_tests automáticamente (hoy solo los diseña y recomienda). Eso requiere integrar con replayer como mutaciones adicionales.

## 2026-07-11: RC1 — De construir a operar

- **Problema**: ORION había acumulado 12+ dominios funcionales (Core, CATEYE, ATLAS, ODYSSEY, HERMES, AEGIS, Copilot, Companion, Workflows, Unified Memory, Health Center, Mission Control). El instinto natural era seguir agregando módulos. Sin embargo, el sistema ya cubre todo el flujo diario del usuario.
- **Alternativas consideradas**:
  1. **Congelar desarrollo, operar durante semanas reales (elegido)** — El mayor valor no viene de nuevas features sino de confiar en el sistema durante uso real continuo. Medir por indicadores operativos (días sin incidentes, tiempo hasta revisar MC < 1 minuto, clics reducidos).
  2. Seguir agregando módulos — Aumenta complejidad sin cerrar loops funcionales. Infla el proyecto sin validar lo existente.
  3. Time Machine / Sandbox / Observatorio — Ideas valiosas para RC2/RC3, no para RC1. Implementar ahora distrae de la validación operativa.
- **Decisión**: RC1 congelado. No se escribe una línea de código nuevo que no sea corrección de bug, seguridad o rendimiento. El proyecto entra en fase operativa mínima 2-4 semanas. Después se evalúa qué mejoras (solo Time Machine, Sandbox, Observatorio) justifican RC2.
- **Impacto**:
  - El usuario pasa de "operador manual" a "estratega" — solo decide, prioriza, aprueba, descarta
  - El sistema se evalúa por resultados observables (dinero generado, tiempo ahorrado, automatizaciones ejecutadas), no por cantidad de código
  - ORION se convierte en un "sistema operativo de trabajo" que envejece bien
- **Filosofía registrada**: ORION no crece por expansión. Crece por consolidación. Cada clic innecesario que desaparece vale más que veinte features nuevas. Dentro de 5 años ORION funciona no por sus miles de líneas sino porque tiene configuración portable, backups, export/import, plugins, mantenimiento, rollback, auditoría, Health Center, Update Manager y Mission Control.

## 2026-07-21: Hermes CLI + FCC Proxy — Reparación de integración

- **Problema**: Hermes CLI mostraba HTTP 404 al intentar usar el FCC Proxy. Causa raíz: tres errores simultáneos:
  1. `provider: github-copilot` → Hermes usaba `api_mode = "chat_completions"` (OpenAI format). FCC Proxy sirve Anthropic Messages API. 404 inevitable.
  2. `base_url: http://localhost:8082/v1` → El SDK Anthropic de Hermes añade `/v1/messages` al base_url, resultando en `http://localhost:8082/v1/v1/messages`.
  3. `model: gpt-5.4` → No existe en el catálogo del proxy.
- **Diagnóstico**:
  - OpenCode usa `provider.anthropic.options.baseURL: "http://localhost:8082"` (sin `/v1`, provider type `anthropic`)
  - Cline usa `base_url: http://localhost:8082`, provider `Anthropic`
  - FCC Proxy sirve `POST /v1/messages` y `POST /messages` (alias sin prefijo) — ambos Anthropic Messages API
  - Health endpoint `GET /health` no requiere auth (confirmado en `routes.py` línea 182)
  - Auth vía `x-api-key` header
- **Solución aplicada**:
  - `~/.hermes/config.yaml`: `provider: github-copilot` → `anthropic`, `base_url: .../v1` → `http://localhost:8082`, `model: gpt-5.4` → `claude-sonnet-4.5`
  - `~/start_proxy.sh`: Reesrito con `nohup` + health check loop + PID file. El anterior usaba `exec setsid ... & disown` que no persistía.
  - `~/.orion/config.sh`: Agregadas funciones `orion_start_proxy()`, `orion_stop_proxy()`, `orion_health_hermes()`, `orion_hermes_chat()`
  - `~/.local/bin/orion`: Agregados subcomandos `proxy` (start/stop/status/restart/logs) y `hermes` (status/chat/config/logs)
- **Verificación**:
  - `hermes chat -q "..."` → Responde correctamente vía proxy (27s primera respuesta)
  - `orion proxy status` → Proxy ✓ en localhost:8082
  - `orion hermes status` → Provider: Anthropic, Model: claude-sonnet-4.5
  - `orion doctor` → API /v1/messages ✓
- **Archivos modificados**:
  - `~/.hermes/config.yaml` (config fix)
  - `~/start_proxy.sh` (reliable launcher)
  - `~/.orion/config.sh` (helper functions, +HERMES_HOME, +desktop helpers)
  - `~/.local/bin/orion` (proxy + hermes + desktop commands)

## 2026-07-21: Hermes One Desktop — Integración con FCC Proxy

- **Problema**: Hermes Desktop (Electron app) necesita usar el mismo FCC Proxy que el CLI.
- **Diagnóstico**: El Desktop app lanza `hermes serve` como subproceso, que lee `~/.hermes/config.yaml`. Como el CLI fix ya corrigió el config.yaml, el desktop hereda automáticamente la configuración del proxy. No requiere configuración separada.
- **Verificación**:
  - `hermes serve --status` confirma `config_path: /home/adrie/.hermes/config.yaml`
  - `orion status` → Hermes Dsk ✓
  - El backend serve responde en `/api/status` con versión 0.18.2
- **Config adicional aplicada**:
  - `~/.orion/config.sh`: `HERMES_HOME` explicitado, funciones `orion_health_desktop()`, `orion_desktop_build()`, `orion_desktop_launch()`, `orion_desktop_serve()`
  - `~/.local/bin/orion`: Nuevo subcomando `desktop` (status|build|serve|launch|logs). Integrado en `status` y `doctor`.
- **Arquitectura**:
  ```
  Hermes Desktop (Electron)
    → spawns `hermes serve` (JSON-RPC/WS gateway)
      → reads ~/.hermes/config.yaml
        → provider: anthropic, base_url: http://localhost:8082
          → FCC Proxy → OpenRouter / Claude
  ```

## 2026-07-22: Hermes Proxy Lock — Protección arquitectónica contra fugas de provider

- **Problema**: Hermes escapaba del FCC Proxy. Cuando el usuario ejecutaba `/model <nombre>`, el resolver de `switch_model()` encontraba el modelo en OpenRouter y cambiaba `provider` silenciosamente, causando HTTP 402 (sin créditos) y pérdida del proxy.
- **Causa raíz**: El sentinel `~/.orion/proxy_mode` existía como señal bash pero Hermes no lo leía. No había ninguna barrera en el código de Hermes que impidiera cambiar provider/base_url/api_key.
- **Decisión**: Agregar `_is_proxy_locked()` que lee `~/.orion/proxy_mode`. En `switch_model()`:
  1. Si proxy locked y `--provider` dado → error inmediato
  2. Si proxy locked y el resolver cambió provider → forzar de vuelta a `current_provider`
  3. Como consecuencia, `provider_changed=False` → solo persiste `model.default` en config
- **Archivos modificados**: `~/.hermes/hermes-agent/hermes_cli/model_switch.py`
- **Cambios**:
  - `_is_proxy_locked()`: chequea existencia de `~/.orion/proxy_mode`
  - Guard en PATH A: `--provider` bloqueado cuando proxy locked
  - Guard post-resolución: fuerza `target_provider = current_provider` si proxy locked
  - `_resolve_alias_global()`: resuelve aliases (sonnet→claude-sonnet-5) contra el catálogo nativo sin cambiar provider
- **Modos válidos**:
  ```
  FCC MODE (proxy_mode presente):
    provider: anthropic (fijo)
    base_url: http://localhost:8082 (fijo)
    /model cambia solo model.default

  OPENCODE FREE MODE (proxy_mode ausente):
    provider: opencode built-in
    modelos: deepseek, nemotron, mimo
  ```
- **Próximo**: ~~FCC Proxy tiene un bug de shutdown espontáneo~~ **RESUELTO 2026-07-22**.
- **Causa raíz del shutdown**: No era bug del proxy. OpenCode usa la herramienta Bash con timeout. Al expirar el timeout, el shell session completo recibe SIGTERM. `nohup` solo bloquea SIGHUP, pero uvicorn registra un handler de SIGTERM que ejecuta `server.should_exit = True` → shutdown clean. El proxy no se "caía solo": lo mataba el timeout del Bash tool.
- **Fix**: `~/start_proxy.sh` cambió de `nohup` a `setsid -w`. `setsid` crea un nuevo session/process group completamente independiente. Cuando el shell padre muere, el proceso setsid no recibe ninguna señal. Es inmune.
- **Verificación**: Proxy estable > 30 min (PID 132680), múltiples /health requests sin shutdown, 473 modelos disponibles vía `/v1/models`.

## 2026-07-24: Revenue Intelligence — USD/hour + dynamic platform speed

- **Problema**: El scheduler priorizaba targets por severidad o EV genérico, pero no sabía cuánto USD/hora real había generado cada plataforma ni cuánto tiempo tomaban los pagos.
- **Decisión**: `RevenueMetrics.usd_per_hour()` computa USD/h desde payout history. `platform_speed_days()` extrae velocidad real por plataforma desde datos de payout. `TargetPrioritizer._estimate_speed()` usa datos dinámicos con fallback a hardcoded. `PriorityResult.usd_per_hour` expone el ratio reward/horas estimadas.
- **Impacto**: Scheduler logea $X.XX/h en cada auto-prioritize. Targets rankeados por USD/hora real, no por CVSS.

## 2026-07-24: CensysTool — REST tool siguiendo patrón ShodanTool

- **Problema**: Censys existía como `CensysClient` en `cores/recon/osint_api.py` (httpx async) y vía `uncover` CLI, pero no como tool standalone registrada en `TOOL_REGISTRY`.
- **Decisión**: Crear `CensysTool` en `cores/tools/censys.py` siguiendo el patrón exacto de `ShodanTool`: `BaseTool`/`UnifiedResult`, `urlopen` sin dependencias externas, `is_available()` chequea `CENSYS_API_KEY` + `CENSYS_API_SECRET`. `search_hosts()`, `host_view()`, `domain()`, `certificates()`.
- **Impacto**: Aparece automáticamente en TOOL_REGISTRY, disponible para pipeline y API.

## 2026-07-24: Crypto Technical Analysis desde CoinGecko

- **Problema**: CoinGeckoFeed tenía precios y 24h change pero no indicadores técnicos para trading signals.
- **Decisión**: Agregar funciones puras `compute_rsi()`, `compute_sma()`, `compute_macd()` + método `get_technical_signals()` que fetches OHLC de CoinGecko y devuelve interpretación (oversold/overbought, trend, MACD bullish/bearish).
- **Impacto**: Sin nuevas dependencias. RSI/SMA/MACD desde datos históricos gratuitos.

## 2026-07-24: Smart Notifications — IntelligentNotificationManager conectado a EventBus

- **Problema**: El `IntelligentNotificationManager` existía pero no estaba conectado a los eventos del sistema.
- **Decisión**: Suscribir 14 eventos clave (finding:*, opportunity:*, report:*, system:*, financial:* revenue:*, acceptance:*) al manager. Agregar endpoints GET `/api/notifications/smart`, GET+POST `/smart/config` para consultar estadísticas y ajustar nivel de detalle.
- **Impacto**: Notificaciones inteligentes con prioridad automática, dedup semántico, digest, y emoji enrichment sin intervención manual.

## 2026-07-25: FCC Multi-Provider 24/7 Router

- **Problema**: FCC proxy dependía de un solo provider (OpenRouter). Si rate limit o outage, el agente muere.
- **Decisión**: Configurar FCC como router multi-provider con providers gratuitos.
- **Estado actual (2026-07-26)**: **0 API keys configuradas**. Todos los 24 providers remotos están en `missing_key`. FCC solo rutea a Ollama local. Las API keys previamente configuradas se perdieron (probablemente al sobrescribir `.env`).
- **Fix aplicado**: Patch en `profiles.py` Groq profile — `disabled_value=None` para evitar `reasoning_effort` no soportado.
- **Archivos modificados**:
  - `/home/adrie/free-claude-code/.env` — routing actualizado a qwen2.5:3b-instruct
  - `/home/adrie/free-claude-code/src/free_claude_code/providers/openai_chat/profiles.py` — Groq reasoning fix
  - `/home/adrie/.config/opencode/config.json` — provider anthropic → FCC, ollama → qwen2.5:3b-instruct
  - `/home/adrie/.hermes/config.yaml` — provider fcc + fallback ollama + qwen3.5:cloud
- **Impacto**: OpenCode, Hermes y Cline usan FCC como router central. FCC rutea todo a Ollama local. Sin API keys externas, no hay acceso a Groq/SambaNova/Gemini.

## 2026-07-26: Infra Stabilization — Ollama único + FCC proxy purificado

- **Problema**: Múltiples modelos locales ocupaban ~8 GB, el FCC ruteaba a modelos inexistentes, y las API keys de providers externos se habían perdido.
- **Diagnóstico**:
  - Ollama: solo `qwen2.5:3b-instruct` (1.9 GB) + `qwen3.5:cloud` (remoto 346 bytes). Los modelos antiguos (qwen3:14b, freehuntx/qwen3-coder, hermes-orion, moondream) ya no estaban.
  - FCC `.env`: todos los tier apuntaban a `ollama/freehuntx/qwen3-coder:8b` (inexistente)
  - OpenCode config: provider ollama listaba modelos inexistentes
  - Hermes: config correcta, solo agregar `qwen3.5:cloud`
  - Cline: configurado vía FCC, sin cambios necesarios
  - GPU AMD RX 6600: sin drivers ROCm, sin `/dev/dri/`, sin amdgpu module — CPU only
- **Cambios realizados**:
  - `~/.fcc/.env` + `free-claude-code/.env`: MODEL → `ollama/qwen2.5:3b-instruct` (los 5 tiers)
  - `~/.config/opencode/config.json`: modelo ollama → `qwen2.5:3b-instruct`
  - `~/.hermes/config.yaml`: agregado `qwen3.5:cloud` a ollama-launch models
- **Arquitectura final**:

  ```
  ┌─ OpenCode ────┐  ┌─ Hermes ──────┐  ┌─ Cline ───────┐
  │ anthropic:FCC │  │ opencode:free │  │ anthropic:FCC │
  │ ollama:local  │  │ fallback:FCC  │  │               │
  └───────────────┘  │ fallback:Oll  │  └───────────────┘
                     └───────────────┘
                          │
                     ┌────▼────┐
                     │  FCC    │  :8082
                     │ Proxy   │  (0/24 providers)
                     └────┬────┘
                          │
                     ┌────▼────┐
                     │ Ollama  │  :11434
                     │ qwen2.5  │  3B, CPU, 32K ctx
                     └─────────┘
  ```

- **API keys necesarias para cobertura 24/7**:
  | Provider | Key | URL obtener |
  |----------|-----|-------------|
  | Groq | `GROQ_API_KEY` | https://console.groq.com/keys |
  | SambaNova | `SAMBANOVA_API_KEY` | https://cloud.sambanova.ai/apis |
  | Gemini | `GEMINI_API_KEY` | https://aistudio.google.com/ |
  | OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
  | OpenCode Zen | `OPENCODE_API_KEY` | https://opencode.ai/auth |
- **Próximo**: Configurar al menos 1 API key externa (Groq o Gemini) en la admin UI de FCC para recuperar el multi-provider.
- **Verificación**: Los 8 tests de componentes pasan. Ollama responde. FCC health ok. OpenCode config limpio. Hermes fallback chain correcto.

## 2026-07-26: OWNEX — Rebranding estratégico del ecosistema

- **Problema**: El ecosistema se llamaba técnicamente "Rastro" pero con identidad visual fragmentada (CATEYE backend, ORION frontend, ATLAS/ODYSSEY/AEGIS apps). No había una identidad unificada que comunicara el propósito real del sistema: un sistema operativo personal de generación de ingresos, no un tool de bug bounty.
- **Alternativas consideradas**:
  1. **OWNEX (elegido)** — "Personal Autonomous Work Operating System". Comunica el propósito completo. No es un bot, no es un dashboard, no es un gestor financiero. Es un orquestador de oportunidades.
  2. Mantener Rastro/CATEYE — No comunica la expansión a Dev Bounty, AI Work, Wealth, Intelligence.
  3. ORION como marca única — Conflicto con ORION coordinator; ORION es el coordinador IA, no el ecosistema.
- **Decisión**: OWNEX como identidad del ecosistema completo. Backend sigue siendo Rastro internamente (carpetas, imports). Frontend se rebrandea a OWNEX (títulos, splash, sidebar, paleta). Los módulos existentes se mapean a Work Cycles:
  - Rastro → Security (bug bounty)
  - Forge → Dev Bounty (nuevo)
  - Pulse → AI Work (nuevo)
  - Vault → Wealth (Capital existente expandido)
  - Atlas → Intelligence (nuevo)
  - Orion → Coordinator IA (existente)
- **Paleta OWNEX**: Negro (#050505) 90%, Azul (#3b82f6) como primario, Blanco (#f0f0f0) texto, Dorado (#f59e0b) objetivos importantes. Solo verde/rojo/amarillo para estados.
- **Impacto**:
  - Frontend: 7 archivos modificados (style.css, App.vue, AppSidebar.vue, OrionSidebar.vue, SplashScreen.vue, MissionControl.vue)
  - Backend: 0 cambios (solo branding visual)
  - Backward compatibility: todas las rutas existentes funcionan igual
  - Próximo: implementar adaptadores para Forge (Superteam, Opire, TaskBounty) y Pulse (Outlier, DataAnnotation, Mindrift)
- **Condiciones para reabrir**: Si se decide renombrar también el backend (carpetas, paquetes, clases). Para eso se necesita un refactor mayor y no aporta valor inmediato.

## 2026-07-25: Frontend Consolidation — 50+ páginas → 8 secciones

- **Problema**: ~50 páginas Vue fragmentadas sin estructura jerárquica. Router de 483 líneas con rutas planas. 5 páginas de revenue duplicadas (RevenueDashboard, RevenueMultiplier, MoneyRadar, Capital, FinancialTruth). Sidebar con solo 3 ítems principales.
- **Alternativas consideradas**:
  1. **Consolidación por secciones (elegido)** — 8 secciones principales con router anidado. Redirecciones de legacy. Sidebar unificado con 40+ ítems.
  2. Rewrite total — Riesgo alto, destruye funcionalidad existente sin beneficio inmediato.
  3. Agregar más páginas — Infla el problema. Status quo empeora.
- **Fases ejecutadas**:
  - **Fase 1**: Capital.vue — 5 páginas de revenue fusionadas en 1 dashboard con tabs. APIs: capital-dashboard, summary, platform-speed, ev-ranking.
  - **Fase 2**: Router 50→8 secciones + Sidebar con 40+ ítems organizados + 79 redirecciones legacy.
  - **Fase 3**: Baby Mode con HUNT Button — Botón central que ejecuta POST /api/hunt/start y muestra progreso en vivo vía polling.
- **Cambios**: `frontend/src/router/index.ts` (→495L jerárquico), `OrionSidebar.vue` (8 grupos), `Capital.vue` (700L nuevo), `BabyMode.vue` (hunt integrado con API real).
- **Backend**: `_current_stage_name` tracking en ScanScheduler + GET /api/pipeline/stages para progreso granular.
- **Impacto**:
  - Navegación predecible: misión → inteligencia → targets → reportes → capital → operaciones → integraciones → copiloto
  - Mantenibilidad: agregar ruta nueva es agregar child en sección correspondiente
  - 0 regresiones: todas las rutas legacy redirigen a sus equivalentes nuevos
  - `_set_stage()` en scheduler expone progreso real a frontend
- **Condiciones para reabrir**: Si se identifica una sección que no encaja en las 8 actuales. Probable cuando crezca el ecosistema ORION.

## 2026-07-26: Knowledge Engine RFC — especificar, no implementar

- **Problema**: El sistema de memoria `.ai/` crece orgánicamente sin un filtro que decida qué se conserva, qué se resume, qué se promueve a permanente y qué se descarta. Sin este filtro, en 6-12 meses MEMORY.md será un archivo más en archived/.
- **Alternativas consideradas**:
  1. **RFC como diseño (elegido)** — Documentar la arquitectura de la Knowledge Engine como RFC. No escribir código. El RFC servirá como blueprint cuando OWNEX Fase 3 lo requiera.
  2. Implementar ahora — Infraestructura sin consumidor. El sistema hoy procesa ~1 sesión/día. La Knowledge Engine necesita escalar a miles de entradas para justificar su existencia.
  3. Ignorar — Deuda diferida. Se corre el riesgo de que dentro de 3 meses alguien (o una IA) implemente algo incompatible con la visión.
- **Decisión**: Crear `.ai/RFC_KNOWLEDGE_ENGINE.md` como documento de diseño. La implementación se prioriza como Fase 6 de OWNEX, después de Work Cycles (Fase 5) y cuando el volumen de conocimiento generado supere la capacidad de lectura humana.
- **Impacto**:
  - La visión arquitectónica queda registrada y congelada
  - Cualquier implementación futura debe ajustarse al RFC
  - No se escribe código nuevo, no se añaden dependencias, no hay deuda técnica
- **Condiciones para reabrir**: Cuando se inicie la Fase 6 de OWNEX, o antes si el sistema empieza a generar más de 10 entradas de conocimiento significativas por día.

## 2026-07-28: Loop Engineering — patrones autónomos como infraestructura de Work Cycles

- **Problema**: Los OWNEX Work Cycles (Security, Forge, Pulse, Vault, Atlas, Odyssey) se ejecutan vía Scheduler pero sin un framework estandarizado de fases, estados, skills, ni OODA loop. Cada ciclo implementa su propia lógica ad-hoc, impidiendo reutilización, auditoría y aprendizaje transversal.

- **Alternativas consideradas**:
  1. **Integrar loop-engineering como framework de patrones (elegido)** — Adoptar la taxonomía de patrones, fases, skills, y OODA loop del ecosistema https://github.com/cobusgreyling/loop-engineering. Crear un adaptador Python (`core/loop/`) que mapea conceptos de loop-engineering a componentes OWNEX.
  2. Framework propio desde cero — Duplica trabajo. loop-engineering ya tiene patrones validados (daily-triage, pr-babysitter, ci-sweeper) + CLI tools (loop-init, loop-audit, loop-cost, loop-doctor).
  3. Sin framework — Status quo. Cada Work Cycle sigue siendo ad-hoc, sin fases comunes, sin OODA loop, sin scoring transversal.

- **Decisión**: Integrar loop-engineering como capa de patrones autónomos. Crear `core/loop/` con:
  - `models.py`: LoopPattern, Phase, PatternRisk, LoopState, LoopRunResult — dataclasses que modelan patrones de loop-engineering
  - `engine.py`: LoopEngine — runner con Scheduler + EventBus, ejecuta fases en orden, publica eventos en cada transición
  - `registry.py`: PatternRegistry + 6 patrones OWNEX (ownex:security, ownex:forge, ownex:pulse, ownex:vault, ownex:atlas, ownex:odyssey)
  - `startup.py`: init_loop_engines() — wired en api/main.py lifespan, get_loop_status() — expuesto en GET /system/health
  - 7 SKILL.md: loop-triage + 6 Work Cycles específicos

- **Impacto**:
  - Cada Work Cycle tiene un LoopPattern con fases definidas, cadencia, risk level, human gates, y budget
  - El scheduler ejecuta LoopEngine.run() en cada tick del patrón
  - El EventBus recibe eventos `loop:{pattern}:{phase}` en cada transición
  - El Health API expone `loop_engines` con estado, score 0-100, última ejecución
  - Skills OWNEX en `skills/` listos para OpenCode/agentes
  - 0 regresiones: core/loop/ es aditivo, no modifica nada existente
  - 650+ líneas Python nuevas, todas lint clean

- **Condiciones para reabrir**: Si loop-engineering publica breaking changes en su CLI/format, o si los patrones existentes requieren nuevas fases (ejecución paralela, sub-loops anidados, triggers externos).

## 2026-08-01: Brand Identity v3 — "The Aperture Nexus" (rebuild total)

- **Problema**: La identidad v2 (hexágono + diamante + cerebro, estética "AI-generated") fue rechazada por el usuario: se veía como colección de imágenes generadas, no como identidad de startup comercial (referencia: Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation). Además el pipeline ComfyUI/FLUX exigía GPU NVIDIA 12GB+ inexistente en el equipo (AMD RX 6600 sin ROCm) — no reproducible.

- **Alternativas consideradas**:
  1. **Pipeline vectorial determinista (elegido)** — Python + cairosvg + Pillow + fontTools. Geometría exacta programática, 100% reproducible sin GPU, fonts SIL OFL vendored, texto renderizado con PIL (cairosvg no soporta fuentes en `<text>` → se parsea el SVG, se quita `<text>` y se compone con PIL).
  2. Mantener v2 con ajustes menores — El usuario pidió explícitamente rebuild ("no me interesa mantener nada de la v2").
  3. AI image generation (Stable Diffusion/FLUX) — Rechazado: el rechazo de v2 fue precisamente por ese look; además requería GPU ausente.

- **Decisión**: Marca v3 "The Aperture Nexus": anillo octagonal (instrumento de precisión) + X de rayos cónicos desde nodo cuadrado central (inteligencia en el núcleo), con rayo que rompe el anillo arriba-derecha (evolución núcleo→edge). Dos ediciones conectadas: ALPHA (desktop, cyan→blue) y OMEGA (mobile/wear, emerald→cyan) — misma geometría, distinto color. Tokens en `assets/branding/design-tokens.json` (SSOT). Todo el pipeline vive en `scripts/brand/` (6 módulos). Assets en `assets/{logos,banners,concepts,desktop,mobile}/`. README reconstruido startup-grade (inglés, sin claims fantásticos).

- **Impacto**:
  - 37+ archivos de marca nuevos (SVG + PNG), todos verificados por muestreo de píxeles por región
  - 30+ scripts legacy v2 + `.ai/brand/` (ComfyUI) eliminados — un solo pipeline SSOT
  - README con claims creíbles (sin tablas de ingresos irreales que delataban hobby)
  - 0 regresiones: backend/frontend intactos; solo branding + docs
  - Fuentes vendored (SIL OFL) → renders deterministas sin dependencia de red
  - Storyboard de trailer 90s (8 escenas) en `assets/video/trailer-storyboard.md`

- **Condiciones para reabrir**: Si el usuario cambia la dirección creativa (nuevo mark), o si se necesita una familia extendida (submarcas por departamento, iconos de ciclo). El pipeline `scripts/brand/` permite regenerar todo el sistema cambiando solo `pipeline.py` + `design-tokens.json`.

## 2026-08-01: Direct Work Engine — barrera como espectro, no como promesa

- **Problema**: La visión "Zero Barrier" prometía "0 barrera de entrada" como si existiera en todo el mercado. Eso no es cierto en muchas áreas. Además `cores/direct_work_engine/` era un módulo fantasma: su `__init__.py` declaraba imports (`models`, `discovery`, `scoring`, `recommendation`, `profile_builder`, `engine`) a archivos inexistentes — `import` rompía con `ModuleNotFoundError`. Por otro lado, `RevenueTracker.is_zero_barrier()` trataba la barrera como **boolean** (todo o nada).

- **Alternativas consideradas**:
  1. **Score continuo 0-100 (elegido)** — La barrera es un espectro: OWNEX busca, filtra y prioriza oportunidades con la MENOR barrera (sin entrevista cuando exista, sin portfolio si es opcional, registro rápido, pago internacional, remoto). Nunca promete "cero barrera garantizado". El `ZeroBarrierScorer` pondera 15 factores (suma 1.0) y el `IntelligentRecommender` ordena por ingreso esperado > aceptación > menor barrera > compatibilidad > velocidad > reputación, con diversidad y penalización por riesgo.
  2. Mantener el boolean existente — No rankea, no discrimina, contradice la visión.
  3. Poblar solo el scorer — Deja sin motor de decisión ni discovery.

- **Decisión**: Poblar el módulo fantasma `cores/direct_work_engine/` como motor desacoplado (sin imports a `core/`): `models` (Opportunity con 18+ campos de barrera, GameDevSpecialization solo-programación, UserProfile expandido, RankedOpportunity), `scoring` (espectro 0-100 + enablers/blockers/reasoning), `recommendation` (config con pesos validables + strategy personalizada), `discovery` (async, adapters por plataforma con aislamiento de errores), `engine` (orquesta discover→score→recommend→stats), `profile_builder` (solo datos reales, nunca inventar). Game Development como categoría obligatoria que **excluye arte** (concept/character/environment/UI art, animación artística) e incluye solo programación. Fixes al diseño concurrente: pesos que sumaban 1.10 → 1.0 + normalización defensiva; `enablers`/`blockers` agregados a `ZeroBarrierScore`; `__post_init__` tolera specialization como string.

- **Impacto**:
  - `import cores.direct_work_engine` OK (antes roto); `tests/test_direct_work_engine.py` 28 passed; ruff limpio
  - El diferenciador OWNEX queda explícito: "de miles de oportunidades, estas tres son las más probables de cobrar esta semana, en este orden" — motor de decisión, no acumulación de módulos
  - Módulo NO montado aún en `api/main.py` (sin adapters reales registrados) — próximo paso natural: adapters Algora/Opire/Freelancer existentes vía `register_adapter`  - 0 regresiones: no toca `core/`, `api/` ni otros módulos; solo se pobló el fantasma

- **Condiciones para reabrir**: Cuando se registren adapters reales de discovery, cuando se monte el router en `api/main.py`, o si se requiere que el scorer reaccione al historial real de payout del usuario (feedback loop de Memory System).

## 2026-08-01: Direct Work Engine — feedback loop + clasificación de modelos de mercado

- **Problema**: El DWE rankeaba oportunidades sin aprender de los outcomes reales (el scorer no conocía qué plataformas/categorías cobran más). Además la visión OWNEX 2035 exige distinguir los **modelos de mercado** (empleo clásico vs freelance vs bounties vs bug bounty vs OSS vs AI tasks vs competencias): las tareas públicas ("¿podés resolver esto?") son más objetivas que los procesos de selección ("¿quién sos?") y deben priorizarse, pero eso no estaba explicitado en el motor.

- **Alternativas consideradas**:
  1. **Feedback loop con historial real (elegido)** — `feedback.py` con `LearningRecord` (platform, category, accepted, amount, time_to_payout_days), `apply_learning()` que pliega outcomes verificados (accepted/paid vs failed/cancelled; pending/reviewing NO cuentan) en `UserProfile.platform_success_rates`/`category_success_rates`/`total_earnings`/`avg_time_to_payment_days`, y `build_history_from_revenue_tracker()` que deriva records desde el RevenueTracker real. Historial vacío = no-op (nunca inventa tasas). El recommender YA lee esas tasas (`_calculate_acceptance_probability`), así el motor mejora con cada cobro/rechazo.
  2. Scorer que adivine tasas por defecto — Contradice "nunca inventar información". Descartado.
  3. Solo documentar la visión — No cierra ningún loop medible.

- **Decisión**: Implementar feedback loop + `EMPLOYMENT_TYPE_MODEL`/`opportunity_model()`/`is_outcome_based()` (7 modelos de mercado, expuestos en `recommendation_reasoning` y strategy "Outcome-based: deliver the result"). `DirectWorkEngine.learn()` como entrada única. Vision 2035 registrada en `.ai/STRATEGIC_VISION.md`.

- **Impacto**:
  - El motor aprende de datos reales: `platform_success_rates`/`category_success_rates` alimentan la probabilidad de aceptación → ranking más honesto con cada ciclo
  - OWNEX distingue explícitamente "mundo resultado" (bounty/microtask/prize) vs "mundo selección" (empleo/freelance) y prioriza las tareas públicas de menor barrera
  - `tests/test_direct_work_engine.py` 28 → 35 (feedback loop con RevenueTracker, nunca inventa, clasificación de modelos); ruff limpio
  - 0 regresiones: módulo desacoplado, no toca `core/`, `api/` ni otros módulos
  - `register_capabilities()` ya auto-registra `learn_from_outcomes` en CapabilityRegistry

- **Condiciones para reabrir**: Cuando se registren adapters reales de discovery (los `core/opportunity/adapters/` existentes vía `register_adapter`), cuando se monte el router/endpoint en `api/main.py`, o cuando se quiera persistir el `UserProfile` aprendido entre sesiones (hoy se reconstruye en memoria).

## 2026-08-01: Direct Work Engine — router expuesto en la API (visible en Mission Control)

- **Problema**: El motor DWE rankeaba oportunidades pero no era consumible: no había endpoints, no era visible en Mission Control. Regla del proyecto: "si no es visible, no existe".
- **Decisión**: Montar `api/routers/direct_work.py` en `api/main.py` con `GET /api/direct-work/status`, `POST /api/direct-work/score`, `POST /api/direct-work/recommend`, `POST /api/direct-work/learn`. Serialización enum-aware (dict ↔ dataclass) en el router, manteniendo los modelos del DWE puros. Sin auto-submisión: enviar info personal sigue requiriendo aprobación (Human Control Layer).
- **Impacto**:
  - El pipeline del megaprompt (Discovery → Intelligence → … → Payment Tracking) ahora tiene interfaz consumible: score/recommend/learn/status
  - `tests/test_direct_work_api.py` 5 passed con TestClient; `import api.main` OK
  - El feedback loop (`/learn`) queda accesible para alimentarse del historial real de pagos
- **Condiciones para reabrir**: Cuando se registren más adapters reales (envolver los `core/opportunity/adapters/` de Algora, IssueHunt, Freelancer a `BaseDiscoveryAdapter`), o cuando el frontend consuma estos endpoints en Mission Control.

## 2026-08-01: Direct Work Engine — primer adapter real de discovery (Opire)

- **Problema**: El DWE rankeaba oportunidades que nadie le alimentaba: sin adapters reales, `discover_all()` no producía nada. El motor de decisión no generaba valor sin datos vivos.
- **Decisión**: Crear `api/adapters/direct_work_opire.py` — `OpireDweAdapter(BaseDiscoveryAdapter)` envuelve el `OpireAdapter` legacy (API pública de Opire, auth opcional) y normaliza `RawOpportunity` → `Opportunity` (categoría dev_bounty, employment_type BOUNTY → outcome-based, difficulty inferida de effort_hours). Se registra idempotente y tolerante a errores en `get_engine()` del router. Vive en la capa API para que el DWE siga desacoplado de `core/`.
- **Impacto**:
  - `get_engine().discovery` ahora tiene OPIRE registrado → el motor puede descubrir bounties reales de Opire
  - `tests/test_direct_work_api.py` 5 → 8 (conversión mockeada, sin red; registro automático idempotente)
  - 0 regresiones: import api.main OK, ruff limpio
- **Condiciones para reabrir**: Cuando se registren más fuentes (Algora, OpenCollective, Superteam, GitHub Sponsors) o se exponga el discovery en un endpoint accionable (`POST /direct-work/discover`).

## 2026-08-01: Direct Work Engine — wrapper genérico + más fuentes reales

- **Problema**: Cada adapter real (Opire) duplicaba la conversión `RawOpportunity → Opportunity`. Envolver más plataformas multiplicaría el código copiado.
- **Decisión**: `api/adapters/legacy.py` — `LegacyOpportunityDweAdapter(BaseDiscoveryAdapter)` (un solo camino de conversión parametrizado por platform/category/employment_type) + `build_default_adapters()` que registra **opire, issuehunt y freelancer**. `OpireDweAdapter` queda como subclase fina del wrapper (DRY). Freelancer clasificado como modelo *freelance* (mundo selección); bounties como outcome-based — refuerza la clasificación de 7 modelos.
- **Impacto**:
  - El motor descubre de 3 fuentes reales: `get_engine().discovery.adapters = {opire, issuehunt, freelancer}`
  - `tests/test_direct_work_api.py` 8 → 10 (conversión mockeada sin red, clasificación freelance vs bounty)
  - 0 regresiones: 45 tests verdes, import api.main OK, ruff limpio
- **Condiciones para reabrir**: Envolver Algora/OpenCollective/Superteam, o exponer discovery accionable (`POST /direct-work/discover`), o que el frontend consuma `/recommend`.

## 2026-08-01: Vault & Atlas Cycles — 6 Work Cycles operativos (AUD-8)

- **Problema**: Solo 4 de 6 Work Cycles tenían clase de motor + router API (security, forge, pulse, direct_work). Vault y Atlas solo tenían seeds DB + scheduler jobs, sin motor ni endpoints — invisibles en Mission Control.
- **Alternativas consideradas**:
  1. **Crear clases VaultCycle/AtlasCycle + routers (elegido)** — Seguir patrón ForgeCycle/PulseCycle existente. Motor desacoplado, bookkeeping DB, knowledge capture, executive dashboard integration.
  2. Solo montar routers stub sin motor — Violaría "si no es visible, no existe" y "no mocks en producción".
  3. Unificar en un solo ciclo "Wealth+Intelligence" — Pérdida de granularidad, categorías distintas (wealth vs intelligence).
- **Decisión**: Crear `core/cycles/vault.py` (VaultCycle, priority 7) y `core/cycles/atlas.py` (AtlasCycle, priority 5) con 6 stages cada uno. Routers `vault_cycle.py` y `atlas_cycle.py` con 8 endpoints cada uno. Montados en `api/main.py`.
- **Impacto**:
  - 6 ciclos operativos: security, forge, pulse, vault, atlas, direct_work
  - `get_all_jobs()` → 27 jobs (vault:2, atlas:2, direct_work:1)
  - Executive Dashboard backend ya expone datos; frontend Mission Control puede consumir `/dashboard`, `/knowledge`, `/status`
  - 0 regresiones: patrón idéntico a forge/pulse, solo adapta platforms/sources
- **Condiciones para reabrir**: Cuando el frontend consuma estos endpoints en Mission Control, o cuando se requiera `run_pipeline()` real (hoy solo bookkeeping DB como forge/pulse).

