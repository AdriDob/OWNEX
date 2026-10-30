"""Model router for OWNEX Finisher — discovery-based, free-first.

Megaprompt §9: "Desarrolla un sistema para descubrir y seleccionar los
mejores modelos disponibles **sin asumir nombres, proveedores o límites
permanentes**."

The previous version hardcoded three model ids. Two of them
(`deepseek-v4-flash-free`, `mimo-7b-free`) no longer exist in the catalog,
which is why workers were dying with provider errors. Every model here is
discovered at runtime; nothing is invented, and no paid model is ever
selected automatically (Constitution rule 3).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

DISCOVERY_TIMEOUT = 30

# Substrings that mean "this model is not for generating code/text".
_NON_CODE_MARKERS = ("embed", "bge-", "e5-", "instructor", "whisper", "tts", "rerank")

# §9: "No confundas un modelo descargado con un modelo gratuito alojado en la
# nube, ni un modelo disponible en un catálogo con acceso garantizado."
# Ollama `:cloud` entries are remote and need separate auth; listing them is
# not access. A dry run proved they fail with UnknownError, so they are not
# treated as available free capacity.
_REMOTE_ONLY_MARKERS = (":cloud",)

# Cheap, observable capability hints derived from the id itself. These are
# INFERRED, never authoritative — that is why they are kept separate from
# `discovered_via` provenance.
_CAPABILITY_HINTS: dict[str, tuple[str, ...]] = {
    "reasoning": ("ultra", "thinking", "reason", "pro", "opus", "sonnet", "max"),
    "code": ("coder", "code", "dev", "step", "flash", "turbo"),
    "long_context": ("ultra", "longcat", "preview", "flash"),
}


@dataclass
class ModelInfo:
    provider: str
    model: str
    free: bool
    context_window: int = 0
    capabilities: list[str] = field(default_factory=list)
    availability: str = "unknown"
    discovered_via: str = "unknown"
    health: str = "unknown"

    @property
    def id(self) -> str:
        return f"{self.provider}/{self.model}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "free": self.free,
            "capabilities": self.capabilities,
            "context_window": self.context_window,
            "discovered_via": self.discovered_via,
        }


class NoFreeModelError(RuntimeError):
    """Raised when no usable free model was discovered.

    §9: dependent tasks must be PAUSED, never silently given an invented
    fallback or a paid model.
    """


class ModelRouter:
    def __init__(self) -> None:
        self.available_models: list[ModelInfo] = []
        self.last_error: str = ""

    # -- discovery ----------------------------------------------------------

    def discover_models(self, force: bool = False) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        errors: list[str] = []

        for discoverer, label in ((self._discover_opencode, "opencode"), (self._discover_ollama, "ollama")):
            try:
                found = discoverer()
                if found:
                    models.extend(found)
                else:
                    errors.append(f"{label}: none discovered")
            except Exception as e:  # discovery must never kill the daemon
                errors.append(f"{label}: {e}")

        # De-duplicate by id, keeping the first (most authoritative) sighting.
        unique: dict[str, ModelInfo] = {}
        for m in models:
            unique.setdefault(m.id, m)

        self.available_models = sorted(unique.values(), key=lambda m: (not m.free, m.id))
        self.last_error = "; ".join(errors)
        return self.available_models

    def _discover_opencode(self) -> list[ModelInfo]:
        """Ask opencode for its real, currently available models."""
        binary = shutil.which("opencode")
        if not binary:
            return []

        result = subprocess.run(
            [binary, "models"],
            capture_output=True,
            text=True,
            timeout=DISCOVERY_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(f"exit {result.returncode}: {result.stderr.strip()[:120]}")

        out: list[ModelInfo] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith(("Provider", "---")):
                continue
            if "/" not in line:
                continue
            provider, _, model = line.partition("/")
            if not provider or not model:
                continue
            if any(marker in model.lower() for marker in _NON_CODE_MARKERS):
                continue
            out.append(
                ModelInfo(
                    provider=provider,
                    model=model,
                    free=self._looks_free(model, provider),
                    context_window=0,  # unknown: never invent
                    capabilities=self._infer_capabilities(model),
                    availability="catalog",
                    discovered_via="opencode models",
                    health="unknown",
                )
            )
        return out

    def _discover_ollama(self) -> list[ModelInfo]:
        binary = shutil.which("ollama")
        if not binary:
            return []
        result = subprocess.run([binary, "list"], capture_output=True, text=True, timeout=DISCOVERY_TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"exit {result.returncode}: {result.stderr.strip()[:120]}")

        out: list[ModelInfo] = []
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if any(marker in name.lower() for marker in _NON_CODE_MARKERS):
                continue
            if any(marker in name.lower() for marker in _REMOTE_ONLY_MARKERS):
                # Remote-only: listed, but access is not guaranteed.
                continue
            out.append(
                ModelInfo(
                    provider="ollama",
                    model=name,
                    free=True,  # local
                    capabilities=self._infer_capabilities(name),
                    availability="local",
                    discovered_via="ollama list",
                )
            )
        return out

    # -- classification -----------------------------------------------------

    @staticmethod
    def _looks_free(model: str, provider: str) -> bool:
        if provider == "ollama":
            return True
        lowered = model.lower()
        return "free" in lowered

    @staticmethod
    def _infer_capabilities(model: str) -> list[str]:
        lowered = model.lower()
        caps = ["chat", "code"]
        for cap, markers in _CAPABILITY_HINTS.items():
            if any(marker in lowered for marker in markers):
                caps.append(cap)
        return sorted(set(caps))

    # -- selection ----------------------------------------------------------

    def free_models(self) -> list[ModelInfo]:
        if not self.available_models:
            self.discover_models()
        return [m for m in self.available_models if m.free]

    def _pick(self, required_capability: str, prefer_local: bool = False) -> str | None:
        """Deterministic, explainable ranking — never alphabetical by accident."""
        candidates = [
            m for m in self.free_models() if required_capability in m.capabilities or required_capability == "any"
        ]
        if not candidates:
            return None

        def score(m: ModelInfo) -> tuple[int, int, int, str]:
            # 1. A verified catalog model beats an unverified local one.
            #    A dry run failed because a listed local/cloud model turned out
            #    to be unreachable; listing is not availability (§9).
            verified = 0 if m.provider == "ollama" else 1
            # 2. Local ollama is preferred only when explicitly requested.
            local = 1 if (prefer_local and m.provider == "ollama") else 0
            # 3. More inferred capabilities = better fit.
            return (local, verified, len(m.capabilities), m.id)

        return sorted(candidates, key=score, reverse=True)[0].id

    def select_best_model(self, task_type: str, prefer_free: bool = True) -> str | None:
        """Return a model id, or None when no suitable free model exists.

        None is meaningful: the caller must PAUSE the task (§9), not invent
        a fallback and never silently pick a paid model.
        """
        if not self.available_models:
            self.discover_models()

        if not prefer_free:
            # Constitutional rule 3: paid models are never selected
            # automatically. Return None so the task goes to a human gate.
            return None

        override = os.environ.get("FINISHER_MODEL_OVERRIDE", "").strip()
        if override:
            return override

        mapping = {
            "frontend": "code",
            "backend": "code",
            "architecture": "reasoning",
            "review": "reasoning",
            "security": "reasoning",
            "quick": "any",
            "documentation": "any",
        }
        capability = mapping.get(task_type, "any")
        # Local ollama is opt-in, never automatic: an unreachable local model
        # costs a full retry cycle.
        prefer_local = os.environ.get("FINISHER_PREFER_LOCAL_MODELS", "0") == "1"
        return self._pick(capability, prefer_local=prefer_local)

    def get_model_for_task(self, task: Any) -> str | None:
        area = getattr(task, "area", "general")
        mapping = {
            "frontend": "frontend",
            "backend": "backend",
            "core_functionality": "backend",
            "data_release": "backend",
            "architecture": "architecture",
            "ai_agents": "architecture",
            "security": "security",
            "testing": "quick",
            "documentation": "documentation",
        }
        return self.select_best_model(mapping.get(area, "any"), prefer_free=True)

    def describe(self) -> dict[str, Any]:
        return {
            "discovered": [m.to_dict() for m in self.available_models],
            "free_count": len(self.free_models()),
            "errors": self.last_error,
        }


model_router = ModelRouter()
