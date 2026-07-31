"""Voice Department - Premium Conversational Intelligence System.

Sistema de conversación por voz de nivel premium que convierte OWNEX en un
verdadero compañero de ingeniería capaz de conversar, razonar, explicar, enseñar
y narrar su trabajo en tiempo real.

Philosophy: OWNEX debe sentirse vivo - capaz de escuchar, comprender, razonar,
explicar, enseñar, preguntar, narrar, avisar, resumir y aprender.
"""

from __future__ import annotations

from cores.voice_department.audio_engine import get_high_quality_audio_engine
from cores.voice_department.conversation_agent import get_conversation_agent
from cores.voice_department.voice_engine import get_voice_engine
from cores.voice_department.voice_memory import get_voice_memory
from cores.voice_department.voice_personalization import get_voice_personalization

__all__ = [
    "get_conversation_agent",
    "get_voice_engine",
    "get_voice_memory",
    "get_voice_personalization",
    "get_high_quality_audio_engine",
]
