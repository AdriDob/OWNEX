"""Voice Department - Data Models.

Modelos de datos para el sistema conversacional de voz premium.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ConversationMode(StrEnum):
    """Modos de conversación."""
    NORMAL = "normal"
    TEACH = "teach"  # Explicar todo desde cero
    ENGINEER = "engineer"  # Detalle técnico
    EXECUTIVE = "executive"  # Resumido y estratégico
    MINIMALIST = "minimalist"  # Conciso
    INVESTIGATOR = "investigator"  # Analítico
    MENTOR = "mentor"  # Guiado y constructivo


class VoicePersonality(StrEnum):
    """Personalidades de voz."""
    PROFESSOR = "professor"
    SENIOR_ENGINEER = "senior_engineer"
    EXECUTIVE = "executive"
    MINIMALIST = "minimalist"
    INVESTIGATOR = "investigator"
    MENTOR = "mentor"


class VoiceInteractionType(StrEnum):
    """Tipos de interacción de voz."""
    SPEECH_ONLY = "speech_only"
    TEXT_ONLY = "text_only"
    HYBRID = "hybrid"  # Ambos al mismo tiempo


class AccessibilityMode(StrEnum):
    """Modos de accesibilidad."""
    SILENT = "silent"  # Solo texto, sin voz
    VOICE = "voice"  # Solo voz
    HYBRID = "hybrid"  # Voz + subtítulos
    SUBTITLES = "subtitles"  # Voz + subtítulos automáticos


@dataclass
class VoiceExplanation:
    """Explicación detallada de una acción o concepto."""
    what_did: str  # "Qué hizo"
    why: str  # "Por qué"
    what_modified: str  # "Qué modificó"
    risks_found: list[str]  # "Qué riesgos encontró"
    how_to_revert: str  # "Cómo volver atrás"
    recommendation: str  # "Qué recomienda"
    what_learned: str  # "Qué aprendió"
    technical_detail: str = ""  # Detalle técnico opcional
    analogy: str = ""  # Analogía opcional para explicación simple


@dataclass
class ConversationContext:
    """Contexto de la conversación actual."""
    session_id: str
    user_id: str
    mode: ConversationMode = ConversationMode.NORMAL
    personality: VoicePersonality = VoicePersonality.SENIOR_ENGINEER
    interaction_type: VoiceInteractionType = VoiceInteractionType.HYBRID
    accessibility_mode: AccessibilityMode = AccessibilityMode.HYBRID
    current_task: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    entities_mentioned: list[str] = field(default_factory=list)
    questions_asked: list[str] = field(default_factory=list)
    explanations_given: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


@dataclass
class VoicePreference:
    """Preferencias de voz del usuario."""
    user_id: str
    tone: str = "professional"  # professional, casual, formal
    speed: float = 1.0  # 0.5 a 2.0
    pitch: float = 1.0  # 0.5 a 2.0
    volume: float = 1.0  # 0.0 a 1.0
    language: str = "es-ES"
    auto_explain: bool = True  # Explicar automáticamente
    auto_narrate: bool = True  # Narrar mientras trabaja
    interrupt_threshold: str = "risk_only"  # risk_only, important, always, never
    detail_level: str = "medium"  # minimal, low, medium, high, maximum
    preferred_mode: ConversationMode = ConversationMode.NORMAL
    preferred_personality: VoicePersonality = VoicePersonality.SENIOR_ENGINEER


@dataclass
class VoiceMemory:
    """Memoria de voz del usuario."""
    user_id: str
    previous_explanations: dict[str, VoiceExplanation] = field(default_factory=dict)
    common_questions: dict[str, str] = field(default_factory=dict)  # Pregunta → Respuesta
    error_patterns: list[str] = field(default_factory=list)  # Errores frecuentes
    learning_points: list[str] = field(default_factory=list)  # Puntos aprendidos
    preferred_responses: dict[str, str] = field(default_factory=dict)  # Situación → Respuesta preferida
    last_interaction: datetime | None = None
    interaction_count: int = 0


@dataclass
class SystemNarration:
    """Narración del sistema mientras trabaja."""
    action: str  # "Estoy analizando la arquitectura"
    status: str  # "in_progress", "completed", "error"
    detail: str = ""  # Detalle adicional
    files_involved: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntelligentQuestion:
    """Pregunta inteligente del sistema."""
    question: str
    context: str  # Contexto de la pregunta
    risk_level: str  # "low", "medium", "high", "critical"
    action_required: str  # Acción requerida del usuario
    can_auto_resolve: bool = False
    auto_resolve_if_safe: bool = True
    asked_at: datetime = field(default_factory=datetime.now)


@dataclass
class AutomaticSummary:
    """Resumen automático de actividad."""
    date: datetime
    activities: list[str]
    changes_made: list[str]
    tests_run: list[str]
    opportunities_found: list[str]
    documentation_updated: list[str]
    system_status: str
    recommendations: list[str]
    learnings: list[str]


@dataclass
class VoiceVisualContext:
    """Contexto visual mientras habla."""
    highlight_files: list[str] = field(default_factory=list)
    show_code: bool = False
    code_content: str = ""
    show_graphs: bool = False
    show_progress: bool = False
    progress_value: float = 0.0
    highlight_changes: bool = False
    follow_narration: bool = True
