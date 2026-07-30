"""MERLIN Configuration — Office Retro Modernized."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DetailLevel(Enum):
    """Detail level for responses."""
    CONCISE = "concise"
    NORMAL = "normal"
    DETAILED = "detailed"


class ResponseTone(Enum):
    """Tone for responses."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"


class Theme(Enum):
    """Retro office themes."""
    CLASSIC_97 = "classic_97"
    MODERN_RETRO = "modern_retro"
    CYBER_RETRO = "cyber_retro"


@dataclass
class MerlinConfig:
    """Configuration for MERLIN assistant."""

    # Identity
    name: str = "MERLIN"
    avatar: str = "🧙"
    title: str = "Asistente de Inteligencia Autónoma"

    # Personality
    greeting: str = "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma."
    sign_off: str = "— MERLIN, asistente de inteligencia autónoma"

    # Behavior
    detail_level: DetailLevel = DetailLevel.NORMAL
    response_tone: ResponseTone = ResponseTone.PROFESSIONAL
    max_response_length: int = 2000

    # Features
    enable_analytics: bool = True
    enable_learning: bool = True
    enable_memory: bool = True
    enable_context_awareness: bool = True

    # Theme
    theme: Theme = Theme.MODERN_RETRO
    custom_color: Optional[str] = None  # Hex color

    # Office Retro Personality
    office_retro_mode: bool = True
    retro_animations: bool = True
    retro_sounds: bool = False  # Disabled by default for modern feel
    retro_typing_effect: bool = True

    # Memory
    memory_limit: int = 1000  # Maximum conversations to remember
    memory_retention_days: int = 90

    # Capabilities
    capabilities: list[str] = field(default_factory=lambda: [
        "target_analysis",
        "report_generation",
        "workflow_optimization",
        "data_analysis",
        "strategic_planning",
        "technical_assistance"
    ])

    # Integrations
    enable_ownex_integration: bool = True
    enable_retrieval_integration: bool = True
    enable_pulse_integration: bool = True
    enable_forge_integration: bool = True

    # Performance
    max_concurrent_requests: int = 5
    request_timeout: int = 30  # seconds
    streaming_enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "avatar": self.avatar,
            "title": self.title,
            "greeting": self.greeting,
            "sign_off": self.sign_off,
            "detail_level": self.detail_level.value,
            "response_tone": self.response_tone.value,
            "max_response_length": self.max_response_length,
            "enable_analytics": self.enable_analytics,
            "enable_learning": self.enable_learning,
            "enable_memory": self.enable_memory,
            "enable_context_awareness": self.enable_context_awareness,
            "theme": self.theme.value,
            "custom_color": self.custom_color,
            "office_retro_mode": self.office_retro_mode,
            "retro_animations": self.retro_animations,
            "retro_sounds": self.retro_sounds,
            "retro_typing_effect": self.retro_typing_effect,
            "memory_limit": self.memory_limit,
            "memory_retention_days": self.memory_retention_days,
            "capabilities": self.capabilities,
            "enable_ownex_integration": self.enable_ownex_integration,
            "enable_retrieval_integration": self.enable_retrieval_integration,
            "enable_pulse_integration": self.enable_pulse_integration,
            "enable_forge_integration": self.enable_forge_integration,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout": self.request_timeout,
            "streaming_enabled": self.streaming_enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MerlinConfig":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "MERLIN"),
            avatar=data.get("avatar", "🧙"),
            title=data.get("title", "Asistente de Inteligencia Autónoma"),
            greeting=data.get("greeting", "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma."),
            sign_off=data.get("sign_off", "— MERLIN, asistente de inteligencia autónoma"),
            detail_level=DetailLevel(data.get("detail_level", "normal")),
            response_tone=ResponseTone(data.get("response_tone", "professional")),
            max_response_length=data.get("max_response_length", 2000),
            enable_analytics=data.get("enable_analytics", True),
            enable_learning=data.get("enable_learning", True),
            enable_memory=data.get("enable_memory", True),
            enable_context_awareness=data.get("enable_context_awareness", True),
            theme=Theme(data.get("theme", "modern_retro")),
            custom_color=data.get("custom_color"),
            office_retro_mode=data.get("office_retro_mode", True),
            retro_animations=data.get("retro_animations", True),
            retro_sounds=data.get("retro_sounds", False),
            retro_typing_effect=data.get("retro_typing_effect", True),
            memory_limit=data.get("memory_limit", 1000),
            memory_retention_days=data.get("memory_retention_days", 90),
            capabilities=data.get("capabilities", [
                "target_analysis",
                "report_generation",
                "workflow_optimization",
                "data_analysis",
                "strategic_planning",
                "technical_assistance"
            ]),
            enable_ownex_integration=data.get("enable_ownex_integration", True),
            enable_retrieval_integration=data.get("enable_retrieval_integration", True),
            enable_pulse_integration=data.get("enable_pulse_integration", True),
            enable_forge_integration=data.get("enable_forge_integration", True),
            max_concurrent_requests=data.get("max_concurrent_requests", 5),
            request_timeout=data.get("request_timeout", 30),
            streaming_enabled=data.get("streaming_enabled", True)
        )
