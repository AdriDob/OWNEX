"""OAR Provider Adapters — Wrappers for existing providers to conform to AIProviderProtocol."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncGenerator

import httpx

from .interfaces import (
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    Capability,
    HealthStatus,
    ModelCapabilities,
    ProviderHealth,
)

logger = logging.getLogger("oar.adapters")


class OllamaAdapter(AIProviderProtocol):
    """Adapter for Ollama provider."""

    def __init__(self, host: str | None = None, model: str | None = None):
        self._host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL", "qwen3-coder:8b")
        self._available: bool | None = None
        self._start_time = time.monotonic()

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama (Local)"

    @property
    def supported_models(self) -> list[str]:
        return [self._model, "qwen3-coder:8b", "llama3.1:8b", "codellama:7b", "mistral:7b"]

    def get_model_capabilities(self, model_id: str) -> ModelCapabilities | None:
        caps = {
            "qwen3-coder:8b": ModelCapabilities(
                model_id=model_id,
                supports={Capability.CHAT, Capability.CODE, Capability.REASONING, Capability.TOOL_CALLING},
                max_context_tokens=32768,
                max_output_tokens=8192,
                tool_call_format="openai",
            ),
            "llama3.1:8b": ModelCapabilities(
                model_id=model_id,
                supports={Capability.CHAT, Capability.REASONING},
                max_context_tokens=131072,
                max_output_tokens=8192,
            ),
            "codellama:7b": ModelCapabilities(
                model_id=model_id,
                supports={Capability.CHAT, Capability.CODE},
                max_context_tokens=16384,
                max_output_tokens=8192,
            ),
        }
        return caps.get(model_id, ModelCapabilities(model_id=model_id, max_context_tokens=4096))

    async def check_health(self) -> ProviderHealth:
        start = time.monotonic()
        try:
            import urllib.request

            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                healthy = resp.status == 200
            latency = (time.monotonic() - start) * 1000
            return ProviderHealth(
                provider_id=self.provider_id,
                status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                latency_ms=latency,
                uptime_seconds=time.monotonic() - self._start_time,
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.monotonic() - start) * 1000,
                last_error=str(e),
                uptime_seconds=time.monotonic() - self._start_time,
            )

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant: ")
        return "\n".join(parts)

    async def chat(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        prompt = self._format_messages(request.messages)

        try:
            import urllib.request

            payload = json.dumps(
                {
                    "model": request.model or self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": request.max_tokens, "temperature": request.temperature},
                }
            ).encode()
            req = urllib.request.Request(
                f"{self._host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())

            latency = (time.monotonic() - start) * 1000
            content = result.get("response", "").strip()

            return AIResponse(
                content=content,
                provider_id=self.provider_id,
                model_id=request.model or self._model,
                task_type=request.task_type,
                usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4},
                cost_usd=0.0,
                latency_ms=latency,
                finish_reason="stop" if content else "error",
            )
        except Exception as e:
            logger.warning("Ollama chat failed: %s", e)
            return AIResponse(
                content="",
                provider_id=self.provider_id,
                model_id=request.model or self._model,
                task_type=request.task_type,
                cost_usd=0.0,
                latency_ms=(time.monotonic() - start) * 1000,
                finish_reason="error",
                metadata={"error": str(e)},
            )

    async def chat_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        prompt = self._format_messages(request.messages)
        try:
            import urllib.request

            payload = json.dumps(
                {
                    "model": request.model or self._model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"num_predict": request.max_tokens, "temperature": request.temperature},
                }
            ).encode()
            req = urllib.request.Request(
                f"{self._host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    chunk = json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except Exception as e:
            logger.warning("Ollama stream failed: %s", e)

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        try:
            import urllib.request

            embed_model = model or "nomic-embed-text"
            results = []
            for text in texts:
                payload = json.dumps({"model": embed_model, "prompt": text}).encode()
                req = urllib.request.Request(
                    f"{self._host}/api/embeddings",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode())
                    results.append(result.get("embedding", []))
            return results
        except Exception as e:
            logger.warning("Ollama embed failed: %s", e)
            return [[] for _ in texts]

    def estimate_cost(self, request: AIRequest) -> float:
        return 0.0

    def estimate_latency(self, request: AIRequest) -> int:
        return 3000

    async def close(self) -> None:
        """Cleanup resources."""
        pass


class OpenAICompatibleAdapter(AIProviderProtocol):
    """Adapter for OpenAI-compatible providers (OpenRouter, Groq, Together, etc.)."""

    def __init__(
        self,
        provider_id: str,
        name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        env_key: str = "",
        env_base: str = "",
        env_model: str = "",
        pricing: tuple[float, float] = (0.0, 0.0),
        capabilities: set[Capability] | None = None,
        max_context: int = 128000,
    ):
        self._provider_id = provider_id
        self._name = name
        self._api_key = api_key or os.getenv(env_key, "") if env_key else ""
        self._base_url = (base_url or os.getenv(env_base, "")).rstrip("/") if base_url or env_base else ""
        self._model = model or os.getenv(env_model, "") if env_model else ""
        self._pricing = pricing
        self._capabilities = capabilities or {Capability.CHAT}
        self._max_context = max_context
        self._available: bool | None = None
        self._start_time = time.monotonic()

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_models(self) -> list[str]:
        return [self._model] if self._model else []

    def get_model_capabilities(self, model_id: str) -> ModelCapabilities | None:
        return ModelCapabilities(
            model_id=model_id,
            supports=self._capabilities,
            max_context_tokens=self._max_context,
            max_output_tokens=8192,
            tool_call_format="openai",
            supports_parallel_tools=True,
        )

    async def check_health(self) -> ProviderHealth:
        start = time.monotonic()
        if not self._api_key or not self._base_url:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=HealthStatus.AUTH_FAILED,
                last_error="Missing API key or base URL",
                uptime_seconds=time.monotonic() - self._start_time,
            )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            latency = (time.monotonic() - start) * 1000
            return ProviderHealth(
                provider_id=self.provider_id,
                status=HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY,
                latency_ms=latency,
                uptime_seconds=time.monotonic() - self._start_time,
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.monotonic() - start) * 1000,
                last_error=str(e),
                uptime_seconds=time.monotonic() - self._start_time,
            )

    async def chat(self, request: AIRequest) -> AIResponse:
        start = time.monotonic()
        if not self._api_key or not self._base_url:
            return AIResponse(
                content="",
                provider_id=self.provider_id,
                model_id=request.model or self._model,
                task_type=request.task_type,
                cost_usd=0.0,
                latency_ms=(time.monotonic() - start) * 1000,
                finish_reason="error",
                metadata={"error": "Not configured"},
            )

        try:
            payload = {
                "model": request.model or self._model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }
            if request.tools:
                payload["tools"] = request.tools
                payload["tool_choice"] = request.tool_choice or "auto"
            if request.response_format:
                payload["response_format"] = request.response_format

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

            latency = (time.monotonic() - start) * 1000

            if resp.status_code != 200:
                return AIResponse(
                    content="",
                    provider_id=self.provider_id,
                    model_id=request.model or self._model,
                    task_type=request.task_type,
                    cost_usd=0.0,
                    latency_ms=latency,
                    finish_reason="error",
                    metadata={"error": f"HTTP {resp.status_code}: {resp.text}"},
                )

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = (self._pricing[0] * input_tokens + self._pricing[1] * output_tokens) / 1000

            return AIResponse(
                content=content.strip(),
                provider_id=self.provider_id,
                model_id=request.model or self._model,
                task_type=request.task_type,
                usage=usage,
                cost_usd=cost,
                latency_ms=latency,
                finish_reason=choice.get("finish_reason"),
                tool_calls=choice.get("message", {}).get("tool_calls"),
            )
        except Exception as e:
            logger.warning("%s chat failed: %s", self._name, e)
            return AIResponse(
                content="",
                provider_id=self.provider_id,
                model_id=request.model or self._model,
                task_type=request.task_type,
                cost_usd=0.0,
                latency_ms=(time.monotonic() - start) * 1000,
                finish_reason="error",
                metadata={"error": str(e)},
            )

    async def chat_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        if not self._api_key or not self._base_url:
            return

        payload = {
            "model": request.model or self._model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = request.tool_choice or "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            async with (
                httpx.AsyncClient(timeout=120) as client,
                client.stream("POST", f"{self._base_url}/chat/completions", json=payload, headers=headers) as resp,
            ):
                async for line in resp.aiter_lines():
                    if not line.strip() or line.startswith(":"):
                        continue
                    if line.strip() == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                        except Exception:
                            continue
        except Exception as e:
            logger.warning("%s stream failed: %s", self._name, e)

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        # Most OpenAI-compatible providers support embeddings at /embeddings
        try:
            embed_model = model or "text-embedding-3-small"
            payload = {"model": embed_model, "input": texts}
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"}

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self._base_url}/embeddings", json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return [d.get("embedding", []) for d in data.get("data", [])]
        except Exception as e:
            logger.warning("%s embed failed: %s", self._name, e)
        return [[] for _ in texts]

    def estimate_cost(self, request: AIRequest) -> float:
        tokens = sum(len(m.get("content", "")) for m in request.messages) // 4
        return (self._pricing[0] * tokens + self._pricing[1] * request.max_tokens) / 1000

    def estimate_latency(self, request: AIRequest) -> int:
        return 1000

    async def close(self) -> None:
        """Cleanup resources."""
        pass


# Factory functions for common providers
def create_openrouter_adapter(api_key: str | None = None, model: str = "openai/gpt-4o-mini") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="openrouter",
        name="OpenRouter",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model,
        env_key="OPENROUTER_API_KEY",
        pricing=(0.00015, 0.0006),  # gpt-4o-mini pricing
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.VISION,
            Capability.JSON_MODE,
            Capability.LONG_CONTEXT,
        },
        max_context=128000,
    )


def create_groq_adapter(api_key: str | None = None, model: str = "llama-3.1-70b-versatile") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="groq",
        name="Groq",
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        model=model,
        env_key="GROQ_API_KEY",
        pricing=(0.0, 0.0),  # Free tier
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.JSON_MODE,
        },
        max_context=32768,
    )


def create_together_adapter(
    api_key: str | None = None, model: str = "meta-llama/Llama-3.1-70B-Instruct-Turbo"
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="together",
        name="Together AI",
        api_key=api_key,
        base_url="https://api.together.xyz/v1",
        model=model,
        env_key="TOGETHER_API_KEY",
        pricing=(0.00088, 0.00088),
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.JSON_MODE,
            Capability.LONG_CONTEXT,
        },
        max_context=128000,
    )


def create_deepinfra_adapter(
    api_key: str | None = None, model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="deepinfra",
        name="DeepInfra",
        api_key=api_key,
        base_url="https://api.deepinfra.com/v1/openai",
        model=model,
        env_key="DEEPINFRA_API_KEY",
        pricing=(0.00075, 0.00075),
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.JSON_MODE,
            Capability.LONG_CONTEXT,
        },
        max_context=128000,
    )


def create_cerebras_adapter(api_key: str | None = None, model: str = "llama3.1-70b") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="cerebras",
        name="Cerebras",
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
        model=model,
        env_key="CEREBRAS_API_KEY",
        pricing=(0.0, 0.0),  # Free
        capabilities={Capability.CHAT, Capability.CODE, Capability.REASONING, Capability.JSON_MODE},
        max_context=8192,
    )


def create_nvidia_adapter(
    api_key: str | None = None, model: str = "meta/llama-3.1-70b-instruct"
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="nvidia_nim",
        name="NVIDIA NIM",
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        model=model,
        env_key="NVIDIA_API_KEY",
        pricing=(0.0009, 0.0009),
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.JSON_MODE,
            Capability.LONG_CONTEXT,
        },
        max_context=128000,
    )


def create_fcc_adapter(api_key: str | None = None, model: str = "claude-sonnet-4-5") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="fcc",
        name="FCC Proxy",
        api_key=api_key,
        base_url=os.getenv("FCC_API_BASE", "http://localhost:8082/v1"),
        model=model,
        env_key="ANTHROPIC_API_KEY",
        pricing=(0.003, 0.015),
        capabilities={
            Capability.CHAT,
            Capability.CODE,
            Capability.REASONING,
            Capability.TOOL_CALLING,
            Capability.VISION,
            Capability.JSON_MODE,
            Capability.LONG_CONTEXT,
        },
        max_context=200000,
    )


def create_opencode_adapter(model: str = "deepseek-v4-flash-free") -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="opencode",
        name="OpenCode Free",
        api_key="",  # No key needed for free models
        base_url="https://api.opencode.ai/v1",
        model=model,
        pricing=(0.0, 0.0),
        capabilities={Capability.CHAT, Capability.CODE, Capability.REASONING},
        max_context=128000,
    )


def create_lmstudio_adapter(
    host: str = "http://localhost:1234/v1", model: str = "local-model"
) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="lmstudio",
        name="LM Studio",
        api_key="lm-studio",  # LM Studio doesn't require real key
        base_url=host,
        model=model,
        pricing=(0.0, 0.0),
        capabilities={Capability.CHAT, Capability.CODE, Capability.REASONING, Capability.TOOL_CALLING},
        max_context=32768,
    )
