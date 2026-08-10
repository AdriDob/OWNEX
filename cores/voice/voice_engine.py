"""OWNEX Voice Engine.

Voice identity abstraction (local-first, provider-swappable):

- ``VoiceProfile``: persisted voice settings (locale es-419, calm operator).
- ``VoicePersonality``: rewrites replies into OWNEX voice rules
  (calm, direct, brief satisfaction, explicit approval asks, no drama).
- ``TTSManager``: provider chain — piper (local CLI) → system_tts fallback.

STT stays client-side (native Capacitor plugin on Android, browser Web
Speech elsewhere); only TTS is served from the backend so mobile gets a
consistent OWNEX voice without depending on the device's TTS.

Config file: ``data/voice_profile.json`` (survives restarts).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.voice.engine")

# Data dir next to the app database (configurable, consistent with other engines).
DEFAULT_DATA_DIR = Path("data")

DEFAULT_PROFILE: dict[str, Any] = {
    "enabled": True,
    "provider": "piper",
    "language": "es",
    "locale": "es-419",
    "speed": 0.95,
    "pitch": 0,
    "volume": 0.85,
    "personality": "calm_operator",
    "fallback": "system_tts",
}

# Piper CLI detection: `piper` binary or the python3 -m piper module.
PIPER_BIN = shutil.which("piper")
PIPER_MODEL_ENV = "OWNEX_PIPER_MODEL"
PIPER_DEFAULT_MODEL = "es_MX-ald-medium"  # Spanish (Mexico), male, calm — closest to es-419 neutral.


@dataclass
class VoiceProfile:
    """Persisted OWNEX voice settings."""

    enabled: bool = True
    provider: str = "piper"
    language: str = "es"
    locale: str = "es-419"
    speed: float = 0.95
    pitch: int = 0
    volume: float = 0.85
    personality: str = "calm_operator"
    fallback: str = "system_tts"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> VoiceProfile:
        known = {k: v for k, v in raw.items() if k in DEFAULT_PROFILE}
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VoiceProfileStore:
    """Persistent profile at ``data/voice_profile.json``."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self._path = Path(data_dir) / "voice_profile.json"
        self._profile = self._load()

    def _load(self) -> VoiceProfile:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                return VoiceProfile.from_dict(raw)
        except Exception as exc:  # corrupt file → reset, never crash
            logger.warning("voice profile corrupt (%s); resetting", exc)
        return VoiceProfile()

    def get(self) -> VoiceProfile:
        return self._profile

    def save(self, profile: VoiceProfile) -> VoiceProfile:
        self._profile = profile
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("could not persist voice profile: %s", exc)
        return self._profile


class VoicePersonality:
    """OWNEX voice rules: calm operator, not a supermarket assistant."""

    _EXCITED_STARTS = (
        "¡",
        "!",
        "¡hola",
        "¡buenas",
        "hola!",
        "increíble",
        "¡súper",
        "¡genial",
    )
    _EXCLAMATIONS_EXACT = ("¡", "!!")

    def apply(self, text: str, *, worth_it: bool | None = None) -> str:
        """Normalise a reply into calm, direct operator speech."""
        if not text:
            return text
        text = text.strip()
        lowered = text.lower()
        # Kill greeting excitement.
        for start in self._EXCITED_STARTS:
            if lowered.startswith(start):
                text = text[1:].strip() if text.startswith(("!", "¡")) else text
        # Replace exclaimed markers with a period (no !!!).
        text = text.replace("!!", ".").replace("¡", "").replace("!", ".")
        # Own em-dash style, short sentences.
        text = text.replace("— ", ": ").strip()
        # Register results first: "Resultado: ..." framing for worth decisions.
        if worth_it is not None:
            verdict = "procede" if worth_it else "no es prioridad"
            text = f"Resultado, {verdict}. {text}"
        while ".." in text:
            text = text.replace("..", ".")
        return text.strip(" .") + "."


class TTSManager:
    """Provider chain: piper (local CLI) → system_tts (bottom).

    ``synthesize()`` returns WAV bytes when a local provider is available,
    else ``None`` — callers fall back to browser speechSynthesis (system_tts).
    """

    def __init__(
        self,
        store: VoiceProfileStore | None = None,
        piper_bin: str | None = PIPER_BIN,
    ) -> None:
        self.store = store or VoiceProfileStore()
        self.piper_bin = piper_bin

    def provider_status(self) -> dict[str, str]:
        profile = self.store.get()
        piper_ok = bool(self.piper_bin)
        return {
            "provider": profile.provider,
            "piper_available": "yes" if piper_ok else "no",
            "active": profile.provider if piper_ok or profile.provider == "system_tts" else profile.fallback,
            "model": PIPER_DEFAULT_MODEL if piper_ok else "",
        }

    def synthesize(self, text: str) -> bytes | None:
        """Return WAV bytes via piper, or ``None`` to fall back to system TTS."""
        profile = self.store.get()
        wanted = profile.provider
        if wanted == "piper" and self.piper_bin:
            try:
                return self._piper_wav(text, profile)
            except Exception as exc:
                logger.warning("piper synthesis failed (%s); falling back", exc)
        return None

    def _piper_wav(self, text: str, profile: VoiceProfile) -> bytes:
        model = PIPER_DEFAULT_MODEL
        with tempfile.TemporaryDirectory(prefix="ownex_tts_") as tmp:
            out_wav = Path(tmp) / "out.wav"
            cmd = [
                self.piper_bin or "piper",
                "--model",
                model,
                "--output_file",
                str(out_wav),
                "--length_scale",
                str(1.0 / profile.speed if profile.speed > 0 else 1.0),
            ]
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"piper exited {proc.returncode}: {proc.stderr[:200]}")
            if not out_wav.exists():
                raise RuntimeError("piper produced no audio")
            return out_wav.read_bytes()


# Module singletons (consistent with the voice router style).
_profile_store: VoiceProfileStore | None = None
_tts_manager: TTSManager | None = None


def get_profile_store() -> VoiceProfileStore:
    global _profile_store
    if _profile_store is None:
        _profile_store = VoiceProfileStore()
    return _profile_store


def get_tts_manager() -> TTSManager:
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager(get_profile_store())
    return _tts_manager


def personality() -> VoicePersonality:
    return VoicePersonality()
