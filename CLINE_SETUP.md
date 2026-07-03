# Configuración de Cline para CATEYE

## 📦 Modelos

### Local — `freehuntx/qwen3-coder:8b`
- **Tamaño:** 5.2 GB (Q4_K_M)
- **VRAM:** ~5.2 GB → sobran ~2.8 GB para KV cache
- **RAM:** 32 GB disponibles → sin riesgo
- **Contexto nativo:** 40K tokens
- **Benchmarks:** HumanEval 85%+, SWE-Bench agentic
- **Por qué este:** Es el mejor modelo de código abierto para programación en 8 GB VRAM. Supera ampliamente al anterior `qwen2.5-coder:7b` en razonamiento, tool-calling y generación de código.

### Cloud gratuito — `google/gemini-2.0-flash-exp:free` (via OpenRouter)
- **Costo:** $0 (completamente gratis)
- **Contexto:** 1M tokens
- **Calidad:** Excelente para código
- **Límite:** ~20 req/min (free tier)
- **API:** OpenAI-compatible via `https://openrouter.ai/api/v1`
- **Alternativa paga pero ultra barata:** `deepseek-v4-flash` (~$0.15/MTok)

### Cloud emergencia — `google/gemini-2.5-flash` (via OpenRouter)
- **Costo:** $0.30/M input, $2.50/M output
- **Contexto:** 1M tokens
- **Calidad:** Superior, con thinking mode para tareas complejas

---

## ⚙️ Configuración en Cline

### Local (Ollama)
1. Abre Cline → icono ⚙️ → **API Provider** → **Ollama**
2. **Base URL:** `http://localhost:11434`
3. **Modelo:** `freehuntx/qwen3-coder:8b`
4. **Context Window:** `32768` (mínimo, idealmente 64000)
5. **Compact Prompt:** ✅ ON

### Cloud (OpenRouter)
1. Crea cuenta en [openrouter.ai/keys](https://openrouter.ai/keys)
2. Genera API key
3. En Cline ⚙️ → **API Provider** → **OpenRouter**
4. Pega tu API key
5. **Modelo:** `google/gemini-2.0-flash-exp:free`
6. **Context Window:** `32768`

### Emergencia
Mismo proveedor OpenRouter, cambia solo el modelo a:
- `google/gemini-2.5-flash` (recomendado, pago mínimo)
- `deepseek/deepseek-v4-flash` (ultra barato, ~$0.15/MTok)

---

## 🔄 Cambiar perfil en < 30 segundos

Cline guarda las API keys en `~/.cline/data/settings/providers.json`. Para cambiar de perfil:

### Método 1 — UI (recomendado, 10s)
1. Click en icono Cline → ⚙️
2. Cambia **API Provider** (Ollama ↔ OpenRouter)
3. Cambia **Model** si necesario
4. Click **Done**
Listo.

### Método 2 — Script (3s)
```bash
cline-switch local    # Cambia a Ollama + qwen3-coder:8b
cline-switch cloud    # Cambia a OpenRouter + Gemini 2.0 Flash free
cline-switch emergency # Cambia a OpenRouter + DeepSeek V4 Flash
```

---

## 🧠 Sistema de reglas (System Prompt)

Las reglas están en `.cline/rules/`:

| Archivo | Propósito |
|---|---|
| `core.md` | Reglas de desarrollo, stack, flujo de trabajo |
| `context.md` | Contexto del proyecto Orion (estado, módulos, URLs) |
| `orion-rules.md` | Reglas completas con referencia rápida |

Cline carga automáticamente todos los `.md` dentro de `.cline/rules/`.

---

## 🔧 Ollama optimizado para 8 GB VRAM

```bash
# Aumentar num_ctx del modelo a 32K (crítico para Cline)
ollama pull freehuntx/qwen3-coder:8b
ollama create my-coder -f - <<EOF
FROM freehuntx/qwen3-coder:8b
PARAMETER num_ctx 32768
PARAMETER num_gpu 99
EOF

# Variables de entorno para AMD ROCm
export HSA_ENABLE_SDMA=0
export OLLAMA_NUM_GPU=999
export OLLAMA_GPU_OVERHEAD=0.1
```

### Verificar que Ollama usa la GPU
```bash
ollama run my-coder "Hola, responde OK si funciono" --verbose
# Busca "llm_load_tensors: using VRAM" en la salida
```

---

## ✅ Checklist de verificación

- [ ] Ollama instalado y corriendo (`ollama serve`)
- [ ] Modelo local descargado (`ollama list`)
- [ ] GPU funcionando (AMD ROCm o Vulkan)
- [ ] Cline instalado en VS Code
- [ ] Perfil Local configurado (Ollama)
- [ ] Perfil Cloud configurado (OpenRouter + Gemini free)
- [ ] Context window ≥ 32768 configurado
- [ ] `.cline/rules/` creado y cargando en Cline
- [ ] Script `cline-switch` instalado en PATH

---

## 📚 Referencias
- [Docs oficiales de Cline](https://docs.cline.bot)
- [Ollama + Cline](https://docs.ollama.com/integrations/cline)
- [Qwen3-Coder en Ollama](https://ollama.com/library/qwen3-coder)
- [OpenRouter modelos gratis](https://openrouter.ai/collections/free-models)
- [Cline config](https://docs.cline.bot/getting-started/config)
