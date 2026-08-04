"""Voice Interface Layer — provider-agnostic voice I/O with Alexa-ready abstraction.

Supports:
- Local microphone input (speech-to-text)
- Text-to-speech output
- Voice command parsing
- Alexa Skills Kit compatible abstraction
- Multiple TTS/STT providers
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("ownex.voice")


class VoiceProvider(Enum):
    """Supported voice providers."""

    LOCAL = "local"  # Local STT/TTS (Whisper, Piper, etc.)
    AZURE = "azure"  # Azure Cognitive Services
    AWS = "aws"  # AWS Polly/Transcribe
    GOOGLE = "google"  # Google Cloud Speech/Text-to-Speech
    ELEVENLABS = "elevenlabs"  # ElevenLabs TTS
    OPENAI = "openai"  # OpenAI Whisper/TTS
    ALEXA = "alexa"  # Alexa Skills Kit


class VoiceLanguage(Enum):
    """Supported languages."""

    EN_US = "en-US"
    EN_GB = "en-GB"
    ES_ES = "es-ES"
    ES_MX = "es-MX"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    IT_IT = "it-IT"
    PT_BR = "pt-BR"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    ZH_CN = "zh-CN"


@dataclass
class VoiceConfig:
    """Voice interface configuration."""

    # Provider settings
    stt_provider: VoiceProvider = VoiceProvider.LOCAL
    tts_provider: VoiceProvider = VoiceProvider.LOCAL

    # Language
    language: VoiceLanguage = VoiceLanguage.EN_US

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024

    # STT settings
    stt_model: str = "base"  # Whisper model size
    stt_threshold: float = 0.5  # Confidence threshold
    silence_timeout: float = 2.0  # Seconds of silence to stop recording
    max_recording_seconds: int = 30

    # TTS settings
    tts_voice: str = "default"
    tts_speed: float = 1.0
    tts_pitch: float = 1.0

    # Wake word
    wake_word: str = "ownx"
    wake_word_sensitivity: float = 0.5

    # Continuous listening
    continuous_listening: bool = False

    # Alexa integration
    alexa_skill_id: str | None = None
    alexa_endpoint: str | None = None


@dataclass
class VoiceCommand:
    """Parsed voice command."""

    id: str
    raw_text: str
    intent: str
    entities: dict[str, Any]
    confidence: float
    timestamp: datetime
    session_id: str


@dataclass
class SpeechResult:
    """Result of speech recognition."""

    text: str
    confidence: float
    language: str
    duration: float
    alternatives: list[str] = field(default_factory=list)


@dataclass
class TTSResult:
    """Result of text-to-speech."""

    audio_data: bytes
    format: str  # "wav", "mp3", "ogg"
    duration: float
    sample_rate: int


# ──────────────────────────────────────────────────────────────────────────
# PROVIDER INTERFACES
# ──────────────────────────────────────────────────────────────────────────


class STTProvider(ABC):
    """Abstract speech-to-text provider."""

    @abstractmethod
    async def initialize(self, config: VoiceConfig) -> bool:
        """Initialize the provider."""
        pass

    @abstractmethod
    async def transcribe(self, audio_data: bytes, config: VoiceConfig) -> SpeechResult:
        """Transcribe audio to text."""
        pass

    @abstractmethod
    async def transcribe_stream(self, audio_stream, config: VoiceConfig) -> SpeechResult:
        """Transcribe streaming audio."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


class TTSProvider(ABC):
    """Abstract text-to-speech provider."""

    @abstractmethod
    async def initialize(self, config: VoiceConfig) -> bool:
        """Initialize the provider."""
        pass

    @abstractmethod
    async def synthesize(self, text: str, config: VoiceConfig) -> TTSResult:
        """Synthesize text to speech."""
        pass

    @abstractmethod
    async def synthesize_stream(self, text: str, config: VoiceConfig):
        """Stream synthesized audio."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    def get_available_voices(self) -> list[dict[str, str]]:
        """Get list of available voices."""
        pass


# ──────────────────────────────────────────────────────────────────────────
# LOCAL PROVIDERS (Whisper + Piper)
# ──────────────────────────────────────────────────────────────────────────


class LocalSTTProvider(STTProvider):
    """Local STT using Whisper."""

    def __init__(self):
        self._model = None
        self._initialized = False

    async def initialize(self, config: VoiceConfig) -> bool:
        try:
            import whisper

            self._model = whisper.load_model(config.stt_model)
            self._initialized = True
            logger.info("Local STT (Whisper) initialized with model: %s", config.stt_model)
            return True
        except ImportError:
            logger.warning("Whisper not installed, local STT unavailable")
            return False
        except Exception as e:
            logger.error("Failed to initialize local STT: %s", e)
            return False

    async def transcribe(self, audio_data: bytes, config: VoiceConfig) -> SpeechResult:
        if not self._initialized:
            return SpeechResult("", 0.0, config.language.value, 0.0)

        import os
        import tempfile

        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            result = self._model.transcribe(
                temp_path,
                language=config.language.value.split("-")[0],
                fp16=False,
            )

            return SpeechResult(
                text=result["text"].strip(),
                confidence=1.0,  # Whisper doesn't provide confidence
                language=config.language.value,
                duration=0.0,
            )
        finally:
            os.unlink(temp_path)

    async def transcribe_stream(self, audio_stream, config: VoiceConfig) -> SpeechResult:
        # For streaming, accumulate and transcribe
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)

        audio_data = b"".join(chunks)
        return await self.transcribe(audio_data, config)

    def get_name(self) -> str:
        return "local_whisper"

    def is_available(self) -> bool:
        return self._initialized


class LocalTTSProvider(TTSProvider):
    """Local TTS using Piper."""

    def __init__(self):
        self._piper_path = None
        self._voice_path = None
        self._initialized = False

    async def initialize(self, config: VoiceConfig) -> bool:
        import os
        import shutil

        # Check for piper
        self._piper_path = shutil.which("piper")
        if not self._piper_path:
            logger.warning("Piper not found, local TTS unavailable")
            return False

        # Find voice model
        voice_dir = os.path.expanduser("~/.local/share/piper/voices")
        if os.path.exists(voice_dir):
            for file in os.listdir(voice_dir):
                if file.endswith(".onnx") and config.language.value.split("-")[0] in file:
                    self._voice_path = os.path.join(voice_dir, file)
                    break

        if not self._voice_path:
            logger.warning("No Piper voice model found for %s", config.language.value)
            return False

        self._initialized = True
        logger.info("Local TTS (Piper) initialized with voice: %s", self._voice_path)
        return True

    async def synthesize(self, text: str, config: VoiceConfig) -> TTSResult:
        if not self._initialized:
            return TTSResult(b"", "wav", 0.0, config.sample_rate)

        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        try:
            cmd = [
                self._piper_path,
                "--model",
                self._voice_path,
                "--output_file",
                output_path,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=text.encode())

            if proc.returncode != 0:
                logger.error("Piper TTS failed: %s", stderr.decode())
                return TTSResult(b"", "wav", 0.0, config.sample_rate)

            with open(output_path, "rb") as f:
                audio_data = f.read()

            # Estimate duration
            duration = len(audio_data) / (config.sample_rate * 2)  # 16-bit mono

            return TTSResult(
                audio_data=audio_data,
                format="wav",
                duration=duration,
                sample_rate=config.sample_rate,
            )
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    async def synthesize_stream(self, text: str, config: VoiceConfig):
        """Stream synthesized audio."""
        if not self._initialized:
            return

        result = await self.synthesize(text, config)
        yield result.audio_data

    def get_name(self) -> str:
        return "local_piper"

    def is_available(self) -> bool:
        return self._initialized

    def get_available_voices(self) -> list[dict[str, str]]:
        return [{"id": "default", "name": "Piper Default", "language": "en-US"}]


# ──────────────────────────────────────────────────────────────────────────
# ALEXA SKILLS KIT ADAPTER
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class AlexaRequest:
    """Incoming Alexa request."""

    request_id: str
    session_id: str
    intent_name: str
    slots: dict[str, Any]
    raw_request: dict[str, Any]


@dataclass
class AlexaResponse:
    """Outgoing Alexa response."""

    output_speech: str
    reprompt: str | None = None
    should_end_session: bool = True
    card_title: str | None = None
    card_content: str | None = None
    directives: list[dict] = field(default_factory=list)


class AlexaAdapter:
    """Adapter for Alexa Skills Kit integration."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self._intent_handlers: dict[str, Callable] = {}
        self._session_attributes: dict[str, dict] = {}

    def register_intent(self, intent_name: str, handler: Callable) -> None:
        """Register an intent handler."""
        self._intent_handlers[intent_name] = handler

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming Alexa request."""
        request_type = request.get("request", {}).get("type")

        if request_type == "LaunchRequest":
            return self._build_response(
                "Welcome to OWNEX. How can I help you?",
                should_end_session=False,
            )

        elif request_type == "IntentRequest":
            return await self._handle_intent(request)

        elif request_type == "SessionEndedRequest":
            return self._build_response("", should_end_session=True)

        return self._build_response("I'm not sure how to handle that.")

    async def _handle_intent(self, request: dict) -> dict:
        intent = request.get("request", {}).get("intent", {})
        intent_name = intent.get("name")
        slots = intent.get("slots", {})
        session = request.get("session", {})
        session_id = session.get("sessionId", "")

        # Extract slot values
        slot_values = {}
        for name, slot in slots.items():
            slot_values[name] = slot.get("value")

        # Call handler
        handler = self._intent_handlers.get(intent_name)
        if handler:
            alexa_request = AlexaRequest(
                request_id=request["request"]["requestId"],
                session_id=session_id,
                intent_name=intent_name,
                slots=slot_values,
                raw_request=request,
            )

            try:
                response_text = await handler(alexa_request)
                return self._build_response(response_text)
            except Exception as e:
                logger.error("Alexa intent handler failed: %s", e)
                return self._build_response("Sorry, I encountered an error.")

        return self._build_response("I don't know how to handle that request.")

    def _build_response(
        self,
        speech: str,
        reprompt: str | None = None,
        should_end_session: bool = True,
        card_title: str | None = None,
        card_content: str | None = None,
    ) -> dict:
        """Build Alexa response format."""
        response = {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": speech,
                },
                "shouldEndSession": should_end_session,
            },
        }

        if reprompt:
            response["response"]["reprompt"] = {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": reprompt,
                },
            }

        if card_title and card_content:
            response["response"]["card"] = {
                "type": "Simple",
                "title": card_title,
                "content": card_content,
            }

        return response


# ──────────────────────────────────────────────────────────────────────────
# COMMAND PARSER
# ──────────────────────────────────────────────────────────────────────────


class VoiceCommandParser:
    """Parse natural language into structured commands."""

    def __init__(self):
        self._patterns: list[dict] = []
        self._register_builtin_patterns()

    def _register_builtin_patterns(self) -> None:
        """Register built-in command patterns."""
        patterns = [
            # Navigation commands
            {
                "intent": "navigate",
                "patterns": [
                    r"(go|ve|ir a|navigate to|abrir).*(dashboard|mission control|analytics|settings|terminal)",
                    r"(abrir|ir).*(dashboard|mission control|analytics|settings|terminal)",
                ],
                "entities": ["destination"],
            },
            # Workflow commands
            {
                "intent": "start_workflow",
                "patterns": [
                    r"(inicia|start|ejecuta|run).*(workflow|proceso)",
                    r"(inicia|start).*(feature development|bug fix|revenue opportunity)",
                ],
                "entities": ["workflow_type", "feature_name"],
            },
            {
                "intent": "pause_workflow",
                "patterns": [
                    r"(pausa|pause|detener|stop).*(workflow|proceso)",
                ],
                "entities": ["workflow_id"],
            },
            {
                "intent": "resume_workflow",
                "patterns": [
                    r"(reanuda|resume|continuar).*(workflow|proceso)",
                ],
                "entities": ["workflow_id"],
            },
            {
                "intent": "cancel_workflow",
                "patterns": [
                    r"(cancela|cancel|abortar).*(workflow|proceso)",
                ],
                "entities": ["workflow_id"],
            },
            # Agent commands
            {
                "intent": "activate_agent",
                "patterns": [
                    r"(activa|activate|inicia).*(agente|agent).*(coding|debug|qa|security|orchestrator)",
                    r"(coding|debug|qa|security|orchestrator).*(agente|agent)",
                ],
                "entities": ["agent_id"],
            },
            {
                "intent": "pause_agent",
                "patterns": [
                    r"(pausa|pause).*(agente|agent).*(coding|debug|qa|security|orchestrator)",
                ],
                "entities": ["agent_id"],
            },
            # Status commands
            {
                "intent": "get_status",
                "patterns": [
                    r"(status|estado|how.*going|what.*happening|what.*doing)",
                    r"(show|give|dame).*(status|summary|report|estado|resumen)",
                ],
                "entities": [],
            },
            # Search commands
            {
                "intent": "search",
                "patterns": [
                    r"(busca|search|look for|find).*(findings|hallazgos|vulnerabilities|vulnerabilidades)",
                    r"(filtrar|filter).*(por|by|for).*(target|sql|xss)",
                ],
                "entities": ["query"],
            },
            # Theme commands
            {
                "intent": "set_theme",
                "patterns": [
                    r"(cambia|change|set).*(tema|theme).*(cyber|ps5|minimal|dark)",
                    r"(activa|activate).*(modo|mode).*(ps5|cyber)",
                ],
                "entities": ["theme"],
            },
            # Discovery commands
            {
                "intent": "discover_opportunities",
                "patterns": [
                    r"(find|search|look for|discover|show).*(opportunit|work|task|job)",
                    r"(new|fresh|latest).*(opportunit|work|task)",
                ],
                "entities": ["category", "platform"],
            },
            # Task commands
            {
                "intent": "list_tasks",
                "patterns": [
                    r"(list|show|what).*(task|pending|queue|tarea|pendiente)",
                    r"(pending|waiting).*(task|approval|tarea)",
                ],
                "entities": ["status"],
            },
            {
                "intent": "approve_task",
                "patterns": [
                    r"(approve|accept|yes|go ahead|aprueba|sí).*(task|#?\d+|tarea)",
                ],
                "entities": ["task_id"],
            },
            {
                "intent": "reject_task",
                "patterns": [
                    r"(reject|deny|no|decline|rechaza|no).*(task|#?\d+|tarea)",
                ],
                "entities": ["task_id", "reason"],
            },
            # Mode commands
            {
                "intent": "set_mode",
                "patterns": [
                    r"(set|change|switch|cambia|cambiar).*(mode|level|nivel).*(observer|preparer|supervisor|autonomous)",
                    r"(go|enter|ir a).*(observer|preparer|supervisor|autonomous).*(mode|level|nivel)",
                ],
                "entities": ["mode"],
            },
            # Report commands
            {
                "intent": "generate_report",
                "patterns": [
                    r"(generate|create|make|prepare|genera|crea).*(report|summary|reporte|resumen)",
                    r"(daily|weekly|monthly|diario|semanal|mensual).*(report|summary|reporte|resumen)",
                ],
                "entities": ["period", "type"],
            },
            # Learning commands
            {
                "intent": "show_learning",
                "patterns": [
                    r"(show|what|muestra).*(learn|learned|pattern|insight|aprendizaje|patrón)",
                ],
                "entities": [],
            },
            # Help
            {
                "intent": "help",
                "patterns": [
                    r"(help|what can you do|commands|ayuda|qué puedes hacer|comandos)",
                ],
                "entities": [],
            },
            # Stop/Cancel
            {
                "intent": "stop",
                "patterns": [
                    r"(stop|cancel|quit|exit|never mind|detente|cancelar|salir)",
                ],
                "entities": [],
            },
        ]

        import re

        for p in patterns:
            p["compiled"] = [re.compile(pat, re.IGNORECASE) for pat in p["patterns"]]
            self._patterns.append(p)

    def parse(self, text: str, session_id: str) -> VoiceCommand:
        """Parse text into a voice command."""
        text_lower = text.lower().strip()

        best_match = None
        best_confidence = 0.0

        for pattern in self._patterns:
            for compiled in pattern["compiled"]:
                match = compiled.search(text_lower)
                if match:
                    # Simple confidence based on match length
                    confidence = len(match.group(0)) / len(text_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = pattern

        if best_match:
            intent = best_match["intent"]
            entities = self._extract_entities(text, best_match.get("entities", []))
        else:
            intent = "unknown"
            entities = {}
            best_confidence = 0.1

        return VoiceCommand(
            id=str(uuid.uuid4())[:8],
            raw_text=text,
            intent=intent,
            entities=entities,
            confidence=best_confidence,
            timestamp=datetime.now(UTC),
            session_id=session_id,
        )

    def _extract_entities(self, text: str, entity_types: list[str]) -> dict[str, Any]:
        """Extract entities from text."""
        entities = {}
        text_lower = text.lower()

        # Destination entity (navigation)
        if "destination" in entity_types:
            destinations = ["dashboard", "mission control", "analytics", "settings", "terminal"]
            for dest in destinations:
                if dest in text_lower:
                    entities["destination"] = dest.replace(" ", "_")
                    break

        # Workflow type entity
        if "workflow_type" in entity_types:
            workflows = ["feature development", "bug fix", "revenue opportunity"]
            for wf in workflows:
                if wf in text_lower:
                    entities["workflow_type"] = wf.replace(" ", "_")
                    break

        # Feature name entity
        if "feature_name" in entity_types:
            import re

            # Extract feature name after "de" or "for"
            match = re.search(r"(?:de|for|por)\s+(.+)", text_lower)
            if match:
                entities["feature_name"] = match.group(1).strip()

        # Agent ID entity
        if "agent_id" in entity_types:
            agents = [
                "orchestrator",
                "architecture",
                "coding",
                "debug",
                "qa",
                "security",
                "documentation",
                "research",
                "product",
                "revenue",
                "automation",
                "infrastructure",
                "evolution",
            ]
            for agent in agents:
                if agent in text_lower:
                    entities["agent_id"] = agent
                    break

        # Mode entity
        if "mode" in entity_types:
            for mode in ["observer", "preparer", "supervisor", "autonomous"]:
                if mode in text_lower:
                    entities["mode"] = mode.upper()
                    break

        # Task ID entity
        if "task_id" in entity_types:
            import re

            match = re.search(r"#?(\d+)", text)
            if match:
                entities["task_id"] = match.group(1)

        # Category entity
        if "category" in entity_types:
            categories = ["bug bounty", "dev bounty", "freelance", "ai work", "data task"]
            for cat in categories:
                if cat in text_lower:
                    entities["category"] = cat
                    break

        # Theme entity
        if "theme" in entity_types:
            themes = ["cyber", "ps5", "minimal", "dark"]
            for theme in themes:
                if theme in text_lower:
                    entities["theme"] = theme
                    break

        # Query entity (search)
        if "query" in entity_types:
            import re

            # Extract query after keywords
            match = re.search(r"(?:busca|search|find|filtrar|filter)\s+(.+)", text_lower)
            if match:
                entities["query"] = match.group(1).strip()

        return entities


# ──────────────────────────────────────────────────────────────────────────
# VOICE INTERFACE
# ──────────────────────────────────────────────────────────────────────────


class VoiceInterface:
    """
    Main voice interface — orchestrates STT, TTS, command parsing, and Alexa.

    Provider-agnostic: can use local, cloud, or Alexa providers.
    """

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()
        self.parser = VoiceCommandParser()

        # Providers
        self._stt: STTProvider | None = None
        self._tts: TTSProvider | None = None
        self._alexa: AlexaAdapter | None = None

        # State
        self._listening = False
        self._session_id = str(uuid.uuid4())[:8]
        self._command_handlers: dict[str, Callable] = {}

        # Callbacks
        self._on_command: Callable[[VoiceCommand], Any] | None = None
        self._on_speech_start: Callable | None = None
        self._on_speech_end: Callable | None = None

        self.event_bus = get_core_event_bus()
        logger.info("VoiceInterface initialized")

    async def initialize(self) -> bool:
        """Initialize voice providers."""
        success = True

        # Initialize STT
        if self.config.stt_provider == VoiceProvider.LOCAL:
            self._stt = LocalSTTProvider()
            success &= await self._stt.initialize(self.config)

        # Initialize TTS
        if self.config.tts_provider == VoiceProvider.LOCAL:
            self._tts = LocalTTSProvider()
            success &= await self._tts.initialize(self.config)

        # Initialize Alexa adapter
        if self.config.alexa_skill_id:
            self._alexa = AlexaAdapter(self.config)
            self._register_alexa_intents()

        if success:
            logger.info(
                "Voice interface initialized (STT: %s, TTS: %s)",
                self.config.stt_provider.value,
                self.config.tts_provider.value,
            )
        else:
            logger.warning("Voice interface partially initialized")

        return success

    def _register_alexa_intents(self) -> None:
        """Register default Alexa intents."""
        if not self._alexa:
            return

        async def handle_discover(request: AlexaRequest) -> str:
            return "I'll search for new opportunities. This may take a moment."

        async def handle_status(request: AlexaRequest) -> str:
            return "OWNEX is running. I have 5 active tasks and found 12 new opportunities today."

        async def handle_help(request: AlexaRequest) -> str:
            return "You can ask me to find opportunities, check status, list tasks, approve tasks, or change autonomy mode."

        self._alexa.register_intent("DiscoverOpportunitiesIntent", handle_discover)
        self._alexa.register_intent("GetStatusIntent", handle_status)
        self._alexa.register_intent("AMAZON.HelpIntent", handle_help)
        self._alexa.register_intent("AMAZON.StopIntent", lambda r: "Goodbye!")
        self._alexa.register_intent("AMAZON.CancelIntent", lambda r: "Cancelled.")

    def register_command_handler(self, intent: str, handler: Callable[[VoiceCommand], Any]) -> None:
        """Register a handler for a parsed command intent."""
        self._command_handlers[intent] = handler

    def set_callbacks(
        self,
        on_command: Callable[[VoiceCommand], Any] | None = None,
        on_speech_start: Callable | None = None,
        on_speech_end: Callable | None = None,
    ) -> None:
        """Set event callbacks."""
        self._on_command = on_command
        self._on_speech_start = on_speech_start
        self._on_speech_end = on_speech_start

    async def listen_once(self) -> VoiceCommand | None:
        """Listen for a single voice command."""
        if not self._stt or not self._stt.is_available():
            logger.error("STT not available")
            return None

        self._listening = True

        if self._on_speech_start:
            await self._on_speech_start()

        try:
            # In real implementation, capture audio from microphone
            # For now, simulate with a placeholder
            logger.info("Listening for command...")

            # Simulate audio capture
            audio_data = await self._capture_audio()

            if not audio_data:
                return None

            # Transcribe
            result = await self._stt.transcribe(audio_data, self.config)

            if result.text.strip():
                # Parse command
                command = self.parser.parse(result.text, self._session_id)

                # Emit event
                self.event_bus.publish(
                    "voice:command",
                    {
                        "command": command.__dict__,
                    },
                )

                # Call handler
                if self._on_command:
                    await self._on_command(command)

                return command

        finally:
            self._listening = False
            if self._on_speech_end:
                await self._on_speech_end()

        return None

    async def _capture_audio(self) -> bytes:
        """Capture audio from microphone."""
        # Placeholder - in real implementation use pyaudio/sounddevice
        # Return dummy audio data for testing
        return b"\x00" * (self.config.sample_rate * 2)  # 1 second of silence

    async def speak(self, text: str) -> bool:
        """Speak text using TTS."""
        if not self._tts or not self._tts.is_available():
            logger.error("TTS not available")
            return False

        try:
            start = time.time()
            result = await self._tts.synthesize(text, self.config)

            # In real implementation, play audio
            # For now, just log
            logger.info("TTS: %s (%.2fs)", text[:50], time.time() - start)

            self.event_bus.publish(
                "voice:spoken",
                {
                    "text": text,
                    "duration": result.duration,
                },
            )

            return True

        except Exception as e:
            logger.error("TTS failed: %s", e)
            return False

    async def speak_stream(self, text: str):
        """Stream TTS audio."""
        if not self._tts or not self._tts.is_available():
            return

        async for chunk in self._tts.synthesize_stream(text, self.config):
            # In real implementation, stream to audio output
            yield chunk

    async def handle_alexa_request(self, request: dict) -> dict:
        """Handle incoming Alexa request."""
        if not self._alexa:
            return {
                "version": "1.0",
                "response": {"outputSpeech": {"type": "PlainText", "text": "Alexa not configured"}},
            }

        return await self._alexa.handle_request(request)

    def get_status(self) -> dict[str, Any]:
        """Get voice interface status."""
        return {
            "listening": self._listening,
            "session_id": self._session_id,
            "config": {
                "stt_provider": self.config.stt_provider.value,
                "tts_provider": self.config.tts_provider.value,
                "language": self.config.language.value,
                "wake_word": self.config.wake_word,
                "continuous": self.config.continuous_listening,
            },
            "providers": {
                "stt": self._stt.get_name() if self._stt else None,
                "tts": self._tts.get_name() if self._tts else None,
                "alexa": self._alexa is not None,
            },
            "stt_available": self._stt.is_available() if self._stt else False,
            "tts_available": self._tts.is_available() if self._tts else False,
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_voice_interface: VoiceInterface | None = None


def get_voice_interface(config: VoiceConfig | None = None) -> VoiceInterface:
    """Get or create the global voice interface."""
    global _voice_interface
    if _voice_interface is None:
        _voice_interface = VoiceInterface(config)
    return _voice_interface


async def initialize_voice(config: VoiceConfig | None = None) -> VoiceInterface:
    """Initialize and return the voice interface."""
    interface = get_voice_interface(config)
    await interface.initialize()
    return interface
