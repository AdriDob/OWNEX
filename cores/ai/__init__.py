"""OWNEX AI Providers package.

This package contains AI model provider implementations for the ORION ecosystem.
Each provider implements the BaseProvider interface and can be used in the
AI Router for intelligent model fallback.

Providers included:
- opencode_free: Free models via OpenCode
- fcc_proxy: Claude models via FCC Proxy (Anthropic API)
- nvidia_nim: NVIDIA NIM models via NVIDIA platform
- ollama: Local Ollama models
- gooseai: GooseAI NLP-as-a-Service (30% cheaper than competitors)
- custom: User-defined custom providers
"""

# Export all provider classes for easy import
from .providers.custom_provider import CustomProvider
from .providers.fcc_provider import FCCProvider
from .providers.gooseai_provider import GooseAIProvider
from .providers.nvidia_nim_provider import NVIDIANIMProvider
from .providers.ollama_provider import OllamaProvider
from .providers.opencode_provider import OpenCodeProvider

__all__ = [
    "GooseAIProvider",
    "OpenCodeProvider",
    "FCCProvider",
    "NVIDIANIMProvider",
    "OllamaProvider",
    "CustomProvider",
]
