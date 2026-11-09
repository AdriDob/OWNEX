"""Voice input layer for OWNEX — local Whisper STT.

Speech-to-text only. Command parsing, execution and voice feedback live in
``cores.voice.command_executor`` (single source of truth) and
``cores.voice.voice_engine`` (piper TTS) — this module just turns audio into
text and drives the loop.

100% local: faster-whisper for STT, piper for TTS, no API keys.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
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


def transcribe_audio(audio_path: Path | str, model_size: str = DEFAULT_MODEL_SIZE) -> str | None:
    """Transcribe an audio file to text, or ``None`` when unavailable.

    Args:
        audio_path: Path to the WAV/MP3/M4A file to transcribe.
        model_size: faster-whisper model size (``base`` is enough for commands).
    """
    path = Path(audio_path)
    if not path.exists():
        logger.error("Audio file not found: %s", path)
        return None
    try:
        model = _load_model(model_size)
        segments, _info = model.transcribe(str(path), vad_filter=True)
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


def speak(text: str) -> bool:
    """Speak ``text`` locally. Returns False when no TTS/player is available."""
    wav = synthesize_feedback(text)
    if wav is None:
        return False

    player = shutil.which("aplay") or shutil.which("paplay") or shutil.which("ffplay")
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
        text = transcribe_audio(args.audio, model_size=args.model)
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
