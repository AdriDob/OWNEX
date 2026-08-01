"""Audio Engine - Motor de audio de alta calidad open source.

Integra motores de alta calidad open source para STT y TTS:
- Kokoro TTS (opcional)
- Piper (ya existente)
- XTTS v2 (opcional)
- F5-TTS (opcional)
- Whisper / Faster Whisper (ya existente)
- Silero VAD (opcional)
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.voice_department.audio_engine")


class AudioEngine(StrEnum):
    """Motores de audio disponibles."""
    PIPER = "piper"  # Ya existente, rápida y buena calidad
    KOKORO = "kokoro"  # Alta calidad, más lenta
    XTTS_V2 = "xtts_v2"  # Muy alta calidad, más lenta
    F5_TTS = "f5_tts"  # Emocional, alta calidad
    WHISPER = "whisper"  # Ya existente, robusto
    FASTER_WHISPER = "faster_whisper"  # Más rápido que Whisper
    SILERO_VAD = "silero_vad"  # Voice Activity Detection


class AudioQuality(StrEnum):
    """Niveles de calidad de audio."""
    MINIMAL = "minimal"  # Piper, Whisper base
    STANDARD = "standard"  # Piper, Whisper small
    HIGH = "high"  # Piper, Whisper medium
    PREMIUM = "premium"  # Kokoro, Whisper large
    ULTRA = "ultra"  # XTTS v2, F5-TTS, Whisper large-v3


class HighQualityAudioEngine:
    """Motor de audio de alta calidad."""

    def __init__(self):
        self.current_tts_engine = AudioEngine.PIPER
        self.current_stt_engine = AudioEngine.WHISPER
        self.current_quality = AudioQuality.STANDARD
        self.vad_enabled = False

    def set_tts_engine(self, engine: AudioEngine) -> None:
        """Establecer motor TTS."""
        if engine in [AudioEngine.PIPER, AudioEngine.KOKORO, AudioEngine.XTTS_V2, AudioEngine.F5_TTS]:
            self.current_tts_engine = engine
            logger.info(f"TTS engine set to {engine}")
        else:
            logger.warning(f"Invalid TTS engine: {engine}")

    def set_stt_engine(self, engine: AudioEngine) -> None:
        """Establecer motor STT."""
        if engine in [AudioEngine.WHISPER, AudioEngine.FASTER_WHISPER]:
            self.current_stt_engine = engine
            logger.info(f"STT engine set to {engine}")
        else:
            logger.warning(f"Invalid STT engine: {engine}")

    def set_quality(self, quality: AudioQuality) -> None:
        """Establecer calidad de audio."""
        self.current_quality = quality

        # Ajustar motores según calidad
        if quality == AudioQuality.MINIMAL or quality == AudioQuality.STANDARD:
            self.current_tts_engine = AudioEngine.PIPER
            self.current_stt_engine = AudioEngine.WHISPER
        elif quality == AudioQuality.HIGH:
            self.current_tts_engine = AudioEngine.PIPER
            self.current_stt_engine = AudioEngine.FASTER_WHISPER
        elif quality == AudioQuality.PREMIUM:
            self.current_tts_engine = AudioEngine.KOKORO
            self.current_stt_engine = AudioEngine.WHISPER
        elif quality == AudioQuality.ULTRA:
            self.current_tts_engine = AudioEngine.XTTS_V2
            self.current_stt_engine = AudioEngine.WHISPER

        logger.info(f"Audio quality set to {quality} (TTS: {self.current_tts_engine}, STT: {self.current_stt_engine})")

    def enable_vad(self, enabled: bool) -> None:
        """Habilitar/deshabilitar Voice Activity Detection."""
        self.vad_enabled = enabled
        logger.info(f"VAD {'enabled' if enabled else 'disabled'}")

    def get_engine_config(self) -> dict[str, Any]:
        """Obtener configuración actual de motores."""
        return {
            "tts_engine": self.current_tts_engine.value,
            "stt_engine": self.current_stt_engine.value,
            "quality": self.current_quality.value,
            "vad_enabled": self.vad_enabled,
        }

    def get_engine_recommendation(self, use_case: str) -> dict[str, Any]:
        """Obtener recomendación de motor según caso de uso."""
        recommendations = {
            "realtime": {
                "tts": AudioEngine.PIPER.value,
                "stt": AudioEngine.FASTER_WHISPER.value,
                "quality": AudioQuality.STANDARD.value,
                "reason": "Balance entre velocidad y calidad para interacción en tiempo real",
            },
            "documentation": {
                "tts": AudioEngine.PIPER.value,
                "stt": AudioEngine.WHISPER.value,
                "quality": AudioQuality.HIGH.value,
                "reason": "Alta calidad para lectura clara y precisa",
            },
            "narration": {
                "tts": AudioEngine.KOKORO.value,
                "stt": AudioEngine.WHISPER.value,
                "quality": AudioQuality.PREMIUM.value,
                "reason": "Alta calidad narrativa para experiencia inmersiva",
            },
            "code_review": {
                "tts": AudioEngine.PIPER.value,
                "stt": AudioEngine.FASTER_WHISPER.value,
                "quality": AudioQuality.STANDARD.value,
                "reason": "Rápido para revisión eficiente de código",
            },
            "emotional": {
                "tts": AudioEngine.F5_TTS.value,
                "stt": AudioEngine.WHISPER.value,
                "quality": AudioQuality.ULTRA.value,
                "reason": "Capacidad emocional para narración expresiva",
            },
        }

        return recommendations.get(use_case, recommendations["realtime"])

    def synthesize(self, text: str, config: dict[str, Any] | None = None) -> bytes:
        """Sintetizar texto a audio (wrapper para sistema existente)."""
        # Integrar con cores/voice_interface.py que ya tiene Piper
        # Por ahora, retornar placeholder
        logger.debug(f"Synthesizing text with {self.current_tts_engine}")
        return b"audio_placeholder"

    def transcribe(self, audio_data: bytes, config: dict[str, Any] | None = None) -> str:
        """Transcribir audio a texto (wrapper para sistema existente)."""
        # Integrar con cores/voice_interface.py que ya tiene Whisper
        # Por ahora, retornar placeholder
        logger.debug(f"Transcribing audio with {self.current_stt_engine}")
        return "transcription_placeholder"

    def detect_voice_activity(self, audio_stream) -> bool:
        """Detectar actividad de voz (VAD)."""
        if not self.vad_enabled:
            return True  # Si VAD deshabilitado, asumir que siempre hay voz

        # Integrar con Silero VAD cuando esté disponible
        # Por ahora, retornar placeholder
        logger.debug("Detecting voice activity with Silero VAD")
        return True


# Singleton instance
_high_quality_audio_engine: HighQualityAudioEngine | None = None


def get_high_quality_audio_engine() -> HighQualityAudioEngine:
    """Obtener instancia singleton del High Quality Audio Engine."""
    global _high_quality_audio_engine
    if _high_quality_audio_engine is None:
        _high_quality_audio_engine = HighQualityAudioEngine()
    return _high_quality_audio_engine


def reset_high_quality_audio_engine() -> None:
    """Resetear instancia singleton."""
    global _high_quality_audio_engine
    _high_quality_audio_engine = None
