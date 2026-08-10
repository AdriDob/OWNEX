# AI Routing Diagnostic Report — FCC, OmniRoute & NVIDIA Integration

## Executive Summary

This report documents the current state of the free model routing system in Rastro/OWNEX, covering:
- **FCC Provider** (Claude models via OpenRouter proxy)
- **OmniRoute Provider** (Multi-provider routing with health scoring)
- **NVIDIA NIM Provider** (NVIDIA API integration)
- **AI Router Engine** (Core routing logic with failover)

**Critical Finding**: The system has all components implemented but lacks proper NVIDIA API key integration and automatic failover logic. Several providers fail silently without proper error propagation.

---

## 1. Current Architecture Overview

### 1.1 Provider Hierarchy

```
AI Router Engine (core/ai_router/engine.py)
    ├── Local Models (Ollama) — priority 0
    ├── NVIDIA NIM Provider (cores/ai/providers/nvidia_nim_provider.py) — priority 10
    ├── FCC Provider (cores/ai/providers/fcc_provider.py) — priority 20
    ├── OpenRouter Provider (cores/ai/providers/openrouter_provider.py) — priority 30
    └── OpenCode Provider (cores/ai/providers/opencode_provider.py) — priority 10 (for code tasks)

COPILOT Router (cores/copilot/providers/router.py)
    ├── OpenCode Provider — priority 10
    ├── FCC Provider (cores/copilot/providers/fcc_provider.py) — priority 20
    ├── NVIDIA Provider (cores/copilot/providers/nvidia_provider.py) — priority 15
    └── OmniRoute Provider (cores/copilot/providers/omniroute_provider.py) — priority 5
```

### 1.2 Environment Variables Status

| Variable | File | Status | Notes |
|----------|------|--------|-------|
| `NVIDIA_API_KEY` | `.env.example`, `.config/ownex/opportunity.env` | ⚠️ Documented but not loaded | FCC provider doesn't read it |
| `NIM_API_KEY` | `.config/ownex/opportunity.env` | ✅ Defined | NVIDIA provider expects this |
| `ANTHROPIC_API_KEY` | `.env`, `.env.example` | ✅ Configured | Used by FCC for OpenRouter |
| `OPENROUTER_API_KEY` | `.env.example` | ⚠️ Optional | Fallback for FCC |

---

## 2. FCC Provider Audit

### 2.1 File: `cores/ai/providers/fcc_provider.py`

**Current State:**
- Uses `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` for authentication
- Base URL defaults to `https://openrouter.ai/api/v1`
- Priority: 20 (after local models and NVIDIA)
- Models: Hardcoded list of 7 models

**Issues Found:**
1. **No NVIDIA API key support** — Does not read `NVIDIA_API_KEY` or `NIM_API_KEY`
2. **No automatic failover** — Returns error response but doesn't trigger router fallback
3. **Health check is minimal** — Only checks if API key exists, doesn't verify connectivity
4. **No rate limit handling** — Doesn't detect 429 responses
5. **No quota exhaustion detection** — Doesn't handle 402/403 for quota

**Code Issues:**
```python
# Line 33-37: Only reads ANTHROPIC_API_KEY / OPENROUTER_API_KEY
self._base_url = (
    self._config.extra.get("base_url", os.getenv("ANTHROPIC_BASE_URL", "")) or "https://openrouter.ai/api/v1"
)
self._api_key = self._config.extra.get("api_key", os.getenv("ANTHROPIC_API_KEY", os.getenv("OPENROUTER_API_KEY", "")))
```

### 2.2 File: `cores/copilot/providers/fcc_provider.py`

**Current State:**
- Nearly identical to AI router version
- Uses same environment variables
- Same issues as above

---

## 3. OmniRoute Provider Audit

### 3.1 File: `cores/copilot/providers/omniroute_provider.py`

**Current State:**
- Implements multi-provider routing with health scoring
- Provider priorities: local (0), nvidia (15), fcc (20), openrouter (30), opencode (10)
- Health checks with latency measurement
- Fallback logic implemented

**Issues Found:**
1. **NVIDIA provider not registered by default** — Only registers if API key present at init time
2. **No dynamic provider registration** — Can't add providers after initialization
3. **Health check runs once** — No periodic health monitoring
4. **Failover only on exception** — Doesn't handle HTTP error codes (429, 402, 403)
5. **No streaming support** — `chat_stream` not implemented

**Code Issues:**
```python
# Line 89-105: NVIDIA only added if key exists at init
if os.getenv("NIM_API_KEY") or self._config.extra.get("nvidia_api_key"):
    self._providers.append(nvidia_provider)
```

---

## 4. NVIDIA Provider Audit

### 4.1 File: `cores/ai/providers/nvidia_nim_provider.py` (AI Router)

**Current State:**
- Reads `NVIDIA_API_KEY` from environment
- Base URL: `https://integrate.api.nvidia.com/v1`
- Priority: 10
- Supports streaming and tool calling

**Issues Found:**
1. **Wrong environment variable** — Uses `NVIDIA_API_KEY` but config uses `NIM_API_KEY`
2. **No health check implementation** — Inherits base class but doesn't override
3. **No rate limit handling** — Missing 429 detection
4. **Model list hardcoded** — Doesn't fetch from API

### 4.2 File: `cores/copilot/providers/nvidia_provider.py` (COPILOT)

**Current State:**
- Reads `NIM_API_KEY` from environment
- More complete implementation with model fetching
- Priority: 15

**Issues Found:**
1. **Inconsistent with AI Router version** — Different env var names
2. **No automatic model refresh** — Models fetched once at init

---

## 5. AI Router Engine Audit

### 5.1 File: `core/ai_router/engine.py`

**Current State:**
- Provider registry with priority-based selection
- Health checks on initialization
- Fallback on provider failure
- Request routing with caching

**Issues Found:**
1. **Health checks run only at startup** — No periodic re-check
2. **Failover only on exception** — Doesn't handle HTTP error codes
3. **No rate limit awareness** — Doesn't track per-provider limits
4. **Caching may serve stale failures** — Failed responses cached
5. **No circuit breaker** — Keeps trying failed providers

**Critical Code Path:**
```python
# Line 400-450: Provider selection logic
async def _select_provider(self, model: str | None) -> BaseProvider | None:
    # Sorts by priority, picks first healthy
    # But "healthy" only checked at init!
```

---

## 6. Credential Management Audit

### 6.1 File: `cores/credentials/vault.py`

**Current State:**
- Secure credential storage with encryption
- Supports multiple key types
- Environment variable fallback

**Issues Found:**
1. **No NVIDIA-specific credential type** — Uses generic "api_key"
2. **No validation of key format** — Doesn't verify NVIDIA key structure

---

## 7. Testing Status

### 7.1 Test File: `tests/test_ai_router.py`

**Current State:**
- Tests for provider selection, failover, caching
- Mocks HTTP responses
- Good coverage of happy paths

**Missing Tests:**
- Rate limit handling (429)
- Quota exhaustion (402/403)
- Invalid API key (401)
- Network timeout
- Provider recovery after failure
- NVIDIA-specific integration tests

---

## 8. Routing Strategy Implementation Gap

### Current vs Desired

| Feature | Current | Desired | Gap |
|---------|---------|---------|-----|
| Local models first | ✅ Priority 0 | ✅ | None |
| NVIDIA second | ⚠️ Priority 10 but key issues | ✅ Priority 10 | Env var, health check |
| OpenRouter third | ✅ Priority 30 | ✅ Priority 30 | None |
| Auto failover on error | ✅ Exception only | ✅ All failure types | HTTP codes |
| Auto failover on rate limit | ❌ | ✅ | 429 handling |
| Auto failover on quota | ❌ | ✅ | 402/403 handling |
| Health monitoring | ❌ Once at init | ✅ Periodic | Background task |
| Circuit breaker | ❌ | ✅ | New implementation |
| Diagnostic command | ❌ | ✅ `ownex doctor ai` | New implementation |

---

## 9. Recommendations

### Immediate Fixes (Priority 1)
1. **Unify NVIDIA env var** — Use `NVIDIA_API_KEY` everywhere (or add alias for `NIM_API_KEY`)
2. **Add NVIDIA to FCC provider** — Allow FCC to use NVIDIA as backend
3. **Fix health checks** — Implement proper connectivity verification
4. **Add HTTP error code handling** — 429, 401, 402, 403, 5xx trigger failover

### Short-term (Priority 2)
5. **Periodic health monitoring** — Background task re-checking providers every 60s
6. **Circuit breaker pattern** — Stop trying failed providers for cooldown period
7. **Implement `ownex doctor ai` command** — Diagnostic endpoint

### Long-term (Priority 3)
8. **Rate limit tracking** — Per-provider token buckets
9. **Latency-based routing** — Prefer faster healthy providers
10. **Comprehensive stress tests** — Chaos engineering for provider failures

---

## 10. Files to Modify

| File | Changes Needed |
|------|----------------|
| `cores/ai/providers/fcc_provider.py` | Add NVIDIA_API_KEY support, improve health check, add HTTP error handling |
| `cores/copilot/providers/fcc_provider.py` | Same as above |
| `cores/ai/providers/nvidia_nim_provider.py` | Fix env var, add health check, add rate limit handling |
| `cores/copilot/providers/nvidia_provider.py` | Align with AI router version |
| `cores/copilot/providers/omniroute_provider.py` | Dynamic provider registration, periodic health checks |
| `core/ai_router/engine.py` | Periodic health checks, circuit breaker, HTTP error failover |
| `cores/credentials/vault.py` | Add NVIDIA credential type |
| `apps/hermes/engine.py` | Add `doctor ai` command |
| `tests/test_ai_router.py` | Add failure scenario tests |
| `.env.example` | Document NVIDIA_API_KEY |

---

## 11. Validation Checklist

After fixes, verify:
- [ ] `ownex doctor ai` shows all providers with health status
- [ ] FCC works with NVIDIA_API_KEY
- [ ] OmniRoute registers NVIDIA dynamically
- [ ] Failover on 429 (rate limit)
- [ ] Failover on 401 (invalid key)
- [ ] Failover on 402/403 (quota)
- [ ] Failover on 5xx (server error)
- [ ] Failover on timeout
- [ ] Recovery after provider comes back
- [ ] Periodic health checks running
- [ ] Circuit breaker prevents hammering failed providers
- [ ] Tests pass for all failure scenarios

---

*Report generated: 2025-08-01*
*System: Rastro/OWNEX v7.0.0*