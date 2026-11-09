"""Voice input layer for OWNEX — local Whisper STT.

Speech-to-text only. Command parsing, execution and voice feedback live in
``cores.voice.command_executor`` (single source of truth) and
``cores.voice.voice_engine`` (piper TTS) — this module just turns audio into
text and drives the loop.

100% local: faster-whisper for STT, piper for TTS, no API keys.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.voice.command_executor import (
    CommandExecutionResult,
    get_voice_command_executor,
    synthesize_feedback,
)

logger = logging.getLogger("ownex.voice.stt")

DEFAULT_MODEL_SIZE = "base"
_MODEL_CACHE: dict[str, Any] = {}


# ── Speech-to-Text ──────────────────────────────────────────────────────


def _load_model(model_size: str):
    """Load (and cache) a faster-whisper model."""
    from faster_whisper import WhisperModel

    if model_size not in _MODEL_CACHE:
        _MODEL_CACHE[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODEL_CACHE[model_size]


def transcribe_audio(
    audio_path: Path | str,
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str | None = None,
) -> str | None:
    """Transcribe an audio file to text, or ``None`` when unavailable.

    Args:
        audio_path: Path to the WAV/MP3/M4A file to transcribe.
        model_size: faster-whisper model size (``base`` is enough for commands).
        language: Optional ISO code hint (``es``, ``en``); auto-detected when omitted.
    """
    path = Path(audio_path)
    if not path.exists():
        logger.error("Audio file not found: %s", path)
        return None
    try:
        model = _load_model(model_size)
        segments, _info = model.transcribe(str(path), language=language, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text or None
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        return None


def listen_from_mic(timeout: int = 5) -> str | None:
    """Listen from the microphone and transcribe, or ``None`` when no mic is available."""
    try:
        import speech_recognition as sr
    except ImportError:
        logger.debug("speech_recognition not installed; use an audio file")
        return None

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("🎤 Escuchando...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
    except Exception as exc:
        logger.warning("Microphone unavailable: %s", exc)
        return None

    with tempfile.TemporaryDirectory(prefix="ownex_stt_") as tmp:
        wav_path = Path(tmp) / "input.wav"
        wav_path.write_bytes(audio.get_wav_data())
        return transcribe_audio(wav_path)


# ── Spoken feedback ─────────────────────────────────────────────────────

# CLI players able to play the generated WAV (first one wins).
PLAYER_CANDIDATES = ("aplay", "paplay", "ffplay")


def speak(text: str) -> bool:
    """Speak ``text`` locally. Returns False when no TTS/player is available."""
    wav = synthesize_feedback(text)
    if wav is None:
        return False

    player = _find_player()
    if player is None:
        logger.debug("No WAV player found; skipping playback")
        return False

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        handle.write(wav)
        wav_path = Path(handle.name)
    try:
        cmd = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)] if player.endswith("ffplay") else [player, str(wav_path)]
        subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        return True
    finally:
        wav_path.unlink(missing_ok=True)


# ── Command dispatch ────────────────────────────────────────────────────


def execute_text(text: str, confirmed: bool = True) -> CommandExecutionResult:
    """Parse and execute a command string against the central executor."""
    executor = get_voice_command_executor()
    parsed = executor.parse_command(text)
    return asyncio.run(executor.execute_command(parsed, confirmed=confirmed))


def run_voice_loop(speak_feedback: bool = False) -> None:
    """Interactive voice loop: mic if available, else audio-file paths or typed text."""
    print("🎤 OWNEX Voice Pipeline activo")
    print("Decí: 'recall memory', 'xss hackerone', 'capture finding 12', 'list recent engrams'")
    print("Enter vacío = ayuda. Ctrl+C para salir.")
    print("=" * 60)

    executor = get_voice_command_executor()
    try:
        while True:
            text = listen_from_mic(timeout=5)
            if text is None:
                raw = input("📁 Audio, texto, o enter para ayuda: ").strip()
                if not raw:
                    for command in executor.get_available_commands():
                        print(f"  • {command['command_type']}: {command['description']}")
                    continue
                candidate = Path(raw).expanduser()
                if candidate.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac", ".ogg"}:
                    text = transcribe_audio(candidate)
                    if text is None:
                        print("❌ No pude transcribir ese audio")
                        continue
                else:
                    text = raw

            print(f'🎯 Escuchado: "{text}"')
            result = execute_text(text)
            print(f"{'✅' if result.success else '❌'} {result.message}")
            if result.voice_feedback:
                print(f"🗣️  {result.voice_feedback}")
                if speak_feedback:
                    speak(result.voice_feedback)
            for entry in (result.data or {}).get("entries", [])[:5]:
                print(f"   · [{entry.get('vuln_type') or entry.get('platform') or '—'}] {entry.get('lesson', '')[:100]}")

            if text.strip().lower() in {"exit", "quit", "salir"}:
                break
    except KeyboardInterrupt:
        print("\n👋 Interrumpido")


def main() -> None:
    """CLI entry point: ``--audio FILE`` one-shot, ``--text TEXT`` one-shot, else loop."""
    import argparse

    parser = argparse.ArgumentParser(description="OWNEX voice input (local Whisper)")
    parser.add_argument("--audio", type=Path, help="Transcribe one audio file and execute the command")
    parser.add_argument("--text", help="Execute one text command without audio")
    parser.add_argument("--speak", action="store_true", help="Speak feedback with local piper TTS")
    parser.add_argument("--model", default=DEFAULT_MODEL_SIZE, help="faster-whisper model size")
    parser.add_argument("--language", help="ISO language hint (es, en); auto-detect when omitted")
    args = parser.parse_args()

    if args.text:
        result = execute_text(args.text)
        print(f"{'✅' if result.success else '❌'} {result.message}")
        if result.voice_feedback:
            print(f"🗣️  {result.voice_feedback}")
            if args.speak:
                speak(result.voice_feedback)
        return

    if args.audio:
        text = transcribe_audio(args.audio, model_size=args.model, language=args.language)
        if text is None:
            print("❌ No pude transcribir ese audio")
            return
        print(f'📝 Transcrito: "{text}"')
        result = execute_text(text)
        print(f"{'✅' if result.success else '❌'} {result.message}")
        if result.voice_feedback:
            print(f"🗣️  {result.voice_feedback}")
            if args.speak:
                speak(result.voice_feedback)
        return

    run_voice_loop(speak_feedback=args.speak)


if __name__ == "__main__":
    main()


# ── Stack health ────────────────────────────────────────────────────────

_STT_MODULE = "faster_whisper"
_MIC_MODULE = "speech_recognition"


def _has_module(name: str) -> bool:
    """True when ``name`` is importable — checked without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # broken parent package / odd sys.path
        return False


def _find_player() -> str | None:
    """First available CLI player able to play a WAV file."""
    for candidate in PLAYER_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _stt_health() -> dict[str, Any]:
    """Local STT component: faster-whisper, with browser recognition as fallback."""
    available = _has_module(_STT_MODULE)
    return {
        "available": available,
        "provider": "faster-whisper",
        "model": DEFAULT_MODEL_SIZE,
        "model_loaded": DEFAULT_MODEL_SIZE in _MODEL_CACHE,
        "mic_capture": _has_module(_MIC_MODULE),
        "detail": (f"faster-whisper ready (model {DEFAULT_MODEL_SIZE})" if available else "faster-whisper not installed"),
        "fallback": "browser_speech_recognition",
        "fallback_detail": ("the dashboard records audio in the browser and posts it to /api/voice/commands/audio"),
    }


def _tts_health() -> dict[str, Any]:
    """Local TTS component: piper binary plus a real ``.onnx`` voice."""
    fallback_detail = "browser speechSynthesis speaks the reply (/api/voice/tts returns 415 and the dashboard falls back locally)"
    try:
        from cores.voice.voice_engine import (
            PIPER_BIN,
            PIPER_DEFAULT_MODEL,
            get_tts_manager,
            resolve_piper_voice,
        )

        voice_path, _dirs = resolve_piper_voice(PIPER_DEFAULT_MODEL)
        voice_ready = voice_path.exists()
        available = bool(PIPER_BIN) and voice_ready
        if available:
            detail = f"piper ready (voice {voice_path})"
        elif not PIPER_BIN:
            detail = "piper binary not found"
        else:
            detail = f"voice {PIPER_DEFAULT_MODEL} missing (download it into data/piper_voices)"
        return {
            "available": available,
            "provider": "piper",
            "binary": PIPER_BIN,
            "voice": str(voice_path) if voice_ready else None,
            "voice_model": PIPER_DEFAULT_MODEL,
            "active_provider": get_tts_manager().provider_status().get("active"),
            "detail": detail,
            "fallback": "system_tts",
            "fallback_detail": fallback_detail,
        }
    except Exception as exc:  # voice engine unusable → browser TTS only
        return {
            "available": False,
            "provider": "piper",
            "binary": None,
            "voice": None,
            "voice_model": None,
            "active_provider": "system_tts",
            "detail": f"voice engine unavailable ({exc})",
            "fallback": "system_tts",
            "fallback_detail": fallback_detail,
        }


def _player_health() -> dict[str, Any]:
    """Playback component: speak() needs a CLI player for the generated WAV."""
    player_bin = _find_player()
    return {
        "available": player_bin is not None,
        "binary": player_bin,
        "candidates": list(PLAYER_CANDIDATES),
        "detail": (f"CLI player {player_bin}" if player_bin else "no CLI player found (aplay/paplay/ffplay)"),
        "fallback": "browser_audio_element",
        "fallback_detail": ("speak() returns False; the dashboard plays the WAV returned by /api/voice/tts in the browser"),
    }


def voice_stack_health() -> dict[str, Any]:
    """Per-component health of the local voice stack, with honest fallbacks.

    Each component reports whether it is usable, why, and what happens instead
    when it is not — so a missing piece never silently degrades the round-trip.
    """
    stt = _stt_health()
    tts = _tts_health()
    player = _player_health()
    components = {"stt": stt, "tts": tts, "audio_player": player}

    if not stt["available"]:
        status = "unavailable"
    elif not (tts["available"] and player["available"]):
        status = "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "checked_at": datetime.now(UTC).isoformat(),
        "components": components,
        "fallbacks": [f"{name}: {section['fallback_detail']}" for name, section in components.items() if not section["available"]],
    }
