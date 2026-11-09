"""Voice Command Executor — bridges voice commands to executors.

Interprets voice commands and routes them to appropriate executors:
- "claim bounty X" → AlgoraExecutor.claim_issue
- "submit PR for bounty X" → AlgoraExecutor.submit_pr
- "check status of bounty X" → AlgoraExecutor.get_bounty
- "start bounty pipeline for X" → BountyPipeline.execute_bounty

Features:
- Command parsing with regex patterns
- Engram memory commands (recall / lookup / capture / tag / list)
- Expanded vulnerability + platform vocabulary (single source of truth)
- Confirmation for critical actions
- Feedback loop integration
- Local TTS feedback via cores.voice.voice_engine (piper)
- Configurable command mappings
- Comprehensive logging
- Clear voice feedback for errors
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.autonomy.bounty_pipeline import BountyPipeline, get_bounty_pipeline
from core.opportunity.executors import get_executors
from cores.opportunity.feedback import FeedbackOutcome, get_feedback_loop

logger = logging.getLogger("ownex.voice.command_executor")


# ── Vocabulary (single source of truth for spoken matching) ──────────────

# Canonical vuln_type → spoken aliases. Extend here, never in a pattern.
VULN_VOCABULARY: dict[str, tuple[str, ...]] = {
    "sql_injection": ("sql injection", "sql-injection", "sqli"),
    "xss": ("xss", "cross site scripting", "cross-site scripting", "cross-site-scripting"),
    "rce": ("rce", "remote code execution", "command injection", "os command injection"),
    "lfi": ("lfi", "local file inclusion", "path traversal", "directory traversal"),
    "rfi": ("rfi", "remote file inclusion"),
    "ssrf": ("ssrf", "server side request forgery", "server-side request forgery"),
    "xxe": ("xxe", "xml external entity"),
    "csrf": ("csrf", "cross site request forgery", "cross-site request forgery"),
    "idor": ("idor", "insecure direct object reference", "broken object level authorization"),
    "open_redirect": ("open redirect", "open-redirect", "unvalidated redirect"),
    "auth_bypass": ("auth bypass", "authentication bypass", "authorization bypass", "broken authentication"),
    "subdomain_takeover": ("subdomain takeover", "dangling dns"),
    "graphql": ("graphql", "graphql introspection", "graphql injection"),
    "jwt": ("jwt", "json web token", "jwt confusion"),
    "prototype_pollution": ("prototype pollution",),
    "business_logic": ("business logic", "business-logic flaw"),
    "info_disclosure": ("information disclosure", "info disclosure", "sensitive data exposure"),
    "race_condition": ("race condition", "toctou"),
    "deserialization": ("deserialization", "deserialisation", "insecure deserialization"),
    "ssti": ("ssti", "server side template injection", "template injection"),
    "request_smuggling": ("request smuggling", "http smuggling"),
    "account_takeover": ("account takeover", "ato"),
}

# Canonical platform → spoken aliases.
PLATFORM_VOCABULARY: dict[str, tuple[str, ...]] = {
    "hackerone": ("hackerone", "hacker one"),
    "bugcrowd": ("bugcrowd", "bug crowd"),
    "intigriti": ("intigriti",),
    "yeswehack": ("yeswehack", "yes we hack"),
    "hackenproof": ("hackenproof",),
    "federacy": ("federacy",),
    "freelancer": ("freelancer",),
}


def _spoken_alternation(vocabulary: dict[str, tuple[str, ...]]) -> str:
    """Regex alternation of every spoken alias, longest first."""
    aliases = [alias for values in vocabulary.values() for alias in values]
    aliases.sort(key=len, reverse=True)
    return "|".join(re.escape(alias) for alias in aliases)


def _detect(text: str, vocabulary: dict[str, tuple[str, ...]]) -> str | None:
    """Map free speech to a canonical key from ``vocabulary``."""
    lowered = text.lower()
    for canonical, aliases in vocabulary.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                return canonical
    return None


def detect_vuln_type(text: str) -> str | None:
    """Return the canonical vulnerability type spoken in ``text``, if any."""
    return _detect(text, VULN_VOCABULARY)


def detect_platform(text: str) -> str | None:
    """Return the canonical platform spoken in ``text``, if any."""
    return _detect(text, PLATFORM_VOCABULARY)


_VULN_ALTERNATION = _spoken_alternation(VULN_VOCABULARY)
_PLATFORM_ALTERNATION = _spoken_alternation(PLATFORM_VOCABULARY)

# Memory nouns as Whisper actually hears them ("engrams" often lands as "in grams").
_MEMORY_NOUNS = r"(?:engrams?|(?:in[ -]?)?grams?|memor(?:y|ies|ias)|knowledge(?:\s+entries)?|aprendizajes|hallazgos)"


def synthesize_feedback(text: str) -> bytes | None:
    """Return WAV bytes for spoken feedback, or ``None`` without local TTS."""
    try:
        from cores.voice.voice_engine import get_tts_manager

        return get_tts_manager().synthesize(text)
    except Exception as exc:  # pragma: no cover - depends on local piper install
        logger.warning("TTS feedback unavailable: %s", exc)
        return None


def _knowledge_capture():
    """Lazy accessor for the Engram knowledge store (heavy import)."""
    from cores.cycles.knowledge_capture import get_knowledge_capture

    return get_knowledge_capture()


class VoiceCommandType(StrEnum):
    """Types of voice commands."""

    ENGRAM_RECALL = "engram_recall"
    ENGRAM_LOOKUP = "engram_lookup"
    ENGRAM_CAPTURE = "engram_capture"
    ENGRAM_TAG = "engram_tag"
    ENGRAM_LIST = "engram_list"
    CLAIM_BOUNTY = "claim_bounty"
    SUBMIT_PR = "submit_pr"
    GET_BOUNTY = "get_bounty"
    START_PIPELINE = "start_pipeline"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Result of parsing a voice command."""

    command_type: VoiceCommandType
    raw_text: str
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    requires_confirmation: bool = False


@dataclass
class CommandExecutionResult:
    """Result of executing a voice command."""

    success: bool
    command_type: VoiceCommandType
    raw_text: str
    message: str
    voice_feedback: str
    data: dict[str, Any] | None = None
    error: str | None = None
    requires_confirmation: bool = False
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class VoiceCommandExecutor:
    """Executes voice commands by routing to appropriate executors."""

    # Command patterns (regex)
    _PATTERNS: dict[VoiceCommandType, list[re.Pattern[str]]] = {
        VoiceCommandType.ENGRAM_RECALL: [
            re.compile(
                r"\b(?:recall|remember)\s+(?:my\s+|your\s+|the\s+)?(?:engrams?|memor(?:y|ies)|knowledge)\b"
                r"(?:\s+(?:for|about|on|de)\s+(?P<topic>[\w./-]+))?",
                re.IGNORECASE,
            ),
            re.compile(r"\bwhat\s+do\s+i\s+know\s+about\s+(?P<topic>[\w./-]+)", re.IGNORECASE),
            re.compile(
                r"\b(?:recuerda|recordar|que\s+se\s+sobre|qué\s+sé\s+sobre)\b"
                r"(?:\s+(?:de|sobre|about)\s+(?P<topic>[\w./-]+))?",
                re.IGNORECASE,
            ),
        ],
        VoiceCommandType.ENGRAM_LOOKUP: [
            re.compile(rf"\b(?:{_VULN_ALTERNATION})\b", re.IGNORECASE),
            re.compile(rf"\b(?:{_PLATFORM_ALTERNATION})\b", re.IGNORECASE),
        ],
        VoiceCommandType.ENGRAM_CAPTURE: [
            re.compile(
                r"\bcapture\s+(?:this\s+)?(?:finding|bug|vuln(?:erability)?|issue)\b"
                r"(?:\s*(?:#|id\s*)?(?P<finding_id>\d+))?",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:captura|guardar)\s+(?:el\s+|este\s+)?(?:hallazgo|finding)\b"
                r"(?:\s*(?:#|id\s*)?(?P<finding_id>\d+))?",
                re.IGNORECASE,
            ),
        ],
        VoiceCommandType.ENGRAM_TAG: [
            re.compile(
                r"\btag\s+(?P<engram_id>[\w-]+)\s+(?:as|with)\s+(?P<tag>[\w-]+)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\betiquetar\s+(?P<engram_id>[\w-]+)\s+(?:como|con)\s+(?P<tag>[\w-]+)",
                re.IGNORECASE,
            ),
        ],
        VoiceCommandType.ENGRAM_LIST: [
            re.compile(
                rf"\b(?:list|show|mostrar)\s+(?:me\s+)?(?:(?:my|mis)\s+)*"
                rf"(?:recent\w*\s+|ultimos\s+|últimos\s+)?{_MEMORY_NOUNS}\b",
                re.IGNORECASE,
            ),
            re.compile(rf"\b(?:ultimos|últimos)\s+{_MEMORY_NOUNS}\b", re.IGNORECASE),
        ],
        VoiceCommandType.CLAIM_BOUNTY: [
            re.compile(r"claim\s+(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"reclamar\s+(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"claim\s+issue\s+([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.SUBMIT_PR: [
            re.compile(r"submit\s+(?:pr\s+)?(?:for\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"enviar\s+(?:pr\s+)?(?:para\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"submit\s+pull\s+request\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.GET_BOUNTY: [
            re.compile(r"check\s+(?:status\s+)?(?:of\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"ver\s+(?:estado\s+)?(?:del\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"status\s+(?:of\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.START_PIPELINE: [
            re.compile(r"start\s+(?:bounty\s+)?pipeline\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"iniciar\s+(?:pipeline\s+)?(?:de\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"execute\s+(?:bounty\s+)?pipeline\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
    }

    # Commands that require confirmation
    _CONFIRMATION_REQUIRED: set[VoiceCommandType] = {
        VoiceCommandType.CLAIM_BOUNTY,
        VoiceCommandType.SUBMIT_PR,
        VoiceCommandType.START_PIPELINE,
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the voice command executor."""
        self.config = config or {}
        self.executors = get_executors(self.config)
        self.feedback_loop = get_feedback_loop()
        self.bounty_pipeline: BountyPipeline | None = None
        self._command_history: list[CommandExecutionResult] = []
        self._max_history = 100

    def parse_command(self, text: str) -> ParsedCommand:
        """Parse a voice command into a structured format."""
        text = text.strip()
        if not text:
            return ParsedCommand(
                command_type=VoiceCommandType.UNKNOWN,
                raw_text=text,
                confidence=0.0,
            )

        for cmd_type, patterns in self._PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    entities: dict[str, Any] = {}
                    named = {k: v for k, v in match.groupdict().items() if v}
                    if named:
                        entities.update(named)
                    elif match.groups():
                        entities["bounty_id"] = match.group(1)
                    # Try to extract additional entities
                    entities.update(self._extract_additional_entities(text))
                    # Vocabulary enrichment shared by every command
                    vuln_type = detect_vuln_type(text)
                    if vuln_type:
                        entities.setdefault("vuln_type", vuln_type)
                    platform = detect_platform(text)
                    if platform:
                        entities.setdefault("platform", platform)

                    return ParsedCommand(
                        command_type=cmd_type,
                        raw_text=text,
                        entities=entities,
                        confidence=0.9,
                        requires_confirmation=cmd_type in self._CONFIRMATION_REQUIRED,
                    )

        return ParsedCommand(
            command_type=VoiceCommandType.UNKNOWN,
            raw_text=text,
            confidence=0.0,
        )

    def _extract_additional_entities(self, text: str) -> dict[str, Any]:
        """Extract additional entities from command text."""
        entities = {}

        # Extract repo (owner/repo format)
        repo_match = re.search(r"([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)", text)
        if repo_match:
            entities["repo"] = repo_match.group(1)

        # Extract issue number
        issue_match = re.search(r"#(\d+)", text)
        if issue_match:
            entities["issue_number"] = int(issue_match.group(1))

        return entities

    async def execute_command(
        self,
        parsed: ParsedCommand,
        confirmed: bool = False,
    ) -> CommandExecutionResult:
        """Execute a parsed voice command."""
        logger.info(
            "[VOICE-EXECUTOR] Executing command: %s (confirmed=%s)",
            parsed.command_type,
            confirmed,
        )

        # Check confirmation for critical actions
        if parsed.requires_confirmation and not confirmed:
            return CommandExecutionResult(
                success=False,
                command_type=parsed.command_type,
                raw_text=parsed.raw_text,
                message="Confirmación requerida",
                voice_feedback=self._get_confirmation_prompt(parsed),
                requires_confirmation=True,
            )

        # Route to appropriate handler
        try:
            if parsed.command_type == VoiceCommandType.CLAIM_BOUNTY:
                return await self._handle_claim_bounty(parsed)
            elif parsed.command_type == VoiceCommandType.SUBMIT_PR:
                return await self._handle_submit_pr(parsed)
            elif parsed.command_type == VoiceCommandType.GET_BOUNTY:
                return await self._handle_get_bounty(parsed)
            elif parsed.command_type == VoiceCommandType.START_PIPELINE:
                return await self._handle_start_pipeline(parsed)
            elif parsed.command_type == VoiceCommandType.ENGRAM_RECALL:
                return await self._handle_engram_recall(parsed)
            elif parsed.command_type == VoiceCommandType.ENGRAM_LOOKUP:
                return await self._handle_engram_lookup(parsed)
            elif parsed.command_type == VoiceCommandType.ENGRAM_CAPTURE:
                return await self._handle_engram_capture(parsed)
            elif parsed.command_type == VoiceCommandType.ENGRAM_TAG:
                return await self._handle_engram_tag(parsed)
            elif parsed.command_type == VoiceCommandType.ENGRAM_LIST:
                return await self._handle_engram_list(parsed)
            else:
                return CommandExecutionResult(
                    success=False,
                    command_type=parsed.command_type,
                    raw_text=parsed.raw_text,
                    message="Comando no reconocido",
                    voice_feedback="No entendí el comando. Por favor reformula.",
                    error="Unknown command type",
                )
        except Exception as e:
            logger.error("[VOICE-EXECUTOR] Error executing command: %s", e)
            return CommandExecutionResult(
                success=False,
                command_type=parsed.command_type,
                raw_text=parsed.raw_text,
                message="Error al ejecutar comando",
                voice_feedback=self._get_error_voice_feedback(str(e)),
                error=str(e),
            )

    async def _handle_claim_bounty(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle claim bounty command."""
        bounty_id = parsed.entities.get("bounty_id")
        repo = parsed.entities.get("repo")
        issue_number = parsed.entities.get("issue_number")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.CLAIM_BOUNTY,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para reclamarlo.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.CLAIM_BOUNTY,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        # Use defaults if not provided
        repo = repo or "unknown/repo"
        issue_number = issue_number or 1

        result = await executor.execute(
            "claim_issue",
            bounty_id=bounty_id,
            repo=repo,
            issue_number=issue_number,
        )

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command claim: {parsed.raw_text}",
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.CLAIM_BOUNTY,
            raw_text=parsed.raw_text,
            message=result.message or ("Bounty reclamado" if result.success else "Falló al reclamar"),
            voice_feedback="Bounty reclamado exitosamente." if result.success else f"Error: {result.error}",
            data=result.data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_submit_pr(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle submit PR command."""
        bounty_id = parsed.entities.get("bounty_id")
        pr_url = parsed.entities.get("pr_url")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty y la URL del PR.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        # Try to extract PR URL from text if not in entities
        if not pr_url:
            url_match = re.search(r"https?://[^\s]+", parsed.raw_text)
            if url_match:
                pr_url = url_match.group(0)

        if not pr_url:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="URL del PR requerida",
                voice_feedback="Necesito la URL del pull request para enviarlo.",
                error="Missing pr_url",
            )

        result = await executor.execute("submit_pr", bounty_id=bounty_id, pr_url=pr_url)

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command submit PR: {parsed.raw_text}",
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.SUBMIT_PR,
            raw_text=parsed.raw_text,
            message=result.message or ("PR enviado" if result.success else "Falló al enviar PR"),
            voice_feedback="Pull request enviado exitosamente." if result.success else f"Error: {result.error}",
            data=result.data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_get_bounty(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle get bounty status command."""
        bounty_id = parsed.entities.get("bounty_id")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.GET_BOUNTY,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para consultar su estado.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.GET_BOUNTY,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        result = await executor.execute("get_bounty", bounty_id=bounty_id)

        bounty_data = result.data if result.data else {}
        status = bounty_data.get("status", "unknown")
        reward = bounty_data.get("reward", "0")

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.GET_BOUNTY,
            raw_text=parsed.raw_text,
            message=f"Estado del bounty {bounty_id}: {status}",
            voice_feedback=f"El bounty {bounty_id} está en estado {status} con recompensa de {reward}.",
            data=bounty_data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_start_pipeline(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle start bounty pipeline command."""
        bounty_id = parsed.entities.get("bounty_id")
        repo = parsed.entities.get("repo")
        issue_number = parsed.entities.get("issue_number")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.START_PIPELINE,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para iniciar el pipeline.",
                error="Missing bounty_id",
            )

        # Get or create bounty pipeline
        if not self.bounty_pipeline:
            self.bounty_pipeline = get_bounty_pipeline()

        # Use defaults if not provided
        repo = repo or "unknown/repo"
        issue_number = issue_number or 1
        issue_url = f"https://github.com/{repo}/issues/{issue_number}"
        title = f"Issue #{issue_number}"
        description = ""

        result = await self.bounty_pipeline.execute_bounty(
            bounty_id=bounty_id,
            repo=repo,
            issue_number=issue_number,
            issue_url=issue_url,
            title=title,
            description=description,
        )

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command pipeline: {parsed.raw_text}",
                estimated_payout=result.issue_analysis.estimated_reward if result.issue_analysis else 0,
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.START_PIPELINE,
            raw_text=parsed.raw_text,
            message=result.feedback or ("Pipeline ejecutado" if result.success else "Falló el pipeline"),
            voice_feedback=(
                f"Pipeline completado exitosamente en {result.total_duration_seconds:.1f} segundos."
                if result.success
                else f"Error en el pipeline: {result.error}"
            ),
            data={
                "verdict": result.verdict,
                "total_duration_seconds": result.total_duration_seconds,
                "phases": result.phases,
            },
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    # ── Engram memory handlers (Gentle AI context accumulation) ──────────

    def _engram_result(
        self,
        parsed: ParsedCommand,
        success: bool,
        message: str,
        voice_feedback: str,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> CommandExecutionResult:
        """Build, record and return an Engram command result."""
        result = CommandExecutionResult(
            success=success,
            command_type=parsed.command_type,
            raw_text=parsed.raw_text,
            message=message,
            voice_feedback=voice_feedback,
            data=data,
            error=error,
        )
        self._add_to_history(result)
        return result

    @staticmethod
    def _entry_brief(entry: Any) -> dict[str, Any]:
        """Compact serialisable view of a KnowledgeEntry."""
        return {
            "engram_id": entry.engram_id,
            "type": str(entry.type),
            "platform": entry.platform,
            "vuln_type": entry.vuln_type,
            "lesson": entry.lesson,
            "confidence": entry.confidence,
            "tags": list(entry.tags),
            "created_at": entry.created_at,
        }

    def _summarise(self, entries: list[Any]) -> str:
        """One spoken sentence summarising recalled engrams."""
        if not entries:
            return "No tengo memorias sobre eso todavía."
        best = entries[0]
        return f"Tengo {len(entries)} memorias. La más relevante: {best.lesson[:160]}"

    async def _handle_engram_recall(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Recall engrams by platform, vuln type or free-text topic."""
        topic = parsed.entities.get("topic")
        platform = parsed.entities.get("platform")
        vuln_type = parsed.entities.get("vuln_type")
        kc = _knowledge_capture()

        if topic and not vuln_type:
            vuln_type = detect_vuln_type(topic)
        if topic and not platform:
            platform = detect_platform(topic)

        entries = kc.recall_engrams(platform=platform, vuln_type=vuln_type, limit=5)
        if topic:
            needle = topic.lower()
            filtered = [e for e in entries if needle in (e.lesson or "").lower() or any(needle in tag.lower() for tag in e.tags)]
            if filtered:
                entries = filtered

        data = {
            "filters": {"topic": topic, "platform": platform, "vuln_type": vuln_type},
            "entries": [self._entry_brief(e) for e in entries],
        }
        return self._engram_result(
            parsed,
            success=bool(entries),
            message=f"{len(entries)} memorias recuperadas",
            voice_feedback=self._summarise(entries),
            data=data,
            error=None if entries else "no matching engrams",
        )

    async def _handle_engram_lookup(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Look up captured learnings by platform or vulnerability type."""
        kc = _knowledge_capture()
        vuln_type = parsed.entities.get("vuln_type")
        platform = parsed.entities.get("platform")

        entries = kc.get_entries_by_vuln_type(vuln_type) if vuln_type else kc.get_entries_by_platform(platform or "")
        label = vuln_type or platform or "?"
        return self._engram_result(
            parsed,
            success=bool(entries),
            message=f"{len(entries)} entradas para {label}",
            voice_feedback=(
                f"Tengo {len(entries)} aprendizajes sobre {label}. {entries[0].lesson[:120]}" if entries else f"Todavía no tengo aprendizajes sobre {label}."
            ),
            data={"label": label, "entries": [self._entry_brief(e) for e in entries[:5]]},
            error=None if entries else f"no entries for {label}",
        )

    def _load_finding(self, finding_id: int | None) -> tuple[Any | None, str | None]:
        """Load a Finding by id. Returns (finding, error)."""
        if finding_id is None:
            return None, "missing finding_id"
        from database import db
        from database.models import Finding

        session = db.SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == finding_id).first()
            if finding is None:
                return None, f"finding {finding_id} not found"
            return finding, None
        finally:
            session.close()

    async def _handle_engram_capture(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Capture learning from a confirmed finding into long-term memory."""
        raw_id = parsed.entities.get("finding_id")
        finding_id = int(raw_id) if raw_id else None
        finding, error = self._load_finding(finding_id)
        if finding is None or error:
            return self._engram_result(
                parsed,
                success=False,
                message="Hallazgo no disponible",
                voice_feedback=(f"No encontré el hallazgo {finding_id}." if finding_id else "Necesito el número del hallazgo para capturarlo."),
                error=error,
            )

        entry = _knowledge_capture().capture_from_finding(finding)
        if entry is None:
            return self._engram_result(
                parsed,
                success=False,
                message="Sin veredicto confirmado",
                voice_feedback=f"El hallazgo {finding_id} no tiene veredicto confirmado todavía.",
                error="no confirmed verdict",
            )
        return self._engram_result(
            parsed,
            success=True,
            message=f"Memoria creada: {entry.engram_id}",
            voice_feedback="Memoria guardada.",
            data=self._entry_brief(entry),
        )

    async def _handle_engram_tag(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Tag an engram for later discovery."""
        engram_id = parsed.entities.get("engram_id", "")
        tag = parsed.entities.get("tag", "")
        if not engram_id or not tag:
            return self._engram_result(
                parsed,
                success=False,
                message="Falta el identificador o la etiqueta",
                voice_feedback="Necesito la memoria y la etiqueta.",
                error="missing engram_id or tag",
            )
        tagged = _knowledge_capture().tag_engram(engram_id, tag)
        return self._engram_result(
            parsed,
            success=tagged,
            message=f"Etiqueta '{tag}' aplicada a {engram_id}" if tagged else f"Memoria {engram_id} no encontrada",
            voice_feedback=f"Etiqueta {tag} aplicada." if tagged else f"No encontré la memoria {engram_id}.",
            data={"engram_id": engram_id, "tag": tag},
            error=None if tagged else "engram not found",
        )

    async def _handle_engram_list(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """List the most recent memories."""
        entries = _knowledge_capture().get_recent(limit=5)
        return self._engram_result(
            parsed,
            success=bool(entries),
            message=f"{len(entries)} memorias recientes",
            voice_feedback=(f"Mis {len(entries)} memorias más recientes: {entries[0].lesson[:120]}" if entries else "Todavía no tengo memorias guardadas."),
            data={"entries": [self._entry_brief(e) for e in entries]},
            error=None if entries else "no entries",
        )

    def _get_confirmation_prompt(self, parsed: ParsedCommand) -> str:
        """Get voice confirmation prompt for a command."""
        prompts = {
            VoiceCommandType.CLAIM_BOUNTY: f"¿Confirmar que quieres reclamar el bounty {parsed.entities.get('bounty_id', '?')}?",
            VoiceCommandType.SUBMIT_PR: f"¿Confirmar que quieres enviar el PR para el bounty {parsed.entities.get('bounty_id', '?')}?",
            VoiceCommandType.START_PIPELINE: f"¿Confirmar que quieres iniciar el pipeline para el bounty {parsed.entities.get('bounty_id', '?')}?",
        }
        return prompts.get(parsed.command_type, "¿Confirmar esta acción?")

    def _get_error_voice_feedback(self, error: str) -> str:
        """Get user-friendly voice feedback for errors."""
        error_lower = error.lower()

        if "token" in error_lower or "auth" in error_lower:
            return "Error de autenticación. Verifica tus credenciales."
        elif "not found" in error_lower or "404" in error_lower:
            return "No encontré el recurso solicitado."
        elif "timeout" in error_lower:
            return "La operación tardó demasiado. Intenta nuevamente."
        elif "permission" in error_lower or "403" in error_lower:
            return "No tienes permiso para realizar esta acción."
        else:
            return "Ocurrió un error. Por favor intenta nuevamente."

    def _add_to_history(self, result: CommandExecutionResult) -> None:
        """Add command execution result to history."""
        self._command_history.append(result)
        if len(self._command_history) > self._max_history:
            self._command_history.pop(0)

        logger.info(
            "[VOICE-EXECUTOR] Command executed: %s, success=%s",
            result.command_type,
            result.success,
        )

    def get_command_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get command execution history."""
        return [asdict(r) for r in self._command_history[-limit:]]

    def get_available_commands(self) -> list[dict[str, Any]]:
        """Get list of available voice commands."""
        return [
            {
                "command_type": cmd_type.value,
                "patterns": [p.pattern for p in patterns],
                "requires_confirmation": cmd_type in self._CONFIRMATION_REQUIRED,
                "description": self._get_command_description(cmd_type),
            }
            for cmd_type, patterns in self._PATTERNS.items()
        ]

    def _get_command_description(self, cmd_type: VoiceCommandType) -> str:
        """Get description for a command type."""
        descriptions = {
            VoiceCommandType.ENGRAM_RECALL: "Recuperar aprendizajes por plataforma, tipo de vuln o tema",
            VoiceCommandType.ENGRAM_LOOKUP: "Buscar aprendizajes por plataforma o tipo de vulnerabilidad",
            VoiceCommandType.ENGRAM_CAPTURE: "Capturar aprendizaje de un hallazgo confirmado",
            VoiceCommandType.ENGRAM_TAG: "Etiquetar una memoria para encontrarla después",
            VoiceCommandType.ENGRAM_LIST: "Listar las memorias más recientes",
            VoiceCommandType.CLAIM_BOUNTY: "Reclamar un bounty de Algora",
            VoiceCommandType.SUBMIT_PR: "Enviar un pull request para un bounty",
            VoiceCommandType.GET_BOUNTY: "Consultar el estado de un bounty",
            VoiceCommandType.START_PIPELINE: "Iniciar el pipeline completo de bounty",
        }
        return descriptions.get(cmd_type, "Comando desconocido")


# Singleton instance
_global_executor: VoiceCommandExecutor | None = None


def get_voice_command_executor(config: dict[str, Any] | None = None) -> VoiceCommandExecutor:
    """Get singleton instance of voice command executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = VoiceCommandExecutor(config)
        logger.info("VoiceCommandExecutor initialized")
    return _global_executor


def reset_voice_command_executor() -> None:
    """Reset singleton instance."""
    global _global_executor
    _global_executor = None
