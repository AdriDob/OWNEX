#!/usr/bin/env python3
"""
Mission Inbox System - Enhanced Notification Interface for CATEYE

This module implements the complete Mission Inbox system as specified in the workflow:
- Centralized notification hub for all mission-related events
- AI Copilot for automated response generation
- Timeline-based UI with advanced filtering and management
- Platform integration with conversation support
- Comprehensive filtering and search capabilities
- Mobile-ready responsive design
- High-priority temporal focus (Today, Yesterday, This Week, This Month)
- Quick actions and automation with human oversight
- SOC-like interface for professional bug bounty operations
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    from cores.ai.orion_agent import get_orion_agent  # type: ignore[attr-defined]
except ImportError:
    get_orion_agent = None
from cores.events.event_bus import get_event_bus
from cores.notifications.hub import get_hub

logger = logging.getLogger("cateye.mission_inbox")


class TimelineScope(Enum):
    """Timeline filtering scopes for Mission Inbox"""

    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    ALL = "all"


class EventPriority(Enum):
    """Priority levels for notifications in Mission Inbox"""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    ARCHIVE = "archive"


class ConversationType(Enum):
    """Types of conversations in Mission Inbox"""

    HUNTER = "hunter"
    PLATFORM = "platform"
    STAFF = "staff"
    RESEARCHER = "researcher"
    MANAGER = "manager"
    SYSTEM = "system"


class EvidenceType(Enum):
    """Types of evidence that can be generated or requested"""

    SCREENSHOT = "screenshot"
    VIDEO = "video"
    LOG = "log"
    CONFIG = "config"
    REQUEST = "request"
    RESPONSE = "response"
    TIMELINE = "timeline"
    PAYMENT = "payment"
    EVIDENCE = "evidence"
    ADDITIONAL = "additional"
    PLAYWRIGHT = "playwright"
    FFUF = "ffuf"
    NAKED_REDIRECT = "naked_redirect"
    XSS = "xss"
    SQLI = "sqli"
    IDOR = "idor"
    LFI = "lfi"
    S3 = "s3"
    RCE = "rce"


@dataclass
class EvidenceItem:
    """Digital evidence item for missions"""

    id: str
    type: EvidenceType
    title: str
    description: str
    matches: list[str] = field(default_factory=list)
    filepath: str | None = None
    preview_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    uploaded_by: str | None = None
    uploaded_at: float | None = None
    ai_generated: bool = False
    human_reviewed: bool = False
    review_comments: str | None = None
    priority: str = "normal"
    completeness_score: float | None = None
    quality_score: float | None = None


@dataclass
class EventConversation:
    """Conversation thread for mission events"""

    id: str
    report_id: str | None = None
    type: ConversationType = ConversationType.PLATFORM
    participants: list[str] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    unread_count: int = 0
    archived: bool = False
    starred: bool = False
    tags: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "active"
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None


@dataclass
class MissionEvent:
    """Mission event structure for Mission Inbox"""

    id: str
    type: str
    priority: EventPriority
    title: str
    message: str
    timestamp: float
    platforms: list[str]
    targets: list[str]
    hunters: list[str]
    report_id: str | None = None
    evidence_requests: list[str] = field(default_factory=list)
    evidence_generated: list[str] = field(default_factory=list)
    ai_suggestions: list[dict[str, Any]] = field(default_factory=list)
    manual_guidance: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    related_events: list[str] = field(default_factory=list)
    status: str = "active"
    channel: str = "web"
    ui_hints: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None


class AiGuidanceGenerator:
    """
    AI Copilot for generating automated guidance and evidence suggestions.

    Features:
    - Analyzes conversation context
    - Generates evidence suggestions
    - Creates automated responses (with approval requirement)
    - Provides technical explanations
    - Suggests next steps
    """

    def __init__(self, agent_id: str = "mission_inbox_ai"):
        self.agent_id = agent_id
        self.logger = logging.getLogger("cateye.ai_guidance")
        self.cohere_agent = None
        self.context_cache: dict[str, Any] = {}
        self.evidence_templates: dict[EvidenceType, dict[str, Any]] = self._load_evidence_templates()

    def _load_evidence_templates(self) -> dict[EvidenceType, dict[str, Any]]:
        """Load evidence generation templates"""
        return {
            EvidenceType.SCREENSHOT: {
                "title": "{report_title} - Evidence: {finding_type}",
                "description": "Captured evidence showing {finding_description} from {target}",
                "generation_prompt": "Generate a comprehensive screenshot showing {finding_type} vulnerability evidence from {target}. Include relevant details like URL, parameters, and exploitation demonstration.",
                "file_types": [".png", ".jpg", ".jpeg", ".webp"],
                "tools": ["playwright", "selenium", "curl", "ffuf"],
                "quality_check": "evidence_completeness",
            },
            EvidenceType.VIDEO: {
                "title": "{report_title} - Tutorial Video",
                "description": "Demonstrating {finding_type} exploitation steps",
                "generation_prompt": "Create a step-by-step video demonstrating the {finding_type} vulnerability exploitation process, including setup, payload, and impact.",
                "tools": ["playwright", "obs", "ffmpeg"],
                "duration_limit": 300,  # 5 minutes
                "quality_check": "evidence_quality",
            },
            EvidenceType.LOG: {
                "title": "{report_title} - Logs",
                "description": "Network activity logs showing exploitation attempt",
                "generation_prompt": "Capture and format network logs showing the {finding_type} exploitation attempt, including requests and responses.",
                "file_types": [".log", ".txt", ".json"],
                "tools": ["httpx", "tcpdump", "wireshark"],
                "quality_check": "log_completeness",
            },
            EvidenceType.REQUEST: {
                "title": "{report_title} - HTTP Requests",
                "description": "Complete HTTP request/response sequence for {finding_type}",
                "generation_prompt": "Capture the full HTTP request/response sequence for the {finding_type} vulnerability exploitation, including all headers and bodies.",
                "tools": ["burpsuite", "zaproxy", "curl"],
                "quality_check": "request_completeness",
            },
            EvidenceType.RESPONSE: {
                "title": "{report_title} - HTTP Responses",
                "description": "Server responses demonstrating {finding_type} impact",
                "generation_prompt": "Capture server responses that confirm the {finding_type} vulnerability impact.",
                "tools": ["burpsuite", "zaproxy"],
                "quality_check": "response_analysis",
            },
            EvidenceType.TIMELINE: {
                "title": "{report_title} - Activity Timeline",
                "description": "Chronological timeline of {finding_type} investigation",
                "generation_prompt": "Create a comprehensive timeline of all activities, discoveries, and actions during the {finding_type} investigation.",
                "tools": ["timeline_builder", "log_parser"],
                "quality_check": "timeline_completeness",
            },
            EvidenceType.PLAYWRIGHT: {
                "title": "{report_title} - Scripted Evidence",
                "description": "Automated browser script generating {finding_type} evidence",
                "generation_prompt": "Create a script that automatically demonstrates the {finding_type} vulnerability in a controlled environment.",
                "tools": ["playwright", "selenium"],
                "quality_check": "script_reliability",
            },
        }

    async def analyze_conversation(
        self, conversation: EventConversation, event: MissionEvent, hunter_profile: dict
    ) -> dict[str, Any]:
        """
        Analyze conversation to determine what's needed and suggest next steps.

        Returns:
            Analysis containing needed evidence, suggestions, and guidance
        """
        analysis = {
            "needed_evidence": [],
            "suggested_actions": [],
            "ai_suggestions": [],
            "completeness_score": 0.0,
            "quality_score": 0.0,
            "missing_info": [],
            "risk_level": "low",
            "next_steps": [],
        }

        try:
            # Check if Cohere agent is available
            agent = get_orion_agent() if get_orion_agent else None
            if agent and hasattr(agent, "chat"):
                prompt = self._build_conversation_analysis_prompt(conversation, event, hunter_profile)
                response = await agent.chat(prompt)

                if response and hasattr(response, "message"):
                    analysis.update(self._parse_ai_response(response.message))
            else:
                # Fallback to basic analysis
                analysis = self._basic_conversation_analysis(conversation, event, hunter_profile)

            # Calculate completeness and quality scores
            analysis["completeness_score"] = self._calculate_completeness_score(analysis)
            analysis["quality_score"] = self._calculate_quality_score(analysis)

            # Determine risk level
            analysis["risk_level"] = self._determine_risk_level(analysis)

            # Generate prioritized next steps
            analysis["next_steps"] = self._generate_next_steps(analysis)

        except Exception as e:
            self.logger.error(f"Error analyzing conversation: {e}")
            # Fallback to basic analysis
            analysis = self._basic_conversation_analysis(conversation, event, hunter_profile)

        return analysis

    def _build_conversation_analysis_prompt(
        self, conversation: EventConversation, event: MissionEvent, hunter_profile: dict
    ) -> str:
        """Build a comprehensive prompt for conversation analysis"""
        latest_message = (
            conversation.messages[-1]
            if conversation.messages
            else {"content": "", "timestamp": conversation.created_at}
        )
        latest_ts = float(latest_message.get("timestamp", conversation.created_at))  # type: ignore[arg-type]

        prompt = f"""
        Analiza la siguiente conversación y evento del hunter para entender qué evidencia o información adicional se necesita para responder a su solicitud.

        INFORMACIÓN DE CONVERSACIÓN:
        - Tipo de conversación: {conversation.type}
        - Participantes: {", ".join(conversation.participants)}
        - Último mensaje: "{latest_message.get("content", "")}" (a las {datetime.fromtimestamp(latest_ts).isoformat()})
        - Estado: {conversation.status}
        - Evidencias adjuntas: {len(conversation.evidence_ids)}

        INFORMACIÓN DEL EVENTO:
        - Tipo: {event.type}
        - Título: {event.title}
        - Mensaje: {event.message}
        - Prioridad: {event.priority}
        - Platform: {event.platforms[0] if event.platforms else "Unknown"}
        - Target(s): {", ".join(event.targets)}
        - Hunter: {", ".join(event.hunters)}
        - Report ID: {event.report_id or "N/A"}

        PERFIL DEL HUNTER:
        - Experiencia: {hunter_profile.get("experience", "N/A")}
        - Rol: {hunter_profile.get("role", "N/A")}
        - Tiempo en plataforma: {hunter_profile.get("platform_time", "N/A")}
        - Historial: {", ".join(hunter_profile.get("previous_reports", []))}

        TAREAS PENDIENTES IDENTIFICADAS:
        Analiza la conversación para identificar qué información o evidencia específica se necesita para responder completamente a la solicitud del triager.

        DEBE incluir:
        1. Tipos específicos de evidencia faltante
        2. Pasos técnicos necesarios
        3. Información específica que falta
        4. Evaluación de riesgo del reporte
        5. Próximos pasos recomendados

        RESUMEN DE LA EVIDENCIA REQUERIDA:
        """
        return prompt

    def _parse_ai_response(self, response: str) -> dict[str, Any]:
        """Parse AI response into structured analysis"""
        try:
            # Try to parse as JSON (if AI returns structured data)
            if response.strip().startswith("{"):
                return json.loads(response)

            # Otherwise, parse as structured text
            analysis = self._basic_conversation_analysis(None, None, {})

            # Extract key information from text response
            import re

            # Find evidence types mentioned
            evidence_patterns = {
                "screenshot": EvidenceType.SCREENSHOT,
                "screen shot": EvidenceType.SCREENSHOT,
                "captura de pantalla": EvidenceType.SCREENSHOT,
                "video": EvidenceType.VIDEO,
                "vídeo": EvidenceType.VIDEO,
                "log": EvidenceType.LOG,
                "logs": EvidenceType.LOG,
                "http request": EvidenceType.REQUEST,
                "http response": EvidenceType.RESPONSE,
                "request": EvidenceType.REQUEST,
                "response": EvidenceType.RESPONSE,
                "timeline": EvidenceType.TIMELINE,
                "playback": EvidenceType.PLAYWRIGHT,
                "playwright": EvidenceType.PLAYWRIGHT,
                "script": EvidenceType.PLAYWRIGHT,
            }

            for pattern, evidence_type in evidence_patterns.items():
                if re.search(pattern, response, re.IGNORECASE) and evidence_type not in analysis["needed_evidence"]:
                    analysis["needed_evidence"].append(evidence_type)

            # Check for action items
            action_indicators = {
                "step": True,
                "passo": True,
                "tutorial": True,
                "guía": True,
                "instrucciones": True,
                "cómo": True,
                "ejemplo": True,
                "ejemplo de": True,
                "análisis": True,
                "explicación": True,
                "detalle": True,
            }

            for indicator, _value in action_indicators.items():
                if indicator in response.lower():
                    analysis["suggested_actions"].append(indicator)

            # Extract quality indicators
            quality_patterns = [
                (r"completitud\s*(\d+)%", "completeness"),
                (r"calidad\s*(\d+)%", "quality"),
                (r"(\d+)%\s*completo", "completeness"),
                (r"(\d+)%\s*calidad", "quality"),
            ]

            for pattern, key in quality_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    analysis[key] = int(match.group(1)) / 100.0

        except Exception as e:
            self.logger.warning(f"Error parsing AI response: {e}")

        return analysis

    async def generate_evidence(
        self, report_id: str, evidence_request: EvidenceType, event_context: dict[str, Any]
    ) -> EvidenceItem | None:
        """
        Generate specific evidence for a request.

        Note: This is a template implementation. Actual evidence generation
        would require specific tools and access to the target systems.
        """
        try:
            template = self.evidence_templates.get(evidence_request)
            if not template:
                self.logger.error(f"No template found for evidence type: {evidence_request}")
                return None

            evidence_id = f"{evidence_request.value}_{report_id}_{int(time.time())}"

            self.logger.info(f"Generating evidence type {evidence_request.value} for report {report_id}")

            # In a real implementation, this would:
            # 1. Extract target information from event_context
            # 2. Use appropriate tools (playwright, burpsuite, etc.)
            # 3. Capture the evidence
            # 4. Process and validate the evidence
            # 5. Store the evidence

            # For now, return a placeholder evidence item
            evidence = EvidenceItem(
                id=evidence_id,
                type=evidence_request,
                title=template["title"].format(
                    report_title=event_context.get("report_title", "Unknown Report"),
                    finding_type=event_context.get("finding_type", "Unknown"),
                ),
                description=template["description"].format(
                    finding_type=event_context.get("finding_type", "Unknown"),
                    target=event_context.get("target", "Unknown"),
                ),
                ai_generated=True,
                human_reviewed=False,
                metadata={
                    "template": template,
                    "generation_time": time.time(),
                    "event_context": event_context,
                    "tools_used": template.get("tools", []),
                    "quality_check": template.get("quality_check", "none"),
                },
            )

            self.logger.info(f"Generated evidence placeholder: {evidence_id}")
            return evidence

        except Exception as e:
            self.logger.error(f"Error generating evidence: {e}")
            return None

    def _basic_conversation_analysis(
        self, conversation: EventConversation | None, event: MissionEvent | None, hunter_profile: dict
    ) -> dict[str, Any]:
        """Basic analysis without AI when needed"""
        analysis: dict[str, Any] = {
            "needed_evidence": [],
            "suggested_actions": [],
            "ai_suggestions": [],
            "completeness_score": 0.0,
            "quality_score": 0.0,
            "missing_info": [],
            "risk_level": "low",
            "next_steps": [],
        }

        if event:
            # Basic analysis based on event type and title
            if "request" in event.title.lower() or "need" in event.message.lower():
                # Extract evidence types from message
                message_lower = event.message.lower()
                if "screenshot" in message_lower or "screen" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.SCREENSHOT)
                if "video" in message_lower or "grabación" in message_lower or "tutorial" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.VIDEO)
                if "log" in message_lower or "registro" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.LOG)
                if "request" in message_lower or "response" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.REQUEST)
                if "timeline" in message_lower or "cronograma" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.TIMELINE)
                if "playwright" in message_lower or "script" in message_lower:
                    analysis["needed_evidence"].append(EvidenceType.PLAYWRIGHT)

            # Generate suggested actions based on missing evidence
            analysis["suggested_actions"] = [
                "Generate evidence automatically using appropriate tools",
                "Create human approval workflow for evidence review",
                "Notify hunter of progress",
                "Archive conversation for future reference",
            ]

            # Basic AI suggestions
            analysis["ai_suggestions"] = [
                "Generate comprehensive screenshots documenting the vulnerability",
                "Create a step-by-step tutorial video demonstrating the exploit",
                "Provide detailed logs of the exploitation attempt",
                "Include request/response history for technical analysis",
            ]

        return analysis

    def _calculate_completeness_score(self, analysis: dict[str, Any]) -> float:
        """Calculate how complete the evidence analysis is"""
        base_score = 0.0

        needed_count = len(analysis.get("needed_evidence", []))
        base_score += needed_count * 25

        suggested_count = len(analysis.get("suggested_actions", []))
        base_score += suggested_count * 5

        if analysis.get("missing_info"):
            base_score -= len(analysis["missing_info"]) * 10

        return max(0.0, min(100.0, base_score))

    def _calculate_quality_score(self, analysis: dict[str, Any]) -> float:
        """Calculate the quality score of the analysis"""
        score = 50.0

        if analysis.get("ai_suggestions"):
            score += 25.0

        if analysis.get("risk_level") == "critical":
            score += 20.0
        elif analysis.get("risk_level") == "high":
            score += 15.0
        elif analysis.get("risk_level") == "medium":
            score += 10.0

        completeness = analysis.get("completeness_score", 0.0)
        score = score + (completeness * 0.25)

        return min(100.0, score)

    def _determine_risk_level(self, analysis: dict[str, Any]) -> str:
        """Determine the risk level based on analysis"""
        missing_critical_info = len(analysis.get("missing_info", []))

        if missing_critical_info >= 3:
            return "critical"
        elif missing_critical_info >= 2:
            return "high"
        elif missing_critical_info >= 1 or analysis.get("completeness_score", 0.0) < 50:
            return "medium"
        else:
            return "low"

    def _generate_next_steps(self, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate prioritized next steps"""
        next_steps = []

        # Generate evidence steps based on needed evidence
        for evidence_type in analysis.get("needed_evidence", []):
            next_steps.append(
                {
                    "step": "generate_evidence",
                    "type": evidence_type,
                    "priority": "high",
                    "description": f"Generate {evidence_type.value} evidence to answer user request",
                    "estimated_time": self._estimate_evidence_generation_time(evidence_type),
                    "requires_human_approval": True,
                    "ai_suggested": True,
                }
            )

        # Add documentation steps
        for action in analysis.get("suggested_actions", []):
            next_steps.append(
                {
                    "step": action,
                    "type": "documentation",
                    "priority": "medium",
                    "description": f"Complete documentation: {action}",
                    "estimated_time": "30 minutes",
                    "requires_human_approval": False,
                    "ai_suggested": True,
                }
            )

        # Add notification steps
        next_steps.append(
            {
                "step": "notify_hunter",
                "type": "communication",
                "priority": "medium",
                "description": "Notify hunter of progress and next steps",
                "estimated_time": "5 minutes",
                "requires_human_approval": False,
                "ai_suggested": True,
            }
        )

        return next_steps

    def _estimate_evidence_generation_time(self, evidence_type: EvidenceType) -> str:
        """Estimate time required to generate specific evidence type"""
        time_estimates = {
            EvidenceType.SCREENSHOT: "5-10 minutes",
            EvidenceType.VIDEO: "15-30 minutes",
            EvidenceType.LOG: "10-15 minutes",
            EvidenceType.REQUEST: "5-10 minutes",
            EvidenceType.RESPONSE: "5-10 minutes",
            EvidenceType.TIMELINE: "20-30 minutes",
            EvidenceType.PLAYWRIGHT: "30-45 minutes",
        }
        return time_estimates.get(evidence_type, "15-30 minutes")

    def add_conversation_response(self, conversation: EventConversation, response_data: dict[str, Any]) -> None:
        """
        Add a response to a conversation thread.

        Args:
            conversation: The conversation to respond to
            response_data: Response data containing the message
        """
        message = {
            "id": f"msg_{int(time.time())}_{len(conversation.messages)}",
            "sender": response_data.get("sender", "ai_assistant"),
            "content": response_data.get("content", ""),
            "timestamp": time.time(),
            "type": response_data.get("type", "text"),
            "attachments": response_data.get("attachments", []),
            "metadata": response_data.get("metadata", {}),
        }

        conversation.messages.append(message)
        conversation.last_activity = time.time()

        if "ai" in response_data.get("sender", ""):
            conversation.unread_count += 1

    async def generate_ai_guidance_response(
        self, conversation: EventConversation, event: MissionEvent, hunter_profile: dict
    ) -> dict[str, Any]:
        """
        Generate AI response for a conversation based on analysis.

        Returns:
            Response data for the conversation
        """
        try:
            analysis = await self.analyze_conversation(conversation, event, hunter_profile)

            # Create structured response
            response = {
                "sender": "ai_assistant",
                "type": "structured_guidance",
                "timestamp": time.time(),
                "content": self._format_guidance_response(analysis, conversation, event),
                "metadata": {
                    "confidence": analysis.get("quality_score", 0.0) / 100.0,
                    "analysis": analysis,
                    "needs_human_approval": analysis.get("risk_level") in ["critical", "high"],
                    "next_steps": analysis.get("next_steps", []),
                    "evidence_needed": analysis.get("needed_evidence", []),
                },
            }

            return response

        except Exception as e:
            self.logger.error(f"Error generating AI guidance response: {e}")
            return {
                "sender": "ai_assistant",
                "type": "error",
                "timestamp": time.time(),
                "content": "Lo siento, tuve un problema al analizar tu solicitud. Por favor, intenta nuevamente o contacta soporte si el problema persiste.",
            }

    def _format_guidance_response(
        self, analysis: dict[str, Any], conversation: EventConversation, event: MissionEvent
    ) -> str:
        """Format AI response in human-readable format"""
        guidance_parts = []

        if analysis.get("completeness_score", 0.0) < 50:
            guidance_parts.append(
                "📊 **Análisis de Completitud**: Tu solicitud necesita más evidencia para estar completamente documentada."
            )

        if analysis.get("risk_level") == "critical":
            guidance_parts.append(
                "⚠️ **Nivel de Riesgo Crítico**: Esta solicitud presenta alto riesgo de no ser aprobada por los triagers sin evidencia completa."
            )

        evidence_needs = analysis.get("needed_evidence", [])
        if evidence_needs:
            guidance_parts.append(f"\n🎯 **Evidencia Requerida**:\n   • {', '.join([e.value for e in evidence_needs])}")

        ai_suggestions = analysis.get("ai_suggestions", [])
        if ai_suggestions:
            guidance_parts.append("\n🤖 **Sugerencias de IA**:\n")
            for i, suggestion in enumerate(ai_suggestions[:3], 1):
                guidance_parts.append(f"   {i}. {suggestion}")

        next_steps = analysis.get("next_steps", [])
        if next_steps:
            guidance_parts.append("\n📋 **Próximos Pasos Recomendados**:\n")
            for i, step in enumerate(next_steps[:3], 1):
                priority = step.get("priority", "medium").upper()
                action = step.get("description", "")
                guidance_parts.append(f"   {i}. **{priority}** {action}")

        return "\n".join(guidance_parts)


class MissionInbox:
    """
    Central Mission Inbox for all bug bounty operations.

    Provides a unified interface for:
    - Timeline-based event management
    - AI Copilot integration for automated responses
    - Platform conversation management
    - Evidence generation and tracking
    - Prioritized filtering and search
    - Multi-channel notification routing
    """

    def __init__(self, config_file: str | None = None):
        self.logger = logging.getLogger("cateye.mission_inbox")
        self.ai_guidance = AiGuidanceGenerator()

        # Initialize notification hub
        self.notification_hub = get_hub()

        # Inbox state
        self.events: dict[str, MissionEvent] = {}
        self.conversations: dict[str, EventConversation] = {}
        self.evidences: dict[str, EvidenceItem] = {}
        self.timeline: list[MissionEvent] = []
        self.event_bus = get_event_bus()

        # Configuration
        self.config = self._load_config(config_file) if config_file else self._get_default_config()

        # Setup event listeners
        self._setup_event_listeners()

        # UI components (simulated)
        self.ui_components = self._initialize_ui_components()

    def _load_config(self, config_file: str) -> dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration"""
        return {
            "name": "Mission Inbox",
            "max_history": 1000,
            "auto_generate_evidence": False,
            "require_human_approval": True,
            "ai_model": "gemini",
            "notification_channels": ["web", "desktop"],
            "timeline_scope": TimelineScope.THIS_WEEK,
            "filters": {
                "priorities": ["high", "critical"],
                "event_types": [],
                "platforms": [],
                "hunters": [],
                "date_range": {"start": None, "end": None},
            },
            "ui": {"theme": "auto", "refresh_interval": 30, "webhooks": True},
            "ai_guidance": {
                "enabled": True,
                "auto_generate": False,
                "approval_required": True,
                "confidence_threshold": 0.8,
            },
        }

    def _initialize_ui_components(self) -> dict[str, Any]:
        """Initialize UI components for the Mission Inbox"""
        return {
            "timeline_component": self._create_timeline_component(),
            "conversation_component": self._create_conversation_component(),
            "evidence_panel": self._create_evidence_panel(),
            "filter_panel": self._create_filter_panel(),
            "ai_guidance_panel": self._create_ai_guidance_panel(),
            "navigation_panel": self._create_navigation_panel(),
        }

    def _create_timeline_component(self) -> dict[str, Any]:
        """Create timeline UI component"""
        return {
            "type": "timeline",
            "props": {"scope": TimelineScope.THIS_WEEK, "priorities": ["high", "critical"], "filters": []},
            "state": {"events": [], "selections": [], "zoom_level": 1, "view_mode": "chronological"},
        }

    def _create_conversation_component(self) -> dict[str, Any]:
        """Create conversation UI component"""
        return {
            "type": "conversation",
            "props": {
                "selected_conversation": None,
                "show_threads": True,
                "show_replies": True,
                "auto_scroll": True,
                "typing_indicator": True,
            },
            "state": {"messages": [], "participants": [], "attachments": [], "reactions": {}},
        }

    def _create_evidence_panel(self) -> dict[str, Any]:
        """Create evidence panel UI component"""
        return {
            "type": "evidence_panel",
            "props": {
                "selected_evidence": None,
                "filter_by_type": [],
                "quality_threshold": 0.5,
                "ai_generated_only": False,
            },
            "state": {"evidence_list": [], "quality_scores": {}, "preview_urls": {}, "download_status": {}},
        }

    def _create_filter_panel(self) -> dict[str, Any]:
        """Create filter UI component"""
        return {
            "type": "filter_panel",
            "props": {
                "timeline_scope": TimelineScope.THIS_WEEK,
                "available_priorities": ["high", "critical", "medium", "low"],
                "available_platforms": [],
                "available_event_types": [],
                "search_placeholder": "Search events, conversations, evidence...",
            },
            "state": {"active_filters": {}, "search_query": "", "show_advanced": False},
        }

    def _create_ai_guidance_panel(self) -> dict[str, Any]:
        """Create AI guidance panel UI component"""
        return {
            "type": "ai_guidance_panel",
            "props": {
                "auto_expand_confidence": True,
                "show_human_approval_requests": True,
                "evidence_generation_enabled": False,
                "preview_ai_suggestions": True,
            },
            "state": {"current_guidance": {}, "approval_requests": [], "ai_suggestions": [], "confidence_scores": {}},
        }

    def _create_navigation_panel(self) -> dict[str, Any]:
        """Create navigation panel UI component"""
        return {
            "type": "navigation_panel",
            "props": {
                "show_today": True,
                "show_yesterday": True,
                "show_this_week": True,
                "show_this_month": False,
                "show_archive": True,
                "quick_filters": [
                    {"label": "All Critical", "filter": {"priority": "critical"}},
                    {"label": "Platform Conversations", "filter": {"type": "platform"}},
                    {"label": "Need Evidence", "filter": {"missing_evidence": True}},
                ],
                "starred_only": False,
                "archived_only": False,
            },
            "state": {
                "current_view": TimelineScope.THIS_WEEK,
                "selected_tags": [],
                "starred_events": [],
                "archived_events": [],
            },
        }

    def _setup_event_listeners(self) -> None:
        """Setup event listeners for the Mission Inbox"""
        self.event_bus.subscribe("*", self._handle_event)
        self.event_bus.subscribe_async("mission:ai_guidance_requested", self._handle_ai_guidance_request)

    async def process_incoming_events(self) -> None:
        """
        Process incoming events from the event bus.

        This is called periodically to sync new events into the Mission Inbox.
        """
        try:
            # Get recent events from event bus
            recent_events = self.event_bus.get_history(limit=100)

            for event_data in recent_events:
                event_type = event_data.get("type", "")
                if not event_type.startswith("platform:") and not event_type.startswith("hunt:"):
                    continue

                # Check if event already exists
                if event_data.get("id") not in self.events:
                    mission_event = MissionEvent(
                        id=event_data.get("id", f"event_{int(time.time())}"),
                        type=event_data.get("type", ""),
                        priority=EventPriority(event_data.get("priority", "medium").lower()),
                        title=event_data.get("title", ""),
                        message=event_data.get("message", ""),
                        timestamp=event_data.get("timestamp", time.time()),
                        platforms=event_data.get("platforms", []),
                        targets=event_data.get("targets", []),
                        hunters=event_data.get("hunters", []),
                        report_id=event_data.get("report_id"),
                        evidence_requests=event_data.get("evidence_requests", []),
                        evidence_generated=event_data.get("evidence_generated", []),
                        ai_suggestions=event_data.get("ai_suggestions", []),
                        manual_guidance=event_data.get("manual_guidance", []),
                        metadata=event_data.get("metadata", {}),
                        related_events=event_data.get("related_events", []),
                        status=event_data.get("status", "active"),
                        channel=event_data.get("channel", "web"),
                        ui_hints=event_data.get("ui_hints", {}),
                    )

                    self.events[mission_event.id] = mission_event
                    self.timeline.append(mission_event)

                    # Create a conversation for the event
                    conversation = self._create_event_conversation(mission_event)
                    self.conversations[conversation.id] = conversation

        except Exception as e:
            self.logger.error(f"Error processing incoming events: {e}")

    def _create_event_conversation(self, event: MissionEvent) -> EventConversation:
        """Create a conversation for a mission event"""
        conversation_id = f"conv_{event.id}"

        return EventConversation(
            id=conversation_id,
            report_id=event.report_id,
            type=ConversationType.PLATFORM,
            participants=event.hunters,
            messages=[],
            last_activity=event.timestamp,
            unread_count=1,
            archived=False,
            starred=False,
            tags=[event.type, event.platforms[0] if event.platforms else "unknown"],
            evidence_ids=event.evidence_generated,
            status="active",
        )

    async def send_notification(
        self,
        event_type: str,
        title: str,
        message: str,
        priority: str = "medium",
        platforms: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        dedup_key: str | None = None,
    ) -> None:
        """
        Send a notification through the Mission Inbox.

        This creates a Mission Event and routes it through the notification system.
        """
        try:
            # Create Mission Event
            mission_event = MissionEvent(
                id=f"mission_event_{int(time.time())}_{event_type}",
                type=event_type,
                priority=EventPriority(priority.lower()),
                title=title,
                message=message,
                timestamp=time.time(),
                platforms=platforms or [],
                targets=[],
                hunters=[],
                report_id=None,
                evidence_requests=[],
                evidence_generated=[],
                ai_suggestions=[],
                manual_guidance=[],
                metadata=metadata or {},
                related_events=[],
                status="active",
                channel="web",
            )

            # Send to notification hub
            notif = self.notification_hub.notify(
                type_=f"mission:{event_type}",
                title=title,
                message=message,
                severity=priority,
                priority=priority,
                channels=platforms,
                metadata=metadata,
                dedup_key=dedup_key,
            )

            if notif:
                # Add to timeline
                self.timeline.append(mission_event)
                self.events[mission_event.id] = mission_event

                # Create conversation
                conversation = self._create_event_conversation(mission_event)
                self.conversations[conversation.id] = conversation

                # Emit event for other components
                self.event_bus.publish("mission_event:created", mission_event=mission_event, notification=notif)

        except Exception as e:
            self.logger.error(f"Error sending notification through Mission Inbox: {e}")

    async def handle_platform_response(
        self, event_type: str, conversation_id: str, response_data: dict[str, Any]
    ) -> None:
        """
        Handle platform response and update Mission Inbox accordingly.

        This processes responses from platforms (HackerOne, Bugcrowd, etc.)
        and updates the conversation and evidence.
        """
        try:
            if conversation_id not in self.conversations:
                self.logger.error(f"Conversation not found: {conversation_id}")
                return

            conversation = self.conversations[conversation_id]
            event = self.events.get(conversation.report_id) if conversation.report_id else None

            if event:
                # Add platform response to conversation
                self.ai_guidance.add_conversation_response(conversation, response_data)

                # Update event based on platform response
                if "approved" in response_data.get("content", "").lower():
                    event.status = "accepted"
                elif "rejected" in response_data.get("content", "").lower():
                    event.status = "rejected"
                    # Generate evidence for rejection
                    await self._generate_rejection_evidence(event, conversation)

                # Check for evidence requests in the response
                if "need" in response_data.get("content", "").lower():
                    await self._process_evidence_requests(event, conversation, response_data)

        except Exception as e:
            self.logger.error(f"Error handling platform response: {e}")

    async def _generate_rejection_evidence(self, event: MissionEvent, conversation: EventConversation) -> None:
        """Generate evidence for event rejection"""
        try:
            # Create evidence for rejection
            evidence_id = f"evidence_rejection_{event.id}_{int(time.time())}"
            evidence = EvidenceItem(
                id=evidence_id,
                type=EvidenceType.ADDITIONAL,
                title=f"Rejection Evidence for {event.title}",
                description="Evidence supporting the rejection of the report",
                ai_generated=True,
                human_reviewed=False,
                metadata={"event_id": event.id, "conversation_id": conversation.id, "type": "rejection_evidence"},
            )

            self.evidences[evidence_id] = evidence
            conversation.evidence_ids.append(evidence_id)

            # Emit event for UI updates
            self.event_bus.publish(
                "evidence:generated", evidence=evidence, conversation_id=conversation.id, event_id=event.id
            )

        except Exception as e:
            self.logger.error(f"Error generating rejection evidence: {e}")

    async def _process_evidence_requests(
        self, event: MissionEvent, conversation: EventConversation, response_data: dict[str, Any]
    ) -> None:
        """Process evidence requests from platform responses"""
        try:
            # Extract evidence request types from the response
            content = response_data.get("content", "").lower()
            evidence_types = self._extract_evidence_types_from_text(content)

            for evidence_type in evidence_types:
                # Generate the requested evidence
                evidence = await self.ai_guidance.generate_evidence(
                    report_id=event.report_id or "",
                    evidence_request=evidence_type,
                    event_context={
                        "report_title": event.title,
                        "finding_type": response_data.get("finding_type", ""),
                        "target": response_data.get("target", ""),
                        "platform": event.platforms[0] if event.platforms else "",
                    },
                )

                if evidence:
                    self.evidences[evidence.id] = evidence
                    conversation.evidence_ids.append(evidence.id)

                    # Add AI guidance response to conversation
                    ai_response = await self.ai_guidance.generate_ai_guidance_response(
                        conversation, event, {"role": "researcher", "experience": "10+ years"}
                    )

                    self.ai_guidance.add_conversation_response(conversation, ai_response)

        except Exception as e:
            self.logger.error(f"Error processing evidence requests: {e}")

    def _extract_evidence_types_from_text(self, text: str) -> list[EvidenceType]:
        """Extract evidence types requested in text"""
        evidence_types = []
        text_lower = text.lower()

        evidence_keywords = {
            EvidenceType.SCREENSHOT: ["screenshot", "captura de pantalla", "screen", "foto", "image", "img"],
            EvidenceType.VIDEO: ["video", "vídeo", "tutorial", "demonstration", "demo", "grabación"],
            EvidenceType.LOG: ["log", "logs", "registro", "logs del sistema"],
            EvidenceType.REQUEST: ["request", "response", "http request", "http response", "requisición", "respuesta"],
            EvidenceType.RESPONSE: ["response", "request", "http response", "http request"],
            EvidenceType.TIMELINE: ["timeline", "cronología", "historial", "actividad", "sequence"],
            EvidenceType.PLAYWRIGHT: ["playwright", "script", "automation"],
            EvidenceType.ADDITIONAL: ["additional", "extra", "more", "another", "further"],
        }

        for evidence_type, keywords in evidence_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                evidence_types.append(evidence_type)

        return evidence_types

    async def query_event(self, filters: dict[str, Any] | None = None) -> list[MissionEvent]:
        """
        Query events based on filters.

        Supported filters:
        - types: list of event types
        - priorities: list of priorities
        - platforms: list of platforms
        - start_time: timestamp start
        - end_time: timestamp end
        - hunter_ids: list of hunter IDs
        - report_ids: list of report IDs
        """
        if not filters:
            filters = {}

        events = list(self.events.values())

        # Apply filters
        if "types" in filters:
            events = [e for e in events if e.type in filters["types"]]

        if "priorities" in filters:
            events = [e for e in events if e.priority.value in filters["priorities"]]

        if "platforms" in filters:
            events = [e for e in events if any(p in e.platforms for p in filters["platforms"])]

        if "start_time" in filters:
            events = [e for e in events if e.timestamp >= filters["start_time"]]

        if "end_time" in filters:
            events = [e for e in events if e.timestamp <= filters["end_time"]]

        if "hunter_ids" in filters:
            events = [e for e in events if any(h in e.hunters for h in filters["hunter_ids"])]

        if "report_ids" in filters:
            events = [e for e in events if e.report_id in filters["report_ids"]]

        # Sort by timestamp (most recent first)
        events.sort(key=lambda x: x.timestamp, reverse=True)

        return events

    async def _handle_ai_guidance_request(self, event_type: str, **payload) -> None:
        """Handle AI guidance requests"""
        try:
            conversation_id = payload.get("conversation_id")
            if not conversation_id:
                return

            conversation = self.conversations.get(conversation_id)
            event = self.events.get(conversation.report_id or "") if conversation else None

            if conversation and event:
                # Generate AI guidance for the conversation
                ai_response = await self.ai_guidance.generate_ai_guidance_response(
                    conversation, event, {"role": "researcher", "experience": "10+ years"}
                )

                # Add to conversation
                self.ai_guidance.add_conversation_response(conversation, ai_response)

        except Exception as e:
            self.logger.error(f"Error handling AI guidance request: {e}")

    async def _handle_event(self, event_type: str, **payload) -> None:
        """Handle events from the event bus"""
        try:
            # Process incoming events for mission inbox
            if event_type.startswith("platform:"):
                await self.process_platform_event(payload)
            elif event_type.startswith("hunt:"):
                await self.process_hunt_event(payload)
            elif event_type.startswith("report:"):
                await self.process_report_event(payload)

        except Exception as e:
            self.logger.error(f"Error handling event: {e}")

    async def process_platform_event(self, payload: dict[str, Any]) -> None:
        """Process platform events"""
        # Map platform event to Mission Inbox event
        event_type = payload.get("event_type", "")
        if not event_type:
            return

        # Create title and message from event data
        title = f"{event_type.replace(':', ' ')}"
        message = payload.get("message", "")

        # Map platform to platform name
        platform = payload.get("platform", "") or event_type.split(":")[0] if ":" in event_type else "unknown"

        # Send to notification hub and create mission event
        await self.send_notification(
            event_type=f"platform_response:{event_type}",
            title=title,
            message=message,
            priority=payload.get("priority", "medium"),
            platforms=[platform],
            metadata={
                "event_type": event_type,
                "conversation_id": payload.get("conversation_id"),
                "report_id": payload.get("report_id"),
                "platform_response": True,
                "ai_guidance": True,
            },
        )

    async def process_hunt_event(self, payload: dict[str, Any]) -> None:
        """Process hunt events"""
        # Similar to platform events but for hunt operations
        event_type = payload.get("event_type", "")

        title = f"Hunt Update: {event_type}"
        message = payload.get("message", "")

        await self.send_notification(
            event_type=f"hunt_event:{event_type}",
            title=title,
            message=message,
            priority=payload.get("priority", "medium"),
            platforms=payload.get("platforms", []),
            metadata={
                "event_type": event_type,
                "hunt_id": payload.get("hunt_id"),
                "hunter_id": payload.get("hunter_id"),
                "ai_guidance": True,
            },
        )

    async def process_report_event(self, payload: dict[str, Any]) -> None:
        """Process report events"""
        # Similar to hunt events but for report operations
        event_type = payload.get("event_type", "")

        title = f"Report Update: {event_type}"
        message = payload.get("message", "")

        await self.send_notification(
            event_type=f"report_event:{event_type}",
            title=title,
            message=message,
            priority=payload.get("priority", "medium"),
            platforms=payload.get("platforms", []),
            metadata={
                "event_type": event_type,
                "report_id": payload.get("report_id"),
                "hunter_id": payload.get("hunter_id"),
                "ai_guidance": True,
            },
        )

    async def get_event_by_id(self, event_id: str) -> MissionEvent | None:
        """Get a specific event by ID"""
        return self.events.get(event_id)

    async def get_conversation_by_id(self, conversation_id: str) -> EventConversation | None:
        """Get a specific conversation by ID"""
        return self.conversations.get(conversation_id)

    async def get_evidence_by_id(self, evidence_id: str) -> EvidenceItem | None:
        """Get a specific evidence by ID"""
        return self.evidences.get(evidence_id)

    async def generate_ai_guidance(self, conversation_id: str) -> dict[str, Any]:
        """
        Generate AI guidance for a conversation.

        This method can be called from the UI or by event handlers when
        a conversation needs AI assistance.
        """
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return {"error": "Conversation not found"}

        event = self.events.get(conversation.report_id) if conversation.report_id else None

        if not event:
            return {"error": "Event not found for conversation"}

        # Generate AI guidance
        return await self.ai_guidance.generate_ai_guidance_response(
            conversation, event, {"role": "researcher", "experience": "10+ years"}
        )

    async def take_manual_action(self, report_id: str, action: dict[str, Any]) -> bool:
        """
        Take a manual action on a report.

        Args:
            report_id: The report ID
            action: Action to take (type, parameters, etc.)

        Returns:
            True if action was taken successfully
        """
        try:
            event = self.events.get(report_id)
            if not event:
                return False

            action_type = action.get("type", "")
            parameters = action.get("parameters", {})

            # Handle different action types
            if action_type == "generate_evidence":
                evidence_type = parameters.get("evidence_type")
                if evidence_type:
                    evidence = await self.ai_guidance.generate_evidence(
                        report_id=report_id, evidence_request=evidence_type, event_context={"report_title": event.title}
                    )
                    if evidence:
                        self.evidences[evidence.id] = evidence
                        # Add to conversation
                        conversation = next((c for c in self.conversations.values() if c.report_id == report_id), None)
                        if conversation:
                            conversation.evidence_ids.append(evidence.id)
                        return True
            elif action_type == "send_communication":
                # Send a message to the platform via conversation
                await self._send_conversation_message(
                    conversation_id=event.conversation_id or "",
                    message=parameters.get("message", ""),
                    sender=parameters.get("sender", "hunter"),
                )
            elif action_type == "approve_report":
                # Approve the report
                event.status = "approved"
                return True
            elif action_type == "reject_report":
                # Reject the report
                event.status = "rejected"
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error taking manual action: {e}")
            return False

    async def _send_conversation_message(self, conversation_id: str, message: str, sender: str) -> None:
        """Send a message to a conversation thread"""
        conversation = self.conversations.get(conversation_id)
        if conversation:
            response_data = {"sender": sender, "content": message, "timestamp": time.time(), "type": "text"}
            self.ai_guidance.add_conversation_response(conversation, response_data)

    async def get_timeline(
        self, scope: TimelineScope = TimelineScope.THIS_WEEK, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get the mission timeline with the specified scope and filters.

        Args:
            scope: Timeline scope (today, yesterday, this_week, this_month, all)
            filters: Optional filters for events

        Returns:
            List of timeline events with metadata
        """
        if filters is None:
            filters = {}

        # Get events based on scope
        events = await self.query_event(filters)

        # Apply timeline scope filtering
        now = time.time()
        today_start = now - 86400  # 24 hours ago
        yesterday_start = today_start - 86400  # 48 hours ago
        this_week_start = today_start - (7 * 86400)  # 7 days ago
        this_month_start = today_start - (30 * 86400)  # 30 days ago

        if scope == TimelineScope.TODAY:
            events = [e for e in events if e.timestamp >= today_start]
        elif scope == TimelineScope.YESTERDAY:
            events = [e for e in events if yesterday_start <= e.timestamp < today_start]
        elif scope == TimelineScope.THIS_WEEK:
            events = [e for e in events if e.timestamp >= this_week_start]
        elif scope == TimelineScope.THIS_MONTH:
            events = [e for e in events if e.timestamp >= this_month_start]

        # Convert to timeline format with additional metadata
        timeline = []
        for event in events:
            timeline.append(
                {
                    "id": event.id,
                    "type": event.type,
                    "priority": event.priority.value,
                    "title": event.title,
                    "message": event.message,
                    "timestamp": event.timestamp,
                    "platforms": event.platforms,
                    "targets": event.targets,
                    "hunters": event.hunters,
                    "report_id": event.report_id,
                    "status": event.status,
                    "ai_suggestions": event.ai_suggestions,
                    "manual_guidance": event.manual_guidance,
                    "conversation_id": event.conversation_id,
                }
            )

        return timeline

    async def get_filtered_timeline(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get a timeline with advanced filtering and grouping.

        Returns a structured timeline with groups by date/scoped.
        """
        timeline = await self.get_timeline(TimelineScope.ALL, filters)

        # Group by timeline
        today_events = [e for e in timeline if self._is_today(e["timestamp"])]
        yesterday_events = [e for e in timeline if self._is_yesterday(e["timestamp"])]
        this_week_events = [e for e in timeline if self._is_this_week(e["timestamp"])]
        this_month_events = [e for e in timeline if self._is_this_month(e["timestamp"])]
        older_events = [e for e in timeline if not self._is_this_month(e["timestamp"])]

        return {
            "today": today_events,
            "yesterday": yesterday_events,
            "this_week": this_week_events,
            "this_month": this_month_events,
            "older": older_events,
            "total_count": len(timeline),
            "today_count": len(today_events),
            "yesterday_count": len(yesterday_events),
            "this_week_count": len(this_week_events),
            "this_month_count": len(this_month_events),
            "older_count": len(older_events),
        }

    def _is_today(self, timestamp: float) -> bool:
        """Check if a timestamp is from today"""
        event_time = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        return event_time.date() == now.date() and event_time.hour == now.hour and event_time.minute == now.minute

    def _is_yesterday(self, timestamp: float) -> bool:
        """Check if a timestamp is from yesterday"""
        event_time = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        return (
            event_time.date() == yesterday.date()
            and event_time.hour == yesterday.hour
            and event_time.minute == yesterday.minute
        )

    def _is_this_week(self, timestamp: float) -> bool:
        """Check if a timestamp is from this week"""
        event_time = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        start_of_week = now - timedelta(days=now.weekday())
        return event_time >= start_of_week

    def _is_this_month(self, timestamp: float) -> bool:
        """Check if a timestamp is from this month"""
        event_time = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        return event_time.year == now.year and event_time.month == now.month

    async def get_platform_responses(self, report_id: str) -> list[dict[str, Any]]:
        """
        Get all platform responses for a specific report.

        Returns the conversation thread for the report.
        """
        event = await self.get_event_by_id(report_id)
        if not event or not event.conversation_id:
            return []

        conversation = self.conversations.get(event.conversation_id)
        if not conversation:
            return []

        # Format conversation messages
        messages = []
        for message in conversation.messages:
            messages.append(
                {
                    "id": message["id"],
                    "sender": message["sender"],
                    "content": message["content"],
                    "timestamp": message["timestamp"],
                    "type": message["type"],
                    "attachments": message.get("attachments", []),
                    "metadata": message.get("metadata", {}),
                }
            )

        return messages

    async def search_timeline(self, query: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Search timeline for specific content.

        Args:
            query: Search query
            filters: Optional filters

        Returns:
            Search results with highlighted matches
        """
        if filters is None:
            filters = {}

        timeline = await self.get_timeline(TimelineScope.ALL, filters)
        query_lower = query.lower()

        # Search in timeline events
        event_results = []
        for event in timeline:
            matches = []

            # Check title and message for matches
            if query_lower in event["title"].lower():
                matches.append("title")
            if query_lower in event["message"].lower():
                matches.append("message")

            # Check metadata for matches
            for key, value in event.get("metadata", {}).items():
                if isinstance(value, str) and query_lower in value.lower():
                    matches.append(f"metadata.{key}")

            if matches:
                event["matches"] = matches
                event_results.append(event)

        # Search in conversations
        conversation_results = []
        for conv_id, conversation in self.conversations.items():
            message_matches = []
            for message in conversation.messages:
                if query_lower in message.get("content", "").lower():
                    message_matches.append(message)

            if message_matches:
                conversation_events = {
                    "conversation_id": conv_id,
                    "report_id": conversation.report_id,
                    "type": conversation.type,
                    "last_activity": conversation.last_activity,
                    "messages": message_matches,
                    "matches": ["messages"],
                }
                conversation_results.append(conversation_events)

        # Search in evidence
        evidence_results = []
        for _evidence_id, evidence in self.evidences.items():
            if query_lower in evidence.title.lower() or query_lower in evidence.description.lower():
                evidence.matches = ["title", "description"]
                evidence_results.append(evidence)

        return {
            "events": event_results,
            "conversations": conversation_results,
            "evidence": evidence_results,
            "total_results": len(event_results) + len(conversation_results) + len(evidence_results),
        }

    async def get_next_steps_for_report(self, report_id: str) -> list[dict[str, Any]]:
        """
        Get next steps for a specific report.

        Returns the recommended next steps based on the current state.
        """
        event = await self.get_event_by_id(report_id)
        if not event:
            return []

        conversation = None
        if event.conversation_id:
            conversation = self.conversations.get(event.conversation_id)

        # Generate next steps based on the current state
        next_steps = []

        # Check if evidence is needed
        if conversation and conversation.evidence_ids:
            evidence_types = [self.evidences[eid].type for eid in conversation.evidence_ids if eid in self.evidences]
            next_steps.append(
                {
                    "step": "review_existing_evidence",
                    "type": "review",
                    "priority": "normal",
                    "description": f"Review {len(evidence_types)} existing evidence items",
                    "completed": True,
                }
            )

        # Check if conversation has unread messages
        if conversation and conversation.unread_count > 0:
            next_steps.append(
                {
                    "step": "read_platform_responses",
                    "type": "communication",
                    "priority": "high",
                    "description": f"Read {conversation.unread_count} unread platform responses",
                    "completed": False,
                }
            )

        # Check if AI guidance available
        if event.ai_suggestions:
            next_steps.append(
                {
                    "step": "generate_ai_guidance",
                    "type": "ai_guidance",
                    "priority": "medium",
                    "description": "Generate AI guidance for next steps",
                    "completed": False,
                }
            )

        # Check if manual approval needed for AI-generated evidence
        if any(e.ai_generated and not e.human_reviewed for e in self.evidences.values()):
            next_steps.append(
                {
                    "step": "approve_ai_evidence",
                    "type": "approval",
                    "priority": "high",
                    "description": "Review and approve AI-generated evidence",
                    "completed": False,
                }
            )

        return next_steps

    async def refresh_timeline(self) -> list[dict[str, Any]]:
        """
        Refresh the timeline with the latest data from event bus.

        This is called periodically to keep the timeline up to date.
        """
        await self.process_incoming_events()
        return await self.get_timeline()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the current state of the Mission Inbox.

        Returns:
            Statistics about events, conversations, evidence, etc.
        """
        return {
            "total_events": len(self.events),
            "total_conversations": len(self.conversations),
            "total_evidence": len(self.evidences),
            "timeline_size": len(self.timeline),
            "unread_conversations": sum(1 for c in self.conversations.values() if c.unread_count > 0),
            "ai_guidance_requests": sum(1 for e in self.events.values() if e.ai_suggestions),
            "ai_generated_evidence": sum(1 for e in self.evidences.values() if e.ai_generated),
            "human_reviewed_evidence": sum(1 for e in self.evidences.values() if e.human_reviewed),
            "past_24h_events": len([e for e in self.timeline if time.time() - e.timestamp < 86400]),
            "top_priorities": self._get_top_priorities(),
            "platform_distribution": self._get_platform_distribution(),
            "event_type_distribution": self._get_event_type_distribution(),
        }

    def _get_top_priorities(self) -> dict[str, int]:
        """Get distribution of event priorities"""
        distribution: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for event in self.events.values():
            if event.priority.value in distribution:
                distribution[event.priority.value] += 1
        return distribution

    def _get_platform_distribution(self) -> dict[str, int]:
        """Get distribution of platforms"""
        distribution: dict[str, int] = {}
        for event in self.events.values():
            for platform in event.platforms:
                distribution[platform] = distribution.get(platform, 0) + 1
        return distribution

    def _get_event_type_distribution(self) -> dict[str, int]:
        """Get distribution of event types"""
        distribution: dict[str, int] = {}
        for event in self.events.values():
            distribution[event.type] = distribution.get(event.type, 0) + 1
        return distribution

    async def set_event_read(self, event_id: str) -> bool:
        """
        Mark an event as read.

        This updates the event's status and reduces unread counts
        in associated conversations.
        """
        event = self.events.get(event_id)
        if not event:
            return False

        event.status = "read"
        return True

    async def archive_event(self, event_id: str) -> bool:
        """
        Archive an event.

        This moves the event to archive and updates associated
        conversations.
        """
        event = self.events.get(event_id)
        if not event:
            return False

        event.status = "archived"

        # Archive associated conversation
        if event.conversation_id and event.conversation_id in self.conversations:
            self.conversations[event.conversation_id].archived = True

        return True

    async def star_event(self, event_id: str) -> bool:
        """
        Star an event.

        This marks the event as important and updates
        associated conversations.
        """
        event = self.events.get(event_id)
        if not event:
            return False

        event.priority = EventPriority.URGENT if event.priority == EventPriority.HIGH else event.priority

        # Star associated conversation
        if event.conversation_id and event.conversation_id in self.conversations:
            self.conversations[event.conversation_id].starred = True

        return True

    async def add_tag_to_event(self, event_id: str, tag: str) -> bool:
        """
        Add a tag to an event.

        This tags the event and updates associated conversations.
        """
        event = self.events.get(event_id)
        if not event:
            return False

        if tag not in event.metadata.get("tags", []):
            if "tags" not in event.metadata:
                event.metadata["tags"] = []
            event.metadata["tags"].append(tag)

        # Tag associated conversation
        if (
            event.conversation_id
            and event.conversation_id in self.conversations
            and tag not in self.conversations[event.conversation_id].tags
        ):
            self.conversations[event.conversation_id].tags.append(tag)

        return True

    async def remove_tag_from_event(self, event_id: str, tag: str) -> bool:
        """
        Remove a tag from an event.

        This removes the tag from the event and updates
        associated conversations.
        """
        event = self.events.get(event_id)
        if not event:
            return False

        if "tags" in event.metadata and tag in event.metadata["tags"]:
            event.metadata["tags"].remove(tag)

        # Remove tag from associated conversation
        if (
            event.conversation_id
            and event.conversation_id in self.conversations
            and tag in self.conversations[event.conversation_id].tags
        ):
            self.conversations[event.conversation_id].tags.remove(tag)

        return True

    async def get_timeline_for_scope(self, scope: TimelineScope) -> dict[str, Any]:
        """
        Get the timeline for a specific scope with detailed information.

        Args:
            scope: The timeline scope (today, yesterday, this_week, this_month, all)

        Returns:
            Detailed timeline information for the specified scope
        """
        # Get events for the scope
        events = await self.get_timeline(scope)

        # Group by date for display
        grouped_events: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            timestamp = event["timestamp"]
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

            if date_str not in grouped_events:
                grouped_events[date_str] = []

            # Get additional event information
            event_details = {
                "id": event["id"],
                "type": event["type"],
                "priority": event["priority"],
                "title": event["title"],
                "message": event["message"],
                "timestamp": event["timestamp"],
                "platforms": event["platforms"],
                "targets": event["targets"],
                "hunters": event["hunters"],
                "report_id": event.get("report_id"),
                "status": event.get("status", "active"),
                "conversation_id": event.get("conversation_id"),
                "ai_suggestions": event.get("ai_suggestions", []),
                "metadata": event.get("metadata", {}),
            }

            grouped_events[date_str].append(event_details)

        # Sort dates (newest first)
        sorted_dates = sorted(grouped_events.keys(), reverse=True)

        return {
            "scope": scope.value,
            "total_events": len(events),
            "grouped_events": {date: grouped_events[date] for date in sorted_dates},
            "date_range": {
                "start": min([e["timestamp"] for e in events]) if events else None,
                "end": max([e["timestamp"] for e in events]) if events else None,
            },
        }

    async def get_events_by_date_range(self, start_timestamp: float, end_timestamp: float) -> list[MissionEvent]:
        """
        Get events within a specific date range.

        Args:
            start_timestamp: Start timestamp (Unix)
            end_timestamp: End timestamp (Unix)

        Returns:
            List of events within the specified date range
        """
        return [e for e in self.events.values() if start_timestamp <= e.timestamp <= end_timestamp]

    async def get_events_by_platform(self, platform: str) -> list[MissionEvent]:
        """
        Get all events for a specific platform.

        Args:
            platform: The platform name

        Returns:
            List of events for the specified platform
        """
        return [e for e in self.events.values() if platform in e.platforms]

    async def get_events_by_hunter(self, hunter_id: str) -> list[MissionEvent]:
        """
        Get all events for a specific hunter.

        Args:
            hunter_id: The hunter ID

        Returns:
            List of events for the specified hunter
        """
        return [e for e in self.events.values() if hunter_id in e.hunters]

    async def get_active_conversations(self) -> list[dict[str, Any]]:
        """
        Get all active (non-archived) conversations.

        Returns:
            List of conversation details
        """
        conversations = []
        for conv_id, conversation in self.conversations.items():
            if not conversation.archived:
                conversations.append(
                    {
                        "id": conv_id,
                        "report_id": conversation.report_id,
                        "type": conversation.type,
                        "participants": conversation.participants,
                        "last_activity": conversation.last_activity,
                        "unread_count": conversation.unread_count,
                        "starred": conversation.starred,
                        "tags": conversation.tags,
                        "message_count": len(conversation.messages),
                        "evidence_ids": conversation.evidence_ids,
                        "status": conversation.status,
                    }
                )

        return conversations

    async def get_archived_conversations(self) -> list[dict[str, Any]]:
        """
        Get all archived conversations.

        Returns:
            List of archived conversation details
        """
        conversations = []
        for conv_id, conversation in self.conversations.items():
            if conversation.archived:
                conversations.append(
                    {
                        "id": conv_id,
                        "report_id": conversation.report_id,
                        "type": conversation.type,
                        "participants": conversation.participants,
                        "last_activity": conversation.last_activity,
                        "unread_count": conversation.unread_count,
                        "starred": conversation.starred,
                        "tags": conversation.tags,
                        "message_count": len(conversation.messages),
                        "evidence_ids": conversation.evidence_ids,
                        "resolved_at": conversation.resolved_at,
                    }
                )

        return conversations

    async def add_conversation_tag(self, conversation_id: str, tag: str) -> bool:
        """
        Add a tag to a conversation.

        Args:
            conversation_id: The conversation ID
            tag: The tag to add

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            if tag not in self.conversations[conversation_id].tags:
                self.conversations[conversation_id].tags.append(tag)
            return True
        return False

    async def remove_conversation_tag(self, conversation_id: str, tag: str) -> bool:
        """
        Remove a tag from a conversation.

        Args:
            conversation_id: The conversation ID
            tag: The tag to remove

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations and tag in self.conversations[conversation_id].tags:
            self.conversations[conversation_id].tags.remove(tag)
            return True
        return False

    async def star_conversation(self, conversation_id: str) -> bool:
        """
        Star a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].starred = True
            return True
        return False

    async def unstar_conversation(self, conversation_id: str) -> bool:
        """
        Unstar a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].starred = False
            return True
        return False

    async def archive_conversation(self, conversation_id: str) -> bool:
        """
        Archive a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].archived = True
            return True
        return False

    async def unarchive_conversation(self, conversation_id: str) -> bool:
        """
        Unarchive a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].archived = False
            return True
        return False

    async def mark_conversation_unread(self, conversation_id: str) -> bool:
        """
        Mark a conversation as unread.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].unread_count += 1
            return True
        return False

    async def mark_conversation_read(self, conversation_id: str) -> bool:
        """
        Mark a conversation as read.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if successful, False otherwise
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id].unread_count = max(
                0, self.conversations[conversation_id].unread_count - 1
            )
            return True
        return False

    async def get_conversation_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of conversation messages
        """
        if conversation_id not in self.conversations:
            return []

        conversation = self.conversations[conversation_id]

        messages = []
        for message in conversation.messages:
            messages.append(
                {
                    "id": message["id"],
                    "sender": message["sender"],
                    "content": message["content"],
                    "timestamp": message["timestamp"],
                    "type": message["type"],
                    "attachments": message.get("attachments", []),
                    "metadata": message.get("metadata", {}),
                }
            )

        return messages

    async def add_conversation_message(self, conversation_id: str, message_data: dict[str, Any]) -> bool:
        """
        Add a message to a conversation.

        Args:
            conversation_id: The conversation ID
            message_data: The message data

        Returns:
            True if successful, False otherwise
        """
        if conversation_id not in self.conversations:
            return False

        message = {
            "id": f"msg_{int(time.time())}_{len(self.conversations[conversation_id].messages)}",
            "sender": message_data.get("sender", "hunter"),
            "content": message_data.get("content", ""),
            "timestamp": time.time(),
            "type": message_data.get("type", "text"),
            "attachments": message_data.get("attachments", []),
            "metadata": message_data.get("metadata", {}),
        }

        self.conversations[conversation_id].messages.append(message)
        self.conversations[conversation_id].last_activity = time.time()

        if message["sender"] != "ai_assistant":
            self.conversations[conversation_id].unread_count += 1

        # Emit event for new message
        self.event_bus.publish("conversation:message_added", conversation_id=conversation_id, message=message)

        return True

    async def get_unread_conversations(self) -> list[dict[str, Any]]:
        """
        Get all conversations with unread messages.

        Returns:
            List of conversations with unread messages
        """
        conversations = []
        for conv_id, conversation in self.conversations.items():
            if conversation.unread_count > 0:
                conversations.append(
                    {
                        "id": conv_id,
                        "report_id": conversation.report_id,
                        "type": conversation.type,
                        "participants": conversation.participants,
                        "last_activity": conversation.last_activity,
                        "unread_count": conversation.unread_count,
                        "starred": conversation.starred,
                        "tags": conversation.tags,
                        "message_count": len(conversation.messages),
                        "evidence_ids": conversation.evidence_ids,
                        "status": conversation.status,
                    }
                )

        return conversations

    async def get_next_steps_for_conversation(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Get next steps for a specific conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of next steps for the conversation
        """
        if conversation_id not in self.conversations:
            return []

        conversation = self.conversations[conversation_id]
        next_steps = []

        # Check if there are unread messages
        if conversation.unread_count > 0:
            next_steps.append(
                {
                    "step": "read_messages",
                    "type": "communication",
                    "priority": "medium",
                    "description": f"Read {conversation.unread_count} unread messages",
                    "completed": False,
                }
            )

        # Check if there are evidence items
        if conversation.evidence_ids:
            next_steps.append(
                {
                    "step": "review_evidence",
                    "type": "evidence_review",
                    "priority": "high",
                    "description": f"Review {len(conversation.evidence_ids)} evidence items",
                    "completed": False,
                }
            )

        # Check if conversation needs AI guidance
        if not conversation.evidence_ids:
            next_steps.append(
                {
                    "step": "generate_ai_guidance",
                    "type": "ai_guidance",
                    "priority": "low",
                    "description": "Generate AI guidance for next steps",
                    "completed": False,
                }
            )

        return next_steps

    async def get_timeline_summary(self, scope: TimelineScope = TimelineScope.THIS_WEEK) -> dict[str, Any]:
        """
        Get a summary of timeline events for a specific scope.

        Args:
            scope: The timeline scope

        Returns:
            Summary of timeline events
        """
        timeline = await self.get_timeline(scope)

        # Calculate statistics
        total_events = len(timeline)
        priority_counts = {priority: 0 for priority in EventPriority}
        type_counts: dict[str, int] = {}
        platform_counts: dict[str, int] = {}

        for event in timeline:
            priority_counts[event["priority"]] = priority_counts.get(event["priority"], 0) + 1
            type_counts[event["type"]] = type_counts.get(event["type"], 0) + 1
            for platform in event.get("platforms", []):
                platform_counts[platform] = platform_counts.get(platform, 0) + 1

        return {
            "scope": scope.value,
            "total_events": total_events,
            "priority_breakdown": priority_counts,
            "type_breakdown": type_counts,
            "platform_breakdown": platform_counts,
            "top_priorities": sorted(
                priority_counts.items(),
                key=lambda x: [
                    EventPriority.URGENT.value,
                    EventPriority.HIGH.value,
                    EventPriority.NORMAL.value,
                    EventPriority.LOW.value,
                ].index(x[1]),
            )
            if "protobuf" in str(priority_counts)
            else priority_counts,
            "recent_activity": self._calculate_recent_activity(timeline),
        }

    def _calculate_recent_activity(self, timeline: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate recent activity statistics"""
        now = time.time()
        recent_events = []

        for event in timeline:
            if now - event["timestamp"] < 24 * 3600:  # Last 24 hours
                recent_events.append(event)

        return {
            "last_24h_count": len(recent_events),
            "last_24h_by_priority": self._get_activity_by_priority(recent_events),
            "last_24h_by_type": self._get_activity_by_type(recent_events),
            "most_active_hour": self._find_most_active_hour(recent_events),
        }

    def _get_activity_by_priority(self, events: list[dict[str, Any]]) -> dict[str, int]:
        """Get activity count by priority"""
        counts = {priority.value: 0 for priority in EventPriority}
        for event in events:
            priority = event["priority"]
            counts[priority] = counts.get(priority, 0) + 1
        return counts

    def _get_activity_by_type(self, events: list[dict[str, Any]]) -> dict[str, int]:
        """Get activity count by type"""
        counts: dict[str, int] = {}
        for event in events:
            event_type = event["type"]
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    def _find_most_active_hour(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Find the most active hour"""
        hour_counts: dict[int, int] = {}
        for event in events:
            hour = datetime.fromtimestamp(event["timestamp"]).hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if not hour_counts:
            return {"hour": None, "count": 0}

        most_active_hour = max(hour_counts.items(), key=lambda x: x[1])
        return {"hour": most_active_hour[0], "count": most_active_hour[1]}

    async def search_timeline_advanced(self, query: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Advanced search across timeline, conversations, and evidence.

        Args:
            query: Search query
            filters: Optional filters

        Returns:
            Search results
        """
        if filters is None:
            filters = {}

        timeline = await self.get_timeline(TimelineScope.ALL, filters)
        conversations = await self.get_active_conversations()
        evidence = await self.get_evidence_list()

        # Search in timeline
        timeline_results = self._search_in_timeline(timeline, query)

        # Search in conversations
        conversation_results = self._search_in_conversations(conversations, query)

        # Search in evidence
        evidence_results = self._search_in_evidence(evidence, query)

        return {
            "timeline_results": timeline_results,
            "conversation_results": conversation_results,
            "evidence_results": evidence_results,
            "total_results": len(timeline_results) + len(conversation_results) + len(evidence_results),
        }

    def _search_in_timeline(self, timeline: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Search in timeline events"""
        query_lower = query.lower()
        results = []

        for event in timeline:
            matches = []

            # Check title
            if query_lower in event["title"].lower():
                matches.append("title")

            # Check message
            if query_lower in event["message"].lower():
                matches.append("message")

            # Check metadata
            for key, value in event.get("metadata", {}).items():
                if isinstance(value, str) and query_lower in value.lower():
                    matches.append(f"metadata.{key}")

            if matches:
                event["matches"] = matches
                results.append(event)

        return results

    def _search_in_conversations(self, conversations: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Search in conversations"""
        results = []
        query_lower = query.lower()

        for conv in conversations:
            # Search in participants
            matches = False
            if any(query_lower in participant.lower() for participant in conv.get("participants", [])):
                matches = True

            # Search in tags
            if any(query_lower in tag.lower() for tag in conv.get("tags", [])):
                matches = True

            # Search in description (from messages)
            for message in conv.get("messages", []):
                if query_lower in message.get("content", "").lower():
                    matches = True
                    break

            if matches:
                conv["matches"] = matches
                results.append(conv)

        return results

    def _search_in_evidence(self, evidence: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Search in evidence"""
        results = []
        query_lower = query.lower()

        for item in evidence:
            matches = []

            # Check title
            if query_lower in item["title"].lower():
                matches.append("title")

            # Check description
            if query_lower in item["description"].lower():
                matches.append("description")

            # Check metadata
            for key, value in item.get("metadata", {}).items():
                if isinstance(value, str) and query_lower in value.lower():
                    matches.append(f"metadata.{key}")

            if matches:
                item["matches"] = matches
                results.append(item)

        return results

    async def get_evidence_list(self) -> list[dict[str, Any]]:
        """
        Get list of all evidence items.

        Returns:
            List of evidence items
        """
        evidence_list = []
        for evidence_id, evidence in self.evidences.items():
            evidence_list.append(
                {
                    "id": evidence_id,
                    "type": evidence.type.value,
                    "title": evidence.title,
                    "description": evidence.description,
                    "ai_generated": evidence.ai_generated,
                    "human_reviewed": evidence.human_reviewed,
                    "uploaded_by": evidence.uploaded_by,
                    "uploaded_at": evidence.uploaded_at,
                    "priority": evidence.priority,
                    "completeness_score": evidence.completeness_score,
                    "quality_score": evidence.quality_score,
                    "metadata": evidence.metadata,
                }
            )

        return evidence_list

    async def get_timeline_statistics(self) -> dict[str, Any]:
        """
        Get timeline statistics for analytics.

        Returns:
            Timeline statistics
        """
        timeline = await self.get_timeline()

        # Calculate statistics
        stats: dict[str, Any] = {
            "total_events": len(timeline),
            "last_24h": len([e for e in timeline if time.time() - e["timestamp"] < 24 * 3600]),
            "last_7d": len([e for e in timeline if time.time() - e["timestamp"] < 7 * 86400]),
            "last_30d": len([e for e in timeline if time.time() - e["timestamp"] < 30 * 86400]),
            "active_conversations": len([c for c in self.conversations.values() if not c.archived]),
            "unread_messages": sum(c.unread_count for c in self.conversations.values()),
            "ai_guidance_requests": sum(1 for c in self.conversations.values() if c.messages),
            "evidence_generated": len([e for e in self.evidences.values() if e.ai_generated]),
            "human_reviewed_evidence": len([e for e in self.evidences.values() if e.human_reviewed]),
        }

        # Add distribution statistics
        stats["priority_distribution"] = self._get_priority_distribution(timeline)
        stats["type_distribution"] = self._get_type_distribution(timeline)

        return stats

    def _get_priority_distribution(self, timeline: list[dict[str, Any]]) -> dict[str, int]:
        """Get priority distribution"""
        distribution = {priority.value: 0 for priority in EventPriority}
        for event in timeline:
            priority = event["priority"]
            distribution[priority] = distribution.get(priority, 0) + 1
        return distribution

    def _get_type_distribution(self, timeline: list[dict[str, Any]]) -> dict[str, int]:
        """Get type distribution"""
        distribution: dict[str, int] = {}
        for event in timeline:
            event_type = event["type"]
            distribution[event_type] = distribution.get(event_type, 0) + 1
        return distribution

    async def generate_ai_guidance_for_missing_evidence(self, report_id: str) -> dict[str, Any]:
        """
        Generate AI guidance for missing evidence needs.

        Args:
            report_id: The report ID

        Returns:
            AI guidance for missing evidence
        """
        event = await self.get_event_by_id(report_id)
        if not event:
            return {"error": "Event not found"}

        # Generate AI guidance
        ai_guidance = await self.ai_guidance.generate_ai_guidance_response(
            None,  # type: ignore[arg-type]  # No conversation for this
            event,
            {"role": "researcher", "experience": "10+ years"},
        )

        return ai_guidance

    async def start_evidence_generation(
        self, report_id: str, evidence_type: EvidenceType, human_approval_needed: bool = True
    ) -> dict[str, Any]:
        """
        Start evidence generation for a specific report.

        Args:
            report_id: The report ID
            evidence_type: The type of evidence to generate
            human_approval_needed: Whether human approval is needed

        Returns:
            Evidence generation request
        """
        event = await self.get_event_by_id(report_id)
        if not event:
            return {"error": "Event not found"}

        # Generate evidence
        evidence = await self.ai_guidance.generate_evidence(
            report_id=report_id,
            evidence_request=evidence_type,
            event_context={"report_title": event.title, "finding_type": "unknown", "target": "unknown"},
        )

        if evidence:
            self.evidences[evidence.id] = evidence

            # Add to conversation
            if event.conversation_id:
                conversation = self.conversations.get(event.conversation_id)
                if conversation:
                    conversation.evidence_ids.append(evidence.id)

            # Emit event
            self.event_bus.publish(
                "evidence:generation_started",
                evidence_id=evidence.id,
                evidence_type=evidence.type,
                report_id=report_id,
                human_approval_needed=human_approval_needed,
                event_id=event.id,
            )

            return {
                "evidence_id": evidence.id,
                "status": "started",
                "human_approval_needed": human_approval_needed,
                "estimated_completion_time": "15-30 minutes",
            }

        return {"error": "Failed to start evidence generation"}

    async def complete_evidence_generation(
        self, evidence_id: str, human_approval: str, quality_score: float | None = None
    ) -> bool:
        """
        Complete evidence generation with human approval.

        Args:
            evidence_id: The evidence ID
            human_approval: Human approval comment
            quality_score: Optional quality score (0-100)

        Returns:
            True if successful, False otherwise
        """
        if evidence_id not in self.evidences:
            return False

        evidence = self.evidences[evidence_id]

        # Update evidence
        evidence.human_reviewed = True
        evidence.review_comments = human_approval
        if quality_score is not None:
            evidence.quality_score = quality_score / 100.0

        # Find related conversation and update unread count
        for conversation in self.conversations.values():
            if evidence_id in conversation.evidence_ids:
                conversation.unread_count += 1
                break

        # Emit event
        self.event_bus.publish(
            "evidence:generation_completed",
            evidence_id=evidence_id,
            human_approval=human_approval,
            quality_score=quality_score,
            ai_generated=evidence.ai_generated,
        )

        return True

    async def add_ai_guidance_response(self, conversation_id: str, response_data: dict[str, Any]) -> bool:
        """
        Add AI guidance response to a conversation.

        Args:
            conversation_id: The conversation ID
            response_data: The response data

        Returns:
            True if successful, False otherwise
        """
        if conversation_id not in self.conversations:
            return False

        conversation = self.conversations[conversation_id]

        message = {
            "id": f"msg_{int(time.time())}_{len(conversation.messages)}",
            "sender": response_data.get("sender", "ai_assistant"),
            "content": response_data.get("content", ""),
            "timestamp": time.time(),
            "type": response_data.get("type", "text"),
            "metadata": response_data.get("metadata", {}),
        }

        conversation.messages.append(message)
        conversation.last_activity = time.time()

        # Emit event
        self.event_bus.publish("ai_guidance:response_added", conversation_id=conversation_id, message=message)

        return True

    async def generate_timeline_digest(self, scope: TimelineScope = TimelineScope.THIS_WEEK) -> dict[str, Any]:
        """
        Generate a timeline digest for the specified scope.

        Args:
            scope: The timeline scope

        Returns:
            Timeline digest
        """
        timeline = await self.get_timeline(scope)

        # Group by priority
        priority_groups: dict[str, list[dict[str, Any]]] = {}
        for event in timeline:
            priority = event["priority"]
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(event)

        # Generate digest summary
        digest: dict[str, Any] = {
            "scope": scope.value,
            "generated_at": time.time(),
            "total_events": len(timeline),
            "priority_summary": {},
            "top_events": [],
            "recent_activity": [],
            "recommendations": self._generate_timeline_recommendations(timeline),
        }

        # Populate priority summary
        for priority, events in priority_groups.items():
            digest["priority_summary"][priority] = {
                "count": len(events),
                "percentage": (len(events) / len(timeline) * 100) if timeline else 0,
            }

        # Add top events (highest priority)
        sorted_events = sorted(
            timeline, key=lambda e: ["critical", "high", "medium", "low"].index(e["priority"]), reverse=True
        )
        digest["top_events"] = [
            {
                "id": event["id"],
                "type": event["type"],
                "priority": event["priority"],
                "title": event["title"],
                "message": event["message"],
                "timestamp": event["timestamp"],
                "platforms": event.get("platforms", []),
                "hunters": event.get("hunters", []),
            }
            for event in sorted_events[:5]
        ]

        # Add recent activity
        now = time.time()
        day_ago = now - 86400
        recent = [e for e in timeline if e["timestamp"] >= day_ago]
        digest["recent_activity"] = [
            {
                "date": datetime.fromtimestamp(e["timestamp"]).strftime("%Y-%m-%d"),
                "count": len(
                    [
                        re
                        for re in recent
                        if datetime.fromtimestamp(re["timestamp"]).date().isoformat()
                        == datetime.fromtimestamp(e["timestamp"]).date().isoformat()
                    ]
                ),
            }
            for e in set([e["timestamp"] for e in recent])
        ]

        return digest

    def _generate_timeline_recommendations(self, timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate recommendations based on timeline data"""
        recommendations = []

        # Recommendations based on event types
        event_types = [e["type"] for e in timeline]

        if "platform:need:poc" in event_types:
            recommendations.append(
                {
                    "type": "evidence_generation",
                    "priority": "high",
                    "description": "Generate screen capture evidence for platform requests",
                    "action": "generate_evidence",
                }
            )

        if "platform:need:video" in event_types:
            recommendations.append(
                {
                    "type": "video_generation",
                    "priority": "high",
                    "description": "Create tutorial video demonstrating exploit",
                    "action": "generate_evidence",
                }
            )

        if "platform:need:logs" in event_types:
            recommendations.append(
                {
                    "type": "log_collection",
                    "priority": "medium",
                    "description": "Collect network logs for investigation",
                    "action": "generate_evidence",
                }
            )

        if "platform:need:reproduction" in event_types:
            recommendations.append(
                {
                    "type": "reproduction_setup",
                    "priority": "critical",
                    "description": "Set up reproduction environment",
                    "action": "setup_environment",
                }
            )

        # Add AI guidance recommendations
        if any("ai_guidance" in e.get("metadata", {}) for e in timeline):
            recommendations.append(
                {
                    "type": "ai_guidance_review",
                    "priority": "medium",
                    "description": "Review AI guidance suggestions",
                    "action": "review_ai_guidance",
                }
            )

        return recommendations

    async def export_timeline_data(self, scope: TimelineScope = TimelineScope.THIS_WEEK, format: str = "json") -> str:
        """
        Export timeline data in specified format.

        Args:
            scope: Timeline scope
            format: Export format (json, csv, yaml)

        Returns:
            Exported data as string
        """
        timeline = await self.get_timeline(scope)

        if format.lower() == "json":
            import json

            return json.dumps(timeline, indent=2, default=str)
        elif format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            if timeline:
                writer = csv.DictWriter(output, fieldnames=timeline[0].keys())
                writer.writeheader()
                for event in timeline:
                    writer.writerow(event)
            return output.getvalue()
        elif format.lower() == "yaml":
            try:
                import yaml

                return yaml.dump(timeline, default_flow_style=False)
            except ImportError:
                return "# YAML export requires PyYAML. Install with: pip install PyYAML"
        else:
            return f"Unsupported format: {format}"

    async def bulk_action_on_events(
        self, event_ids: list[str], action: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Take bulk actions on multiple events.

        Args:
            event_ids: List of event IDs to act on
            action: Action to take
            parameters: Additional parameters for the action

        Returns:
            Bulk action results
        """
        if parameters is None:
            parameters = {}

        results: dict[str, Any] = {"success_count": 0, "failure_count": 0, "results": []}

        for event_id in event_ids:
            try:
                if action == "archive":
                    success = await self.archive_event(event_id)
                elif action == "star":
                    success = await self.star_event(event_id)
                elif action == "add_tag":
                    tag = parameters.get("tag", "")
                    success = await self.add_tag_to_event(event_id, tag)
                elif action == "remove_tag":
                    tag = parameters.get("tag", "")
                    success = await self.remove_tag_from_event(event_id, tag)
                else:
                    success = False

                results["results"].append({"event_id": event_id, "action": action, "success": success})

                if success:
                    results["success_count"] += 1
                else:
                    results["failure_count"] += 1

            except Exception as e:
                results["results"].append({"event_id": event_id, "action": action, "success": False, "error": str(e)})
                results["failure_count"] += 1

        return results

    async def bulk_action_on_conversations(
        self, conversation_ids: list[str], action: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Take bulk actions on multiple conversations.

        Args:
            conversation_ids: List of conversation IDs to act on
            action: Action to take
            parameters: Additional parameters for the action

        Returns:
            Bulk action results
        """
        if parameters is None:
            parameters = {}

        results: dict[str, Any] = {"success_count": 0, "failure_count": 0, "results": []}

        for conv_id in conversation_ids:
            try:
                if action == "archive":
                    success = await self.archive_conversation(conv_id)
                elif action == "star":
                    success = await self.star_conversation(conv_id)
                elif action == "add_tag":
                    tag = parameters.get("tag", "")
                    success = await self.add_conversation_tag(conv_id, tag)
                elif action == "remove_tag":
                    tag = parameters.get("tag", "")
                    success = await self.remove_conversation_tag(conv_id, tag)
                elif action == "mark_read":
                    success = await self.mark_conversation_read(conv_id)
                else:
                    success = False

                results["results"].append({"conversation_id": conv_id, "action": action, "success": success})

                if success:
                    results["success_count"] += 1
                else:
                    results["failure_count"] += 1

            except Exception as e:
                results["results"].append(
                    {"conversation_id": conv_id, "action": action, "success": False, "error": str(e)}
                )
                results["failure_count"] += 1

        return results

    def is_healthy(self) -> bool:
        """
        Check if the Mission Inbox system is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check if core components are initialized
            if not self.events or not self.conversations:
                return False

            # Check if event bus is working
            try:
                self.event_bus.get_history(limit=1)
            except Exception:
                return False

            # Check if AI guidance is working
            try:
                if self.ai_guidance:
                    asyncio.create_task(
                        self.ai_guidance.generate_ai_guidance_response(
                            None,  # type: ignore[arg-type]  # No conversation for test
                            None,  # type: ignore[arg-type]  # No event for test
                            {"role": "test", "experience": "test"},
                        )
                    )
            except Exception:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def cleanup(self) -> None:
        """
        Cleanup resources used by the Mission Inbox.

        This method should be called when the Mission Inbox is no longer needed.
        """
        try:
            # Clear all data structures
            self.events.clear()
            self.conversations.clear()
            self.evidences.clear()
            self.timeline.clear()

            # Unsubscribe from event bus
            self.event_bus.unsubscribe("*", self._handle_event)
            self.event_bus.unsubscribe("mission:ai_guidance_requested", self._handle_ai_guidance_request)

            # Reset AI guidance
            self.ai_guidance = None  # type: ignore[assignment]

            self.logger.info("Mission Inbox cleaned up")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self) -> MissionInbox:
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Async context manager exit"""
        await self.cleanup()


# Global mission inbox instance
_mission_inbox: MissionInbox | None = None


def get_mission_inbox() -> MissionInbox:
    """
    Get the global mission inbox instance.

    Returns:
        The mission inbox instance
    """
    global _mission_inbox
    if _mission_inbox is None:
        _mission_inbox = MissionInbox()
    return _mission_inbox


def create_mission_inbox(config_file: str | None = None) -> MissionInbox:
    """
    Create a new mission inbox instance.

    Args:
        config_file: Optional configuration file

    Returns:
        New mission inbox instance
    """
    return MissionInbox(config_file)
