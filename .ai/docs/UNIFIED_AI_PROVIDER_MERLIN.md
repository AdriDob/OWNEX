# Unified AI Provider & MERLIN — Sistema Unificado de IA

## 🎯 PROBLEMA RESUELTO

OWNEX tenía múltiples sistemas de IA usando diferentes providers:
- AI Worker (OpenAI, Anthropic, Ollama)
- MERLIN (respuestas hardcoded)
- Copilot (OmniRoute, NVIDIA, Ollama)

**Esto causaba:**
- Inconsistencia en calidad de respuestas
- Diferentes modelos para diferentes sistemas
- Costos innecesarios (OpenAI/Anthropic pagados)
- MERLIN no usaba IA real (solo templates)

---

## 🚀 SOLUCIÓN IMPLEMENTADA

### 1. UnifiedAIProvider (Nuevo)

**Sistema unificado que usa los mismos free models que el IDE:**

**OmniRoute (Free):**
- `oc/deepseek-v4-flash-free` — DeepSeek V4 Flash (default)
- `oc/qwen3.6-plus-free` — Qwen 3.6 Plus
- `oc/minimax-m3-free` — MiniMax M3
- `aug/gemini-3.1-pro` — Gemini 3.1 Pro
- `aug/gemini-3.0-flash` — Gemini 3.0 Flash
- `groq/llama-3.3-70b-versatile` — Llama 3.3 70B via Groq
- `groq/meta-llama/llama-4-scout-17b-16e-instruct` — Llama 4 Scout
- `groq/qwen/qwen3-32b` — Qwen 3 32B
- `groq/qwen/qwen3.6-27b` — Qwen 3.6 27B
- `samba/Meta-Llama-3.3-70B-Instruct` — Llama 3.3 via Samba
- `samba/Llama-4-Maverick-17B-128E-Instruct` — Llama 4 Maverick
- `samba/DeepSeek-V3.2` — DeepSeek V3.2
- `auto/best-coding` — Auto mejor para código
- `auto/best-fast` — Auto más rápido
- `auto/best-reasoning` — Auto mejor razonamiento

**NVIDIA NIM (Free):**
- `nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2` — Mistral 8x7B
- `nv-ai-foundation-541280:llama-3.1-70b-instruct` — Llama 3.1 70B
- `nv-ai-foundation-541280:nemotron-3-ultra` — Nemotron 3 Ultra
- `nvidia/nemotron-3-ultra` — Nemotron 3 Ultra
- `meta/llama-3.1-70b-instruct` — Llama 3.1 70B

**Ollama (Local):**
- `qwen3-coder:8b` — Qwen 3 Coder 8B
- `llama3.1:8b` — Llama 3.1 8B
- `codellama:7b` — Code Llama 7B
- `mistral:7b` — Mistral 7B

**Failover Chain:**
1. OmniRoute (primary, free)
2. NVIDIA NIM (fallback, free)
3. Ollama (fallback, local)

### 2. Integración con AI Worker

**AI Worker ahora usa UnifiedAIProvider:**
- Pulse Worker (AI training tasks)
- Forge Worker (code proposals)
- Proposal Worker (freelance proposals)
- Scope Worker (scope verification)
- Triage Worker (triage responses)
- Auto Applicant (applications)

**Antes:**
```python
class LLMClient:
    def __init__(self, provider: str = "", model: str = ""):
        self._provider = provider or os.getenv("AI_WORKER_PROVIDER", "ollama")
        self._model = model or os.getenv("AI_WORKER_MODEL", "llama3.2")
```

**Ahora:**
```python
class LLMClient:
    def __init__(self, provider: str = "", model: str = ""):
        self._provider = get_unified_provider()
        self._default_model = model or "oc/deepseek-v4-flash-free"
```

### 3. MERLIN Perfeccionado

**MERLIN ahora es el personaje animado de OWNEX:**

**Características:**
- ✅ Usa UnifiedAIProvider (mismos models que IDE)
- ✅ Personalidad retro office expandida
- ✅ Respuestas generadas por IA real (no solo templates)
- ✅ Mood states (happy, focused, playful, curious)
- ✅ Retro reactions (19 referencias nostálgicas)
- ✅ Sound effects (click-click, bip-bop, beep)
- ✅ Animation states (idle, thinking, typing, success, error)
- ✅ 7 greetings diferentes con emojis
- ✅ 7 sign-offs diferentes con emojis
- ✅ 9 thinking phrases diferentes
- ✅ 7 error phrases diferentes
- ✅ 7 success phrases diferentes

**Personalidad:**
- Friendly pero profesional
- Ocasionalmente usa referencias retro (floppy disks, CRT monitors, Windows 95, Winamp, Netscape)
- Structura respuestas claramente
- Conocimiento de seguridad, automatización, AI
- F twist divertido y nostálgico

**Ejemplo de respuesta MERLIN:**
```
¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma. 🧙

Analizando tu solicitud de análisis de target... 📊

Para realizar un análisis completo, MERLIN necesita:
1. El dominio o URL del target
2. El tipo de análisis requerido (recon, attack surface, vulnerabilities)
3. El alcance del análisis

💾 MERLIN está listo para procesar esto. Proporciona los detalles y procederemos.

— Tu amigo MERLIN 💾
```

### 4. Configuración de Environment Variables

**Variables compartidas con IDE:**
```bash
# OmniRoute (default provider)
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=omniroute

# NVIDIA NIM (fallback)
NVIDIA_API_KEY=...
NIM_API_KEY=...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Ollama (local fallback)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3-coder:8b

# FCC Proxy (Claude via OpenRouter - usado por copilot)
FCC_BASE_URL=http://localhost:8082
ANTHROPIC_API_KEY=orion-dev-local
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
```

---

## 📊 VALIDACIÓN DE PROVEEDORES

### ¿Cuáles providers usa OWNEX ahora?

**Auto-reparación y trabajo:**
- ✅ OmniRoute (DeepSeek, Qwen, Gemini, Groq, Samba) — FREE
- ✅ NVIDIA NIM (Mistral, Llama, Nemotron) — FREE
- ✅ Ollama (local models) — FREE

**Copilot integrado:**
- ✅ OmniRoute (mismos models) — FREE
- ✅ NVIDIA NIM (mismos models) — FREE
- ✅ FCC Proxy (Claude via OpenRouter) — FREE

**MERLIN:**
- ✅ OmniRoute (mismos models) — FREE
- ✅ NVIDIA NIM (mismos models) — FREE
- ✅ Ollama (mismos models) — FREE

**Conclusión:** TODOS los sistemas usan los MISMOS free models que el IDE.

---

## 🎯 CÓMO USAR

### 1. Usar UnifiedAIProvider

```python
from cores.ai.unified_provider import get_unified_provider

provider = get_unified_provider()

# Chat simple
result = await provider.chat(
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"},
    ],
    model="oc/deepseek-v4-flash-free",
    max_tokens=2048,
    temperature=0.7,
)

print(result["content"])
```

### 2. Usar MERLIN

```python
from cores.merlin.system import get_merlin_system

merlin = get_merlin_system()

response = await merlin.process_message(
    message="Ayúdame a analizar este target",
    detail_level="normal",
    response_tone="professional",
    enable_analytics=True,
    enable_learning=True,
)

print(response)
```

### 3. Verificar health de providers

```python
from cores.ai.unified_provider import get_unified_provider

provider = get_unified_provider()
health = await provider.check_health()

print(health)
# {
#   "omniroute": True,
#   "nvidia": True,
#   "ollama": True,
# }
```

### 4. Listar modelos disponibles

```python
from cores.ai.unified_provider import get_unified_provider

provider = get_unified_provider()
models = provider.get_available_models()

print(models)
# [
#   "oc/deepseek-v4-flash-free",
#   "oc/qwen3.6-plus-free",
#   "nv-ai-foundation-541280:mistral-8x7b-instruct-v0.2",
#   "qwen3-coder:8b",
#   ...
# ]
```

---

## 💎 CARACTERÍSTICAS DE MERLIN

### Personalidad Expandida

**Greetings (7 variantes):**
- "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma. 🧙"
- "Bienvenido de nuevo. MERLIN está listo para asistirte. 💾"
- "MERLIN aquí. ¿En qué puedo ayudarte hoy? 🖥️"
- "¡Saludos! MERLIN reportándose para el servicio. ⌨️"
- "¡Hey! MERLIN online y listo para rockear. 🎨"
- "¡Buenos días! MERLIN a tu disposición. 📊"
- "¡Hola, humano! MERLIN listo para la acción. 🚀"

**Retro Reactions (19 variantes):**
- "🎨 ¡El estilo retro nunca muere!"
- "💾 Guardando en disquete virtual..."
- "🖨️ Imprimiendo en tu mente..."
- "📊 Gráficos generados con estilo!"
- "⌨️ Teclas mecánicas activadas..."
- "🖥️ Monitores CRT simulados..."
- "📁 Archivos organizados al estilo clásico!"
- "📀 Leyendo CD-ROM virtual..."
- "🔌 Conectando al pasado..."
- "📼 Rebobinando cinta de backup..."
- "🖱️ Click doble simulado..."
- "📟 Marcando módem..."
- "💾 Save point activado!"
- "🎮 Game over evitado!"
- "📡 Señal digital recibida!"
- "🔊 Sonido de startup de Windows 95..."
- "🖼️ Resolución de 800x600 activada!"
- "🌐 Netscape Navigator cargando..."
- "📧 Outlook Express abierto!"
- "🎵 Winamp en loop!"

**Mood States (4 estados):**
- **Happy:** "¡MERLIN está feliz de ayudarte! 😊"
- **Focused:** "MERLIN está concentrado... 🧙"
- **Playful:** "¡Vamos a rockear esto! 🎸"
- **Curious:** "MERLIN quiere saber más... 🤔"

**Sound Effects (8 variantes):**
- "🔊 *click-click*"
- "🔊 *bip-bop*"
- "🔊 *beep*"
- "🔊 *whirrr*"
- "🔊 *ding*"
- "🔊 *buzz*"
- "🔊 *chime*"
- "🔊 *clack*"

**Animation States (6 estados):**
- "idle": "🧙 MERLIN esperando..."
- "thinking": "🧙 MERLIN pensando..."
- "typing": "⌨️ MERLIN escribiendo..."
- "success": "✨ MERLIN éxito!"
- "error": "😅 MERLIN error..."
- "processing": "📊 MERLIN procesando..."

---

## 💎 CONCLUSIÓN

**SÍ, OWNEX usa los mismos free models que el IDE:**

1. **UnifiedAIProvider** — Sistema unificado
2. **OmniRoute** — Primary (DeepSeek, Qwen, Gemini, Groq, Samba) — FREE
3. **NVIDIA NIM** — Fallback (Mistral, Llama, Nemotron) — FREE
4. **Ollama** — Fallback local (Qwen, Llama, CodeLlama) — FREE
5. **AI Worker** — Usa UnifiedAIProvider
6. **MERLIN** — Usa UnifiedAIProvider + personalidad animada
7. **Copilot** — Usa OmniRoute + NVIDIA (mismos models)

**MERLIN perfeccionado:**
- ✅ IA real (no solo templates)
- ✅ Personalidad retro office expandida
- ✅ 19 retro reactions nostálgicas
- ✅ 4 mood states
- ✅ 8 sound effects
- ✅ 6 animation states
- ✅ Mismos free models que IDE
- ✅ Fallback robusto (OmniRoute → NVIDIA → Ollama)

**El personaje animado de OWNEX está completo, divertido, y usa la misma infraestructura de IA que el IDE.**
