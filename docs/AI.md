# OWNEX AI System (OAR)

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

OAR (OWNEX AI Runtime) is the unified AI orchestration layer that manages provider routing, cost tracking, failover, caching, and learning across all AI operations in OWNEX.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      OAR RUNTIME                             │
├─────────────────────────────────────────────────────────────┤
│  SmartRouter ──► ProviderRegistry ──► Adapters (9)         │
│       │              │                    │                  │
│       ▼              ▼                    ▼                  │
│  CostTracker    HealthMonitor         FailoverEngine       │
│       │              │                    │                  │
│       ▼              ▼                    ▼                  │
│  SemanticCache  LearningEngine        CircuitBreakers      │
└─────────────────────────────────────────────────────────────┘
```

## Provider Chain (Failover Order)

| Priority | Provider | Base URL | Transport | Models | Cost |
|----------|----------|----------|-----------|--------|------|
| 1 | **OmniRoute** | `http://localhost:20128/v1` | OpenAI | `auto/*`, `deepseek-v4`, `qwen3-6-plus` | Free (API key) |
| 2 | **FCC Proxy** | `http://localhost:8082` | Anthropic | `claude-sonnet-4-20250514`, `claude-haiku-4-20250514` | Free (orion-dev-local) |
| 3 | **Ollama** | `http://localhost:11434/v1` | OpenAI | `qwen2.5:3b-instruct` | Local (free) |
| 4 | **OpenCode Built-in** | Internal | Various | DeepSeek, Nemotron, Mimo | Free |

## Core Components

### 1. Provider Registry (`cores/ai/runtime/registry.py`)

```python
class ProviderRegistry:
    def register(self, provider_id: str, adapter: AIProviderProtocol):
        # Stores provider with capabilities
    
    def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        # max_context_tokens, capabilities (CODE, CHAT, REASONING)
    
    def list_models(self, provider_id: str) -> list[str]:
        # Available models per provider
```

### 2. Smart Router (`cores/ai/runtime/router.py`)

```python
class SmartRouter:
    def route(self, request: AIRequest, context: RoutingContext) -> RoutingDecision:
        """
        Routing logic:
        1. TaskType.CODE → prefer local (Ollama qwen2.5-coder)
        2. TaskType.CHAT → prefer free (OmniRoute auto/best)
        3. TaskType.REASONING → prefer high-reasoning (FCC claude-sonnet-4)
        4. Budget check → reject if over daily_budget_usd
        5. Health check → skip unhealthy providers
        6. Learning → prefer historically successful routes
        """
```

**Task Types**:
- `CODE` — Code generation, analysis, review
- `CHAT` — General conversation
- `REASONING` — Complex analysis, planning
- `EMBEDDING` — Vector embeddings

### 3. Cost Tracker (`cores/ai/runtime/cost.py`)

```python
class CostTracker:
    def __init__(self, daily_budget_usd: Decimal = Decimal("0")):
        # Default $0/day — explicit opt-in for paid
    
    def record_usage(self, provider: str, model: str, 
                     input_tokens: int, output_tokens: int, cost_usd: Decimal):
        # Persists to SQLite
    
    def check_budget(self, estimated_cost: Decimal) -> bool:
        # Returns False if would exceed daily budget
    
    def get_daily_spend(self) -> Decimal:
        # Current day's total
```

### 4. Failover Engine (`cores/ai/runtime/failover.py`)

```python
class FailoverEngine:
    def __init__(self, circuit_breaker_threshold: int = 3):
        # Opens circuit after N consecutive failures
    
    def record_success(self, provider: str):
        # Resets failure count
    
    def record_failure(self, provider: str):
        # Increments, opens circuit at threshold
    
    def is_available(self, provider: str) -> bool:
        # False if circuit open
```

### 5. Health Monitor (`cores/ai/runtime/health.py`)

```python
class HealthMonitor:
    async def check_provider(self, provider_id: str) -> ProviderHealth:
        # Calls /models or /health endpoint
        # Returns: status, latency_ms, model_count, error_rate
    
    async def check_all(self) -> dict[str, ProviderHealth]:
        # Parallel health checks
```

### 6. Learning Engine (`cores/ai/runtime/learning.py`)

```python
class LearningEngine:
    def record_outcome(self, task_type: TaskType, provider: str, 
                       model: str, success: bool, latency_ms: int):
        # Updates preference matrix
    
    def get_preference(self, task_type: TaskType) -> list[ProviderPreference]:
        # Returns ranked providers for task type
```

### 7. Semantic Cache (`cores/ai/runtime/cache.py`)

```python
class SemanticCache:
    def get(self, prompt_hash: str) -> AIResponse | None:
        # Exact match on normalized prompt
    
    def set(self, prompt_hash: str, response: AIResponse, ttl: int = 3600):
        # Stores with TTL
```

## Configuration

### OAR Config (`cores/ai/runtime/interfaces.py`)

```python
@dataclass
class OARConfig:
    daily_budget_usd: Decimal = Decimal("0")  # Free by default
    prefer_local: bool = True
    prefer_free: bool = True
    max_latency_ms: int = 30000
    enable_cache: bool = True
    enable_learning: bool = True
    circuit_breaker_threshold: int = 3
    health_check_interval_s: int = 60
```

### Provider Adapters (`cores/ai/runtime/adapters.py`)

```python
# 9 Factory functions creating provider adapters:
create_openrouter_adapter()  # OpenRouter (paid tiers)
create_groq_adapter()  # Groq (free tier)
create_together_adapter()  # Together AI
create_deepinfra_adapter()  # DeepInfra
create_cerebras_adapter()  # Cerebras
create_nvidia_adapter()  # NVIDIA NIM
create_fcc_adapter()  # FCC Proxy (Anthropic via OpenRouter)
create_opencode_adapter()  # OpenCode built-in
create_lmstudio_adapter()  # LM Studio local
```

## Integration Points

### Hermes CLI (`~/.hermes/config.yaml`)

```yaml
model:
  provider: omniroute
  base_url: http://localhost:20128/v1
  name: auto/best-free
  api_key: sk-f8bed9b225539e00-8d7be9-af8dabba
fallback_providers:
  - base_url: http://localhost:8082
    model: claude-sonnet-4-20250514
    provider: fcc
  - base_url: http://localhost:11434
    model: qwen2.5:3b-instruct
    provider: ollama-launch
```

### OpenCode (`~/.config/opencode/config.json`)

```json
{
  "provider": "fcc",
  "model": "nvidia_nim/deepseek-ai/deepseek-coder-6.7b-instruct",
  "providers": {
    "fcc": {"type": "openai", "base_url": "http://localhost:8082/v1"},
    "omniroute": {"type": "openai", "base_url": "http://localhost:20128/v1", "auth": "sk-..."},
    "ollama": {"type": "ollama", "base_url": "http://localhost:11434/v1"}
  }
}
```

### MERLIN (`cores/merlin/system.py`)

```python
class MerlinSystem:
    async def process_message(self, message: str) -> MerlinResponse:
        # Uses OAR for AI calls
        # Intent analysis → tool selection → response generation
        # Memory persistence via UnifiedMemoryStore
```

## Agent System

### Departmental Agents (`cores/agents/specialists/`)

| Agent | Role | Capabilities |
|-------|------|--------------|
| **Orchestrator** | CEO | Coordination, approvals, strategy |
| **Architecture** | CTO | System design, tech decisions |
| **Coding** | Developer | Implementation, PRs |
| **Debug** | SRE | Root cause analysis, logs |
| **QA** | Test | Test generation, validation |
| **Security** | SecEng | Audits, hardening |
| **Documentation** | TechWriter | Docs, ADRs |
| **Research** | Researcher | Tech exploration |
| **Product** | PM | UX, features, roadmap |
| **Revenue** | BizDev | Market analysis, pricing |
| **Automation** | DevOps | Workflows, CI/CD |
| **Infrastructure** | Platform | Servers, deployments |
| **Evolution** | Architect | Self-improvement, audits |

### MVP Core Team (5 agents)
1. Orchestrator — Coordination
2. Coding — Implementation
3. Documentation — Memory
4. Revenue — Income optimization
5. QA — Quality gate

## AI Chat (MERLIN)

### Desktop (`MerlinInterface.vue`)
- Full conversational interface
- Sidebar: Notes, Memory, Quick Actions
- Settings: Theme, Detail Level, Tone
- Streaming responses

### Mobile (`MobileCompanionJarvis.vue` → `VoiceAssistantRecorder`)
- Voice input (STT via Capacitor Speech Recognition)
- TTS via backend Piper → Web Speech fallback
- Compact chat bubbles
- Quick actions

### Capabilities
| Capability | Description |
|------------|-------------|
| `target_analysis` | Analyze bug bounty targets |
| `report_generation` | Draft vulnerability reports |
| `workflow_optimization` | Suggest automation improvements |
| `data_analysis` | Analyze revenue/capital data |
| `strategic_planning` | Roadmap, prioritization |
| `technical_assistance` | Code review, debugging |
| `general` | Open conversation |

## Memory & Context

### UnifiedMemoryStore (`cores/memory/store.py`)

```python
# 10 Namespaces:
# global, cateye, atlas, odyssey, hermes, copilot, merlin, user, projects, decision_history

store.store(
    namespace="merlin",
    key="conversation_123",
    content="User asked about IDOR validation",
    tags=["conversation", "security"],
    priority=2.0,
)

context = mm.get_strategic_context()  # For MERLIN system prompt
```

### MerlinMemory (`cores/merlin/memory.py`)

```python
mm.store_brief("Validated 3 IDORs on acme.com, $2400 expected")
mm.store_decision("prioritize_acme", {"reason": "high_ev", "targets": [...]})
mm.set_preferences({"language": "es", "verbosity": "terse"})
```

## Voice Interface

### Backend (`cores/voice/voice_engine.py`)

```python
class TTSManager:
    def synthesize(self, text: str) -> bytes:
        # Piper CLI → WAV
        # Model: es_MX-ald-medium (es-419)
        # Voice: calm_operator (speed 0.95, pitch 0, vol 0.85)

class VoicePersonality:
    # Framing: "Resultado, {verdict}."
    # No exclamations, calm tone
```

### Frontend
- **Desktop**: `VoiceAssistantListener.vue` — Polls `/voice/assistant/replies`, speaks via Web Speech API
- **Mobile**: `VoiceAssistantRecorder.vue` — STT via `@capacitor-community/speech-recognition`, sends to `/voice/assistant`

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/voice/assistant` | Submit voice/text query |
| `GET /api/voice/assistant/replies` | Poll for AI responses (desktop) |
| `GET /api/voice/status` | Provider status |
| `GET /api/voice/config` | Voice profile |
| `PUT /api/voice/config` | Update voice profile |
| `POST /api/merlin/chat` | MERLIN conversation |
| `GET /api/merlin/memory` | Conversation memory |
| `POST /api/merlin/memory` | Store memory |
| `GET /api/oar/status` | OAR health, providers |
| `POST /api/oar/chat` | Direct OAR query |

## Testing

```bash
pytest tests/test_oar.py                    # 12 passed
pytest tests/test_voice_engine.py           # 21 passed
pytest tests/test_merlin_system.py          # (if exists)
pytest tests/test_voice_assistant.py        # (if exists)
```

---

*Document generated from codebase. Last verified: 2026-08-27*