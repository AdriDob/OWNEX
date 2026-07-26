# Hermes One + OpenCode Zen Free — Setup Guide

## Provider: OpenCode Zen Free

- **URL**: `https://opencode.ai/zen/v1`
- **Model**: `deepseek-v4-flash-free`
- **Cost**: Free (no API key required)
- **Context**: 128K
- **Reasoning**: Enabled

## Auth Patch

OpenAI SDK always sends `Authorization: Bearer` header even with empty key, which OpenCode Zen rejects.

Patch applied in two files:

### `run_agent.py:4629-4633`
```python
elif base_url_host_matches(base_url, "opencode.ai"):
    if model and model.endswith("-free"):
        client_kwargs["default_headers"] = {"Authorization": ""}
```

### `agent/agent_init.py:938-942`
```python
elif base_url_host_matches(base_url, "opencode.ai"):
    if model and model.endswith("-free"):
        initial_kwargs["default_headers"] = {"Authorization": ""}
```

## Config (`~/.hermes/config.yaml`)

```yaml
provider: opencode-zen
model: deepseek-v4-flash-free
```

## Verification

```bash
hermes chat -q "Respond with exactly three words: Hermes One Ready"
# Expected: Hermes One Ready
```

## Important

- No API key in `.env` for this provider
- Patch targets only models ending in `-free` — does not affect other providers
- Fallback chain: OpenCode Zen Free → Gemini → Ollama → Mock
