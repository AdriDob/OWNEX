"""Voice Department Tests - Tests para el sistema conversacional de voz."""


import pytest

from cores.voice_department import (
    get_conversation_agent,
    get_high_quality_audio_engine,
    get_voice_accessibility,
    get_voice_department_integrations,
    get_voice_memory,
    get_voice_personalization,
    get_voice_visual_interface,
)
from cores.voice_department.audio_engine import AudioEngine, AudioQuality
from cores.voice_department.models import (
    AccessibilityMode,
    ConversationMode,
    VoicePersonality,
)


class TestConversationAgent:
    """Tests para Conversation Agent."""

    def test_create_context(self):
        """Test crear contexto de conversación."""
        agent = get_conversation_agent()
        context = agent.create_context("test_user_5", "test_session")

        assert context.user_id == "test_user_5"
        assert context.session_id == "test_session"
        assert context.mode is not None
        assert context.personality is not None

    def test_process_input_explain_intent(self):
        """Test procesar input con intención de explicación."""
        agent = get_conversation_agent()
        context = agent.create_context("test_user_6", "test_session")

        result = agent.process_input("¿Qué es esto?", context)

        assert result["intent"] == "explain"
        assert "response" in result
        assert "visual_context" in result

    def test_switch_mode(self):
        """Test cambiar modo de conversación."""
        agent = get_conversation_agent()
        context = agent.create_context("test_user_7", "test_session")

        context = agent.switch_mode(context, ConversationMode.TEACH)

        assert context.mode == ConversationMode.TEACH

    def test_switch_personality(self):
        """Test cambiar personalidad."""
        agent = get_conversation_agent()
        context = agent.create_context("test_user_8", "test_session")

        context = agent.switch_personality(context, VoicePersonality.PROFESSOR)

        assert context.personality == VoicePersonality.PROFESSOR

    def test_generate_explanation(self):
        """Test generar explicación."""
        agent = get_conversation_agent()
        context = agent.create_context("test_user", "test_session")

        explanation = agent.generate_explanation("test_action", context)

        assert explanation.what_did
        assert explanation.why
        assert explanation.how_to_revert

    def test_generate_automatic_summary(self):
        """Test generar resumen automático."""
        agent = get_conversation_agent()

        summary = agent.generate_automatic_summary("test_user")

        assert summary.date
        assert summary.activities
        assert summary.system_status


class TestVoiceMemory:
    """Tests para Voice Memory."""

    def test_get_memory(self):
        """Test obtener memoria de usuario."""
        memory_system = get_voice_memory()
        memory = memory_system.get_memory("test_user_2")

        assert memory.user_id == "test_user_2"
        assert memory.interaction_count >= 1

    def test_save_explanation(self):
        """Test guardar explicación."""
        memory_system = get_voice_memory()
        from cores.voice_department.models import VoiceExplanation

        explanation = VoiceExplanation(
            what_did="Test action",
            why="Test reason",
            what_modified="Test modification",
            risks_found=[],
            how_to_revert="Test revert",
            recommendation="Test recommendation",
            what_learned="Test learning",
        )

        memory_system.save_explanation("test_user_3", "test_topic", explanation)

        retrieved = memory_system.get_previous_explanation("test_user_3", "test_topic")
        assert retrieved.what_did == "Test action"

    def test_has_explained_before(self):
        """Test verificar si ya se explicó."""
        memory_system = get_voice_memory()
        memory_system.get_memory("test_user_4")

        assert not memory_system.has_explained_before("test_user_4", "new_topic")

        # Guardar explicación
        from cores.voice_department.models import VoiceExplanation

        explanation = VoiceExplanation(
            what_did="Test",
            why="Test",
            what_modified="Test",
            risks_found=[],
            how_to_revert="Test",
            recommendation="Test",
            what_learned="Test",
        )
        memory_system.save_explanation("test_user_4", "test_topic", explanation)

        assert memory_system.has_explained_before("test_user_4", "test_topic")


class TestVoicePersonalization:
    """Tests para Voice Personalization."""

    def test_get_preferences(self):
        """Test obtener preferencias."""
        personalization = get_voice_personalization()
        pref = personalization.get_preferences("test_user_10")

        assert pref.user_id == "test_user_10"
        assert pref.tone == "professional"
        assert pref.speed == 1.0

    def test_set_tone(self):
        """Test establecer tono."""
        personalization = get_voice_personalization()
        pref = personalization.set_tone("test_user_11", "casual")

        assert pref.tone == "casual"

    def test_set_speed(self):
        """Test establecer velocidad."""
        personalization = get_voice_personalization()
        pref = personalization.set_speed("test_user_12", 1.5)

        assert pref.speed == 1.5

    def test_set_speed_clamp(self):
        """Test que velocidad se limite entre 0.5 y 2.0."""
        personalization = get_voice_personalization()
        pref = personalization.set_speed("test_user_13", 3.0)

        assert pref.speed == 2.0  # Limitado a máximo

    def test_should_explain(self):
        """Test lógica de auto-explain."""
        personalization = get_voice_personalization()
        pref = personalization.set_auto_explain("test_user_14", True)

        assert personalization.should_explain("test_user_14") is True

    def test_should_narrate(self):
        """Test lógica de auto-narrate."""
        personalization = get_voice_personalization()
        pref = personalization.set_auto_narrate("test_user_15", True)

        assert personalization.should_narrate("test_user_15") is True

    def test_should_interrupt_risk_only(self):
        """Test lógica de interrupción con threshold risk_only."""
        personalization = get_voice_personalization()
        personalization.set_interrupt_threshold("test_user_16", "risk_only")

        assert personalization.should_interrupt("test_user_16", "low") is False
        assert personalization.should_interrupt("test_user_16", "high") is True
        assert personalization.should_interrupt("test_user_16", "critical") is True


class TestAudioEngine:
    """Tests para Audio Engine."""

    def test_get_engine(self):
        """Test obtener motor de audio."""
        engine = get_high_quality_audio_engine()

        assert engine.current_tts_engine == AudioEngine.PIPER
        assert engine.current_stt_engine == AudioEngine.WHISPER
        assert engine.current_quality == AudioQuality.STANDARD

    def test_set_tts_engine(self):
        """Test establecer motor TTS."""
        engine = get_high_quality_audio_engine()
        engine.set_tts_engine(AudioEngine.KOKORO)

        assert engine.current_tts_engine == AudioEngine.KOKORO

    def test_set_invalid_tts_engine(self):
        """Test que motor TTS inválido no se establece."""
        engine = get_high_quality_audio_engine()
        engine.set_tts_engine(AudioEngine.WHISPER)  # WHISPER no es TTS

        # Debería mantener el motor anterior o default
        assert engine.current_tts_engine == AudioEngine.PIPER

    def test_set_quality(self):
        """Test establecer calidad de audio."""
        engine = get_high_quality_audio_engine()
        engine.set_quality(AudioQuality.PREMIUM)

        assert engine.current_quality == AudioQuality.PREMIUM
        assert engine.current_tts_engine == AudioEngine.KOKORO

    def test_get_engine_recommendation(self):
        """Test obtener recomendación de motor."""
        engine = get_high_quality_audio_engine()
        rec = engine.get_engine_recommendation("realtime")

        assert "tts" in rec
        assert "stt" in rec
        assert "quality" in rec
        assert "reason" in rec


class TestVoiceVisualInterface:
    """Tests para Voice Visual Interface."""

    def test_create_visual_context(self):
        """Test crear contexto visual."""
        visual = get_voice_visual_interface()
        context = visual.create_visual_context()

        assert context.follow_narration is True

    def test_highlight_files(self):
        """Test resaltar archivos."""
        visual = get_voice_visual_interface()
        context = visual.highlight_files(["file1.py", "file2.py"])

        assert context.highlight_files == ["file1.py", "file2.py"]

    def test_show_code_snippet(self):
        """Test mostrar código."""
        visual = get_voice_visual_interface()
        context = visual.show_code_snippet("print('hello')", "python")

        assert context.show_code is True
        assert "print('hello')" in context.code_content

    def test_show_progress(self):
        """Test mostrar progreso."""
        visual = get_voice_visual_interface()
        context = visual.show_progress(75.0, "Processing")

        assert context.show_progress is True
        assert context.progress_value == 75.0

    def test_generate_visual_state(self):
        """Test generar estado visual."""
        visual = get_voice_visual_interface()
        state = visual.generate_visual_state()

        assert "highlight_files" in state
        assert "show_code" in state
        assert "show_progress" in state


class TestVoiceAccessibility:
    """Tests para Voice Accessibility."""

    def test_set_mode(self):
        """Test establecer modo de accesibilidad."""
        accessibility = get_voice_accessibility()
        accessibility.set_mode(AccessibilityMode.SILENT)

        assert accessibility.current_mode == AccessibilityMode.SILENT

    def test_should_speak_silent(self):
        """Test que no hable en modo silencioso."""
        accessibility = get_voice_accessibility()
        accessibility.set_mode(AccessibilityMode.SILENT)

        assert accessibility.should_speak() is False

    def test_should_speak_voice(self):
        """Test que hable en modo voz."""
        accessibility = get_voice_accessibility()
        accessibility.set_mode(AccessibilityMode.VOICE)

        assert accessibility.should_speak() is True

    def test_should_show_subtitles_hybrid(self):
        """Test que muestre subtítulos en modo híbrido."""
        accessibility = get_voice_accessibility()
        accessibility.set_mode(AccessibilityMode.HYBRID)
        accessibility.enable_subtitles(True)

        assert accessibility.should_show_subtitles() is True

    def test_add_subtitle(self):
        """Test agregar subtítulo."""
        accessibility = get_voice_accessibility()
        accessibility.set_mode(AccessibilityMode.HYBRID)
        accessibility.enable_subtitles(True)

        accessibility.add_subtitle("Test subtitle", 123.456, "OWNEX")

        assert len(accessibility.subtitle_history) == 1
        assert accessibility.subtitle_history[0]["text"] == "Test subtitle"


class TestVoiceDepartmentIntegrations:
    """Tests para integraciones del Voice Department."""

    def test_get_integrated_status(self):
        """Test obtener estado de integraciones."""
        integrations = get_voice_department_integrations()
        status = integrations.get_integrated_status()

        assert "mission_control" in status
        assert "copilot" in status
        assert "coder_agent" in status
        assert "execution_layer" in status
        assert "workflow_engine" in status
        assert "documentation" in status
        assert "knowledge_graph" in status

    def test_coordinate_visual_with_system(self):
        """Test coordinar visual con sistema."""
        integrations = get_voice_department_integrations()
        visual_config = {"files": ["test.py"]}

        context = integrations.coordinate_visual_with_system("terminal", visual_config)

        assert context.show_code is True
        assert context.highlight_files == ["test.py"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
