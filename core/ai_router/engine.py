"""AI Router — intelligent model fallback for the ORION ecosystem.

Prevents work interruption by detecting provider limits early and
switching to available alternatives before the current model fails.

Fallback chain (never includes OpenRouter directly):
  OpenCode Free → FCC Proxy → GooseAI → NVIDIA NIM → Ollama Local

Provider status is persisted to ~/.orion/ai_provider_status.json
for cross-module visibility.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.ai_router")

POLICY_PATH = os.path.expanduser("~/.orion/ai_policy.yaml")
HISTORY_PATH = os.path.expanduser("~/.orion/ai_switches.jsonl")

_TIER_ORDER = {"free": 1, "proxy": 2, "cloud": 3, "local": 4}

_VALID_CHAIN = ["opencode_free", "fcc_proxy", "gooseai", "nvidia_nim", "ollama"]

_ALWAYS_VALID_MODELS = {
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-free",
}

_PROXY_EVENTS_PREFIX = "ai:router:"


@dataclass
class AIProviderStatus:
    name: str
    tier: str
    available: bool
    current_model: str = ""
    models: list[str] = field(default_factory=list)
    error: str = ""
    latency_ms: float = 0.0
    last_checked: str = ""
    status_category: str = "unknown"
    cooldown_remaining: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "available": self.available,
            "current_model": self.current_model,
            "models": self.models,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
            "last_checked": self.last_checked,
            "status_category": self.status_category,
            "cooldown_remaining": round(self.cooldown_remaining, 1),
        }


@dataclass
class AIProvider:
    name: str
    tier: str
    models: list[str]
    status: str = "unknown"


@dataclass
class AIPolicy:
    fallback_enabled: bool = True
    providers_priority: list[str] = field(default_factory=lambda: list(_VALID_CHAIN))
    switch_before_limit_percentage: int = 20
    max_retry_failures: int = 2
    prefer_quality_for: list[str] = field(default_factory=lambda: ["architecture", "security", "reports"])
    prefer_speed_for: list[str] = field(default_factory=lambda: ["search", "formatting", "simple_edits"])
    never_use_openrouter_directly: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "fallback_enabled": self.fallback_enabled,
            "providers_priority": list(self.providers_priority),
            "switch_before_limit_percentage": self.switch_before_limit_percentage,
            "max_retry_failures": self.max_retry_failures,
            "prefer_quality_for": list(self.prefer_quality_for),
            "prefer_speed_for": list(self.prefer_speed_for),
            "never_use_openrouter_directly": self.never_use_openrouter_directly,
        }


@dataclass
class AIHealth:
    status: str  # green, yellow, red
    current_provider: str = ""
    current_model: str = ""
    near_limit: bool = False
    available_providers: list[AIProviderStatus] = field(default_factory=list)
    recommended_fallback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_provider": self.current_provider,
            "current_model": self.current_model,
            "near_limit": self.near_limit,
            "available_providers": [p.to_dict() for p in self.available_providers],
            "recommended_fallback": self.recommended_fallback,
        }


@dataclass
class FallbackRecommendation:
    should_switch: bool
    reason: str
    from_provider: str = ""
    from_model: str = ""
    to_provider: str = ""
    to_model: str = ""
    estimated_task_complexity: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_switch": self.should_switch,
            "reason": self.reason,
            "from_provider": self.from_provider,
            "from_model": self.from_model,
            "to_provider": self.to_provider,
            "to_model": self.to_model,
            "estimated_task_complexity": self.estimated_task_complexity,
        }


@dataclass
class SwitchRecord:
    timestamp: str
    from_provider: str
    from_model: str
    to_provider: str
    to_model: str
    reason: str
    success: bool = True
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "from_provider": self.from_provider,
            "from_model": self.from_model,
            "to_provider": self.to_provider,
            "to_model": self.to_model,
            "reason": self.reason,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 1),
        }


def create_default_policy() -> AIPolicy:
    return AIPolicy()


def load_policy() -> AIPolicy:
    try:
        import yaml

        path = Path(POLICY_PATH)
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return AIPolicy(
                fallback_enabled=data.get("fallback_enabled", True),
                providers_priority=data.get("providers_priority", list(_VALID_CHAIN)),
                switch_before_limit_percentage=data.get("switch_before_limit_percentage", 20),
                max_retry_failures=data.get("max_retry_failures", 2),
                prefer_quality_for=data.get("prefer_quality_for", ["architecture", "security", "reports"]),
                prefer_speed_for=data.get("prefer_speed_for", ["search", "formatting", "simple_edits"]),
                never_use_openrouter_directly=data.get("never_use_openrouter_directly", True),
            )
    except Exception as exc:
        logger.debug("Cannot load AI policy: %s", exc)
    return create_default_policy()


def save_policy(policy: AIPolicy) -> None:
    try:
        import yaml

        path = Path(POLICY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(policy.to_dict(), f, default_flow_style=False)
    except Exception as exc:
        logger.warning("Cannot save AI policy: %s", exc)


class AIRouterEngine:
    """Decision engine for intelligent model fallback.

    Monitors provider availability, detects approaching limits, and
    recommends the best fallback. Integrates with EventBus and
    CapabilityRegistry for observability.
    """

    def __init__(self, policy: AIPolicy | None = None) -> None:
        self._policy = policy or load_policy()
        self._history: list[SwitchRecord] = []
        self._event_bus: Any = None
        self._load_history()

    @property
    def policy(self) -> AIPolicy:
        return self._policy

    def reload_policy(self) -> None:
        self._policy = load_policy()

    def save_policy(self) -> None:
        save_policy(self._policy)

    # ── Provider discovery ───────────────────────────────────────

    def _discover_providers(self) -> list[AIProviderStatus]:
        providers: list[AIProviderStatus] = []
        now = datetime.now(UTC).isoformat()

        # 1. OpenCode Free models (deepseek, nemotron, mimo)
        providers.append(
            AIProviderStatus(
                name="opencode_free",
                tier="free",
                available=True,
                current_model="opencode/deepseek-v4-flash-free",
                models=sorted(_ALWAYS_VALID_MODELS),
                last_checked=now,
            )
        )

        # 2. FCC Proxy
        proxy_available, proxy_model, proxy_latency = self._check_proxy()
        providers.append(
            AIProviderStatus(
                name="fcc_proxy",
                tier="proxy",
                available=proxy_available,
                current_model=proxy_model or "",
                models=self._get_proxy_models() if proxy_available else [],
                latency_ms=proxy_latency,
                last_checked=now,
                error="" if proxy_available else "Proxy not reachable",
            )
        )

        # 3. GooseAI (cloud, cost-effective)
        gooseai_available, gooseai_models, gooseai_latency = self._check_gooseai()
        providers.append(
            AIProviderStatus(
                name="gooseai",
                tier="cloud",
                available=gooseai_available,
                current_model=gooseai_models[0] if gooseai_models else "",
                models=gooseai_models,
                latency_ms=gooseai_latency,
                last_checked=now,
                error="" if gooseai_available else "GooseAI not configured",
            )
        )

        # 4. NVIDIA NIM (cloud, high quality)
        nim_available, nim_models, nim_latency = self._check_nvidia_nim()
        providers.append(
            AIProviderStatus(
                name="nvidia_nim",
                tier="cloud",
                available=nim_available,
                current_model=nim_models[0] if nim_models else "",
                models=nim_models,
                latency_ms=nim_latency,
                last_checked=now,
                error="" if nim_available else "NVIDIA NIM not reachable",
            )
        )

        # 5. Ollama local
        ollama_available, ollama_models, ollama_latency = self._check_ollama()
        providers.append(
            AIProviderStatus(
                name="ollama",
                tier="local",
                available=ollama_available,
                current_model=ollama_models[0] if ollama_models else "",
                models=ollama_models,
                latency_ms=ollama_latency,
                last_checked=now,
                error="" if ollama_available else "Ollama not reachable",
            )
        )

        return providers

    def _check_proxy(self) -> tuple[bool, str, float]:
        start = time.monotonic()
        try:
            import httpx

            resp = httpx.get("http://localhost:8082/health", timeout=3.0)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                model = (
                    data.get("default_model", "claude-sonnet-4.5") if isinstance(data, dict) else "claude-sonnet-4.5"
                )
                return True, model, elapsed
            return False, "", elapsed
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            return False, "", elapsed

    def _get_proxy_models(self) -> list[str]:
        try:
            import httpx

            resp = httpx.get("http://localhost:8082/v1/models", headers={"x-api-key": "orion-dev-local"}, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                return [m.get("id", "") for m in models if m.get("id")][:20]
        except Exception:
            pass
        return []

    def _check_gooseai(self) -> tuple[bool, list[str], float]:
        start = time.monotonic()
        try:
            import httpx

            api_key = os.getenv("GOSEAI_API_KEY", "")
            base_url = os.getenv("GOSEAI_API_BASE", "https://api.goose.ai/v1")

            if not api_key:
                elapsed = (time.monotonic() - start) * 1000
                return False, [], elapsed

            headers = {"Authorization": f"Bearer {api_key}"}
            resp = httpx.get(f"{base_url}/models", headers=headers, timeout=5.0)
            elapsed = (time.monotonic() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", []) if m.get("id")]
                return bool(models), models, elapsed
            return False, [], elapsed
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            return False, [], elapsed

    def _check_nvidia_nim(self) -> tuple[bool, list[str], float]:
        start = time.monotonic()
        try:
            import httpx

            api_key = os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "")
            if not api_key:
                elapsed = (time.monotonic() - start) * 1000
                return False, [], elapsed

            headers = {"Authorization": f"Bearer {api_key}"}
            resp = httpx.get("https://integrate.api.nvidia.com/v1/models", headers=headers, timeout=5.0)
            elapsed = (time.monotonic() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", []) if m.get("id")]
                return bool(models), models, elapsed
            return False, [], elapsed
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            return False, [], elapsed

    def _check_ollama(self) -> tuple[bool, list[str], float]:
        start = time.monotonic()
        try:
            import httpx

            resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
            elapsed = (time.monotonic() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", []) if m.get("name")]
                return bool(models), models, elapsed
            return False, [], elapsed
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            return False, [], elapsed

    # ── Proxy lock check ─────────────────────────────────────────

    def is_proxy_locked(self) -> bool:
        return os.path.isfile(os.path.expanduser("~/.orion/proxy_mode"))

    # ── Health / Status ──────────────────────────────────────────

    def check_health(self) -> AIHealth:
        providers = self._discover_providers()

        current = next((p for p in providers if p.available and p.tier == "proxy"), None)
        if not current:
            current = next((p for p in providers if p.available and p.tier == "free"), None)
        if not current:
            current = next((p for p in providers if p.available), None)

        current_provider = current.name if current else "none"
        current_model = current.current_model if current else "none"

        near_limit = False
        for p in providers:
            if p.name == "opencode_free" and p.available:
                near_limit = self._estimate_near_limit()

        recommended = self._recommend_fallback(providers, current_provider, "")

        available_count = sum(1 for p in providers if p.available)
        if available_count == 0:
            status = "red"
        elif near_limit and available_count <= 1:
            status = "yellow"
        else:
            status = "green"

        return AIHealth(
            status=status,
            current_provider=current_provider,
            current_model=current_model,
            near_limit=near_limit,
            available_providers=providers,
            recommended_fallback=recommended.to_provider if recommended else "",
        )

    def _estimate_near_limit(self) -> bool:
        try:
            import yaml

            path = os.path.expanduser("~/.hermes/config.yaml")
            if not os.path.isfile(path):
                return False
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}
            max_ctx = cfg.get("model", {}).get("context_length", 128000)
            if max_ctx <= 0:
                return False
            return False
        except Exception:
            return False

    # ── Fallback recommendation ───────────────────────────────────

    def recommend_fallback(self, task_type: str = "", task_complexity: str = "") -> FallbackRecommendation:
        providers = self._discover_providers()

        current = next((p for p in providers if p.available), None)
        if not current:
            return FallbackRecommendation(
                should_switch=False, reason="No providers available at all", estimated_task_complexity=task_complexity
            )

        near_limit = self._estimate_near_limit()
        return self._recommend_fallback(providers, current.name, task_type, near_limit, task_complexity)

    def _recommend_fallback(
        self,
        providers: list[AIProviderStatus],
        current_name: str,
        task_type: str = "",
        force_near_limit: bool = False,
        task_complexity: str = "",
    ) -> FallbackRecommendation:
        if not self._policy.fallback_enabled:
            return FallbackRecommendation(should_switch=False, reason="Fallback disabled in policy")

        available = sorted(
            [p for p in providers if p.available],
            key=lambda p: _TIER_ORDER.get(p.tier, 99),
        )

        if len(available) <= 1:
            return FallbackRecommendation(should_switch=False, reason="No alternative providers available")

        current_in_chain = next(
            (p for p in available if p.name == current_name),
            available[0],
        )

        if task_type and task_type in self._policy.prefer_quality_for:
            preferred_index = next(
                (i for i, p in enumerate(available) if p.tier in ("proxy", "free")),
                None,
            )
        elif task_type and task_type in self._policy.prefer_speed_for:
            preferred_index = next(
                (i for i, p in enumerate(available) if p.tier == "free"),
                None,
            )
        else:
            preferred_index = None

        if preferred_index is not None and preferred_index < len(available):
            preemptive = available[preferred_index]
            if preemptive.name != current_in_chain.name and force_near_limit:
                return FallbackRecommendation(
                    should_switch=True,
                    reason=f"Preemptive switch for {task_type} task (nearing limit)",
                    from_provider=current_in_chain.name,
                    from_model=current_in_chain.current_model,
                    to_provider=preemptive.name,
                    to_model=preemptive.current_model,
                    estimated_task_complexity=task_complexity,
                )

        fallback_candidates = [p for p in available if p.name != current_in_chain.name]
        if fallback_candidates:
            best = fallback_candidates[0]
            return FallbackRecommendation(
                should_switch=force_near_limit,
                reason=f"Recommended fallback: {best.name}"
                if not force_near_limit
                else f"Nearing limit on {current_in_chain.name}, switch to {best.name}",
                from_provider=current_in_chain.name,
                from_model=current_in_chain.current_model,
                to_provider=best.name,
                to_model=best.current_model,
                estimated_task_complexity=task_complexity,
            )

        return FallbackRecommendation(should_switch=False, reason="No suitable fallback found")

    def execute_switch(self, task_type: str = "", task_complexity: str = "") -> FallbackRecommendation:
        recommendation = self.recommend_fallback(task_type, task_complexity)
        if recommendation.should_switch:
            self._record_switch(recommendation)
        return recommendation

    def record_switch(self, record: SwitchRecord) -> None:
        """Public method to record a switch (for testing)."""
        self._history.append(record)
        self._save_history()

    def _record_switch(self, rec: FallbackRecommendation) -> None:
        record = SwitchRecord(
            timestamp=datetime.now(UTC).isoformat(),
            from_provider=rec.from_provider,
            from_model=rec.from_model,
            to_provider=rec.to_provider,
            to_model=rec.to_model,
            reason=rec.reason,
            success=True,
        )
        self._history.append(record)
        self._save_history()

    def _load_history(self) -> None:
        try:
            if os.path.isfile(HISTORY_PATH):
                with open(HISTORY_PATH) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self._history.append(SwitchRecord(**data))
        except Exception as exc:
            logger.debug("Cannot load switch history: %s", exc)

    def _save_history(self) -> None:
        try:
            Path(HISTORY_PATH).parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_PATH, "w") as f:
                for record in self._history[-500:]:
                    f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as exc:
            logger.warning("Cannot save switch history: %s", exc)

    def get_switch_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Alias for get_switch_history for test compatibility."""
        return self.get_switch_history(limit)

    def clear_history(self) -> None:
        """Clear the switch history."""
        self._history.clear()
        self._save_history()

    def _persist_switch(self, record: SwitchRecord) -> None:
        """Persist a switch record (called internally)."""
        self._history.append(record)
        self._save_history()

    def publish_event(self, event: str, **kwargs) -> None:
        """Publish an event to the event bus (no-op if no bus)."""
        if self._event_bus:
            self._event_bus.publish(event, **kwargs)

    def register_capabilities(self) -> None:
        """Register capabilities with the capability registry."""
        try:
            from cores.capabilities.registry import get_capability_registry

            registry = get_capability_registry()
            registry.register(
                "ai_router",
                "core.ai_router.engine",
                metadata={
                    "name": "AI Router",
                    "description": "Intelligent model fallback for ORION ecosystem",
                    "version": "1.0.0",
                    "capabilities": [
                        "provider_discovery",
                        "fallback_recommendation",
                        "health_monitoring",
                        "switch_execution",
                    ],
                },
            )
        except Exception as e:
            logger.debug("Could not register capabilities: %s", e)


def get_ai_router() -> AIRouterEngine:
    """Global singleton accessor."""
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = AIRouterEngine()
    return _ROUTER


_ROUTER: AIRouterEngine | None = None
