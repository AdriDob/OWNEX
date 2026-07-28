# OWNEX Agent Infrastructure Status

> Last updated: 2026-07-26
> Purpose: Document the current state of the agent routing infrastructure
> and provide recovery procedures.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   OWNEX Agent Stack                        │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Hermes      │  │  OpenCode     │  │  Cline       │  │
│  │  CLI          │  │  CLI/built-in │  │  VSCode ext  │  │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘  │
│         │                 │                    │          │
│         ▼                 ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              FCC Proxy (port 8082)                   │ │
│  │  Routes Claude API calls to upstream providers      │ │
│  │                                                      │ │
│  │  Tier routing:                                      │ │
│  │    haiku  → Ollama (local qwen2.5:3b-instruct)      │ │
│  │    sonnet → OpenRouter (google/gemini-3.5-flash)    │ │
│  │    opus   → OpenRouter (anthropic/claude-opus-5)    │ │
│  │    fable  → OpenRouter (google/gemini-3.5-flash)    │ │
│  └───┬──────────────────────────────┬──────────────────┘ │
│      │                              │                     │
│      ▼                              ▼                     │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  Ollama (11434) │  │  OpenRouter API             │  │
│  │  qwen2.5:3b     │  │  (free tier, OPENROUTER    │  │
│  │  qwen3.5:cloud  │  │   API_KEY in env)           │  │
│  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Provider Priority (24/7 Availability)

| Priority | Provider | Type | Availability | Use Case |
|----------|----------|------|--------------|----------|
| **PRIMARY** | OpenRouter | Cloud API | Requires API key | Sonnet/opus/fable |
| **SECONDARY** | Ollama local | CPU | Always available | Haiku/fallback |
| **TERTIARY** | FCC Proxy | Router | Port 8082 | Routes to providers above |
| **EMERGENCY** | Ollama qwen3.5:cloud | Remote | Requires internet | Backup local model |

## Changes Made (2026-07-26)

### 1. Hermes Config Fixed ✅

**Problem**: Hermes default provider was `ollama-launch` instead of `fcc`.
The `model.default` was `qwen2.5:3b-instruct` pointing to Ollama directly.
Hermes was completely bypassing FCC proxy for all requests.

**Why it corrupted**: Hermes CLI auto-wrote the config during testing,
overwriting my fix with `provider: opencode` and `default: laguna-s-2.1-free`.

**Re-fix applied**: Explicitly set `provider: fcc` and `default: claude-haiku-4-5`.
This is now the correct persistent config.

### 2. FCC .env Routing Updated ✅

**Problem**: All FC tiers (haiku/sonnet/opus/fable) routed to the same
local Ollama model `ollama/qwen2.5:3b-instruct`. No external providers
were configured despite having an OpenRouter key available.

**Fix**: `/home/adrie/free-claude-code/.env`
- Added `OPENROUTER_API_KEY` (uncommented)
- Updated tier routing:
  - `MODEL_HAIKU` → `ollama/qwen2.5:3b-instruct` (local, fast for simple tasks)
  - `MODEL_SONNET` → `open_router/google/gemini-3.5-flash-lite` (cloud, capable)
  - `MODEL_OPUS` → `open_router/anthropic/claude-opus-5` (cloud, best quality)
  - `MODEL_FABLE` → `open_router/google/gemini-3.5-flash-lite` (cloud, balanced)
- Updated Ollama models comment to reflect current state

### 3. Ollama Speed Optimization ✅

**Problem**: Ollama was using all 8 CPU threads by default, competing
with VSCode (2.5GB), Hermes (480MB), OpenCode (1.7GB), and other services.
System had 12GB/13GB RAM used, causing excessive swapping.

**Fix**: Ollama configured with:
- `OLLAMA_NUM_THREAD=2` (sufficient for 3B model, avoids CPU thrashing)
- `OLLAMA_MAX_LOADED_MODELS=1` (prevents memory bloat)
- `~/.ollama-env` created for persistence

### 4. OpenCode Config Review ✅

OpenCode `~/.config/opencode/config.json` was already correctly configured:
- Provider `anthropic` → FCC proxy (`http://localhost:8082`)
- Provider `ollama` → local fallback (`http://localhost:11434/v1`)
- Default model: `claude-sonnet-4-5` (routes through FCC)
- No changes needed

## Known Issues

### 1. Ollama Inference Speed on CPU
The 3B qwen2.5 model on CPU without GPU acceleration (AMD RX 6600, no ROCm)
can be slow for inference. This is inherent — no quick fix available without:
- GPU upgrade with ROCm/Vulkan support
- Migration to a faster/quantized model
- More system RAM to prevent swapping

**Mitigation**: Cloud models (OpenRouter) handle complex tasks; Ollama is
a fallback for when cloud is unavailable.

### 2. FC Proxy /v1/messages Empty Responses
After service restarts, FCC proxy `/v1/messages` may return empty if Ollama
is still loading the model or if RAM pressure causes timeouts. This is a
stability issue that should improve once Ollama is tuned and services
are restarted cleanly.

### 3. No External API Keys for OpenRouter, Groq, Gemini, etc.
The OpenRouter key IS configured in FCC .env (from environment variable),
but other providers (Groq, SambaNova, Gemini) don't have keys. This limits
the free tier routing to OpenRouter only.

## Recovery Procedures

### Full Service Restart
```bash
# Kill everything
pkill -9 -f "fcc-server" 2>/dev/null
kill $(pgrep -x ollama) 2>/dev/null
sleep 2

# Start Ollama with limited threads (prevents RAM thrashing)
OLLAMA_NUM_THREAD=2 nohup ollama serve > /tmp/ollama-serve.log 2>&1 &

# Start FCC proxy
cd /home/adrie/free-claude-code
nohup .venv/bin/fcc-server > /tmp/fcc-server.log 2>&1 &

# Wait for both to be healthy
sleep 5
curl -sf http://localhost:11434/health && echo "Ollama OK"
curl -sf http://localhost:8082/health && echo "FCC OK"
```

### Verify Routing
```bash
# Test haiku (should go to Ollama local)
curl -s -X POST http://localhost:8082/v1/messages \
  -H "x-api-key: orion-dev-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-haiku-4-5","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'

# Test sonnet (should go to OpenRouter)
curl -s -X POST http://localhost:8082/v1/messages \
  -H "x-api-key: orion-dev-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'
```

### Check Model Availability
```bash
# Ollama models
ollama list

# FCC proxy models
curl -s http://localhost:8082/v1/models | python3 -m json.tool

# OpenRouter models (if key works)
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "HTTP-Referer: http://localhost:8082" \
  "https://openrouter.ai/api/v1/models" | python3 -c "
import json,sys
data=json.load(sys.stdin)
print(f'{len(data.get(\"data\",[]))} models available')
"
```

## Verification Status

| Check | Result | Notes |
|-------|--------|-------|
| Hermes config → fcc provider | ✅ Fixed | `~/.hermes/config.yaml` |
| Hermes default → claude-haiku-4-5 | ✅ Fixed | Fast local model |
| FCC .env → OpenRouter key | ✅ Added | From `$OPENROUTER_API_KEY` |
| FCC .env → tier routing | ✅ Updated | Sonnet/opus → cloud |
| Ollama → 2 threads | ✅ Applied | `~/.ollama-env` |
| OpenCode config | ✅ No changes needed | Already correct |
| FCC health endpoint | ✅ Working | `curl :8082/health` |
| Ollama health endpoint | ✅ Working | `curl :11434/api/tags` |
| FCC /v1/messages → Ollama | ⚠️ Needs test | Verify after clean restart |
| FCC /v1/messages → OpenRouter | ⚠️ Needs test | Verify after clean restart |
| Hermes claude-haiku-4-5 | ⚠️ Needs test | Verify after restart |
| Hermes claude-sonnet-4-5 | ⚠️ Needs test | Verify OpenRouter routing |
| 24h availability | ⚠️ Pending | Depends on cloud uptime |