"""Tests for the OWNEX voice engine (profile, personality, TTS manager)."""

from __future__ import annotations

from pathlib import Path

from cores.voice.voice_engine import (
    VoicePersonality,
    VoiceProfile,
    VoiceProfileStore,
    get_tts_manager,
)


class TestVoiceProfile:
    def test_defaults_follow_owner_spec(self) -> None:
        p = VoiceProfile()
        assert p.provider == "piper"
        assert p.language == "es"
        assert p.locale == "es-419"
        assert p.speed == 0.95
        assert p.pitch == 0
        assert p.volume == 0.85
        assert p.personality == "calm_operator"
        assert p.fallback == "system_tts"

    def test_roundtrip_dict(self) -> None:
        p = VoiceProfile.from_dict(VoiceProfile().to_dict())
        assert p.locale == "es-419"
        assert p.speed == 0.95

    def test_from_dict_ignores_unknown_keys(self) -> None:
        p = VoiceProfile.from_dict({"speed": 0.9, "port": 8080, "model": "x"})
        assert p.speed == 0.9
        assert p.personality == "calm_operator"

    def test_store_persists(self, tmp_path: Path) -> None:
        store = VoiceProfileStore(tmp_path)
        store.save(VoiceProfile(speed=0.9, locale="es-MX"))
        loaded = store.get()
        assert loaded.speed == 0.9
        assert loaded.locale == "es-MX"
        assert loaded.personality == "calm_operator"

    def test_store_survives_reload(self, tmp_path: Path) -> None:
        store = VoiceProfileStore(tmp_path)
        store.save(VoiceProfile(speed=0.97))
        loaded = VoiceProfileStore(tmp_path).get()
        assert loaded.speed == 0.97

    def test_store_tolerates_corrupt_file(self, tmp_path: Path) -> None:
        store = VoiceProfileStore(tmp_path)
        (tmp_path / "voice_profile.json").write_text("{not json")
        p = store.get()
        assert p.locale == "es-419"


class TestVoicePersonality:
    def test_calm_operator_strips_excitement(self) -> None:
        v = VoicePersonality()
        out = v.apply("¡Hola! Increíble, es tu mejor día!!")
        assert "¡" not in out
        assert "!!" not in out
        assert "!" not in out

    def test_applies_result_verdict(self) -> None:
        v = VoicePersonality()
        out = v.apply("Hay una oportunidad lucrativa", worth_it=True)
        assert out.startswith("Resultado, procede")

    def test_applies_negative_verdict(self) -> None:
        v = VoicePersonality()
        out = v.apply("No hay nada relevante", worth_it=False)
        assert out.startswith("Resultado, no es prioridad")

    def test_no_verdict_keeps_text(self) -> None:
        v = VoicePersonality()
        out = v.apply("El sistema está operativo")
        assert out.startswith("El sistema está operativo")
        assert not out.startswith("Resultado")


class TestTTSManager:
    def test_provider_status_honest_when_piper_absent(self) -> None:
        m = get_tts_manager()
        st = m.provider_status()
        assert st["provider"] == "piper"
        assert st["piper_available"] in ("yes", "no")
        if st["piper_available"] == "no":
            assert st["active"] == "system_tts"
            assert st["model"] == ""

    def test_synthesize_returns_none_without_piper(self, monkeypatch) -> None:
        from cores.voice.voice_engine import TTSManager, VoiceProfileStore

        m = TTSManager(VoiceProfileStore(), piper_bin=None)
        assert m.synthesize("Hola") is None
        assert m.provider_status()["piper_available"] == "no"
