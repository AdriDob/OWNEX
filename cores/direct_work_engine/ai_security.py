"""AI Security Engine — Detects AI-specific vulnerabilities and security issues.

This module provides detection capabilities for AI-specific vulnerability classes
including prompt injection, tool poisoning, MCP attacks, RAG attacks, and more.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.direct_work.ai_security")


class AIVulnerabilityType(Enum):
    """Categories of AI-specific vulnerabilities."""

    PROMPT_INJECTION = "prompt_injection"
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    TOOL_POISONING = "tool_poisoning"
    MCP_ATTACK = "mcp_attack"
    RAG_ATTACK = "rag_attack"
    AGENT_SECURITY = "agent_security"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MEMORY_POISONING = "memory_poisoning"
    AGENT_TO_AGENT_ATTACK = "agent_to_agent_attack"
    PROMPT_LEAKAGE = "prompt_leakage"
    JAILBREAK = "jailbreak"
    MODEL_ABUSE = "model_abuse"
    SAFETY_BYPASS = "safety_bypass"
    AUTHORIZATION_BYPASS = "authorization_bypass"


class AISeverity(Enum):
    """Severity levels for AI vulnerabilities."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AIVulnerability:
    """Represents a detected AI vulnerability."""

    vuln_type: AIVulnerabilityType
    severity: AISeverity
    title: str
    description: str
    evidence: list[str] = field(default_factory=list)
    affected_component: str = ""
    attack_vector: str = ""
    impact: str = ""
    remediation: str = ""
    confidence: float = 0.0
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIFinding:
    """Result of an AI security scan."""

    target: str
    scan_type: str
    vulnerabilities: list[AIVulnerability] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    scanned_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Prompt Injection Detection Patterns
PROMPT_INJECTION_PATTERNS = [
    # Direct prompt injection
    r"(?i)ignore\s+(?:previous|all|above)\s+(?:instructions?|prompts?|rules?)",
    r"(?i)forget\s+(?:everything|all|previous)\s+(?:you\s+)?(?:know|learned|were\s+told)",
    r"(?i)you\s+are\s+now\s+(?:a|an)\s+\w+",
    r"(?i)pretend\s+(?:to\s+be|you\s+are)\s+\w+",
    r"(?i)roleplay\s+(?:as|you\s+are)\s+\w+",
    r"(?i)act\s+as\s+(?:if\s+you\s+are\s+)?\w+",
    r"(?i)simulate\s+(?:being\s+)?\w+",
    r"(?i)disregard\s+(?:previous|all)\s+(?:instructions?|prompts?)",
    r"(?i)override\s+(?:previous|all)\s+(?:instructions?|prompts?)",
    r"(?i)system\s*:\s*",
    r"(?i)user\s*:\s*",
    r"(?i)assistant\s*:\s*",
    # Jailbreak attempts
    r"(?i)developer\s+mode",
    r"(?i)do\s+anything\s+now",
    r"(?i)dan\s+mode",
    r"(?i)unrestricted\s+mode",
    # Indirect injection markers
    r"(?i)<!--\s*injection",
    r"(?i)\[INJECT",
    r"(?i)DATA_EXFILTRATION",
]

# Tool Poisoning Patterns
TOOL_POISONING_PATTERNS = [
    r"(?i)tool\s+(?:name|definition)\s*[:=]\s*[\"']?\s*[^\"']*inject",
    r"(?i)function\s+(?:call|definition)\s*[:=]\s*[^\"']*malicious",
    r"(?i)parameters?\s*[:=]\s*[^\"']*\$\{.*\}",
    r"(?i)exec\s*\(|eval\s*\(|system\s*\(",
    r"(?i)__import__\s*\(|subprocess\s*\.",
    r"(?i)os\s*\.\s*system|os\s*\.\s*popen",
]

# MCP Attack Patterns
MCP_ATTACK_PATTERNS = [
    r"(?i)mcp\s+(?:server|client|tool)",
    r"(?i)model\s+context\s+protocol",
    r"(?i)tool\s+poisoning",
    r"(?i)resource\s+poisoning",
    r"(?i)prompt\s+template\s+injection",
]

# RAG Attack Patterns
RAG_ATTACK_PATTERNS = [
    r"(?i)retrieval\s+augmented\s+generation",
    r"(?i)knowledge\s+base\s+injection",
    r"(?i)document\s+injection",
    r"(?i)embedding\s+injection",
    r"(?i)vector\s+store\s+poisoning",
]

# Agent Security Patterns
AGENT_SECURITY_PATTERNS = [
    r"(?i)agent\s+(?:to\s+agent|communication|coordination)",
    r"(?i)multi\s*[- ]?agent",
    r"(?i)autonomous\s+agent",
    r"(?i)agent\s+memory\s+(?:poisoning|manipulation)",
    r"(?i)tool\s+use\s+(?:abuse|injection)",
]

# Privilege Escalation Patterns
PRIVILEGE_ESCALATION_PATTERNS = [
    r"(?i)admin\s+(?:access|panel|mode|privileges?)",
    r"(?i)root\s+(?:access|shell|privileges?)",
    r"(?i)sudo\s+",
    r"(?i)escalate\s+(?:privileges?|access)",
    r"(?i)bypass\s+(?:auth|authorization|authentication)",
    r"(?i)impersonat(?:e|ion)",
    r"(?i)token\s+(?:theft|steal|reuse|replay)",
]

# Data Exfiltration Patterns
DATA_EXFILTRATION_PATTERNS = [
    r"(?i)exfiltrat(?:e|ion)",
    r"(?i)steal\s+(?:data|credentials?|tokens?|keys?)",
    r"(?i)leak\s+(?:data|info|secrets?)",
    r"(?i)dump\s+(?:database|memory|credentials?)",
    r"(?i)export\s+(?:all|data|users?)",
]

# Prompt Leakage Patterns
PROMPT_LEAKAGE_PATTERNS = [
    r"(?i)what\s+(?:is|are)\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"(?i)show\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?prompt",
    r"(?i)repeat\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"(?i)output\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"(?i)reveal\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"(?i)print\s+(?:your|the)\s+(?:system\s+)?prompt",
]

# Jailbreak Patterns
JAILBREAK_PATTERNS = [
    r"(?i)ignore\s+all\s+(?:rules|guidelines|restrictions|constraints)",
    r"(?i)you\s+(?:have\s+)?no\s+(?:rules|restrictions|limitations?)",
    r"(?i)free\s+(?:mode|version|access)",
    r"(?i)unrestricted",
    r"(?i)no\s+ethical\s+(?:guidelines?|constraints?)",
    r"(?i)harmful\s+(?:content|output|response)",
]


# Compile all patterns for efficiency
ALL_PATTERNS = {
    AIVulnerabilityType.PROMPT_INJECTION: [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS],
    AIVulnerabilityType.TOOL_POISONING: [re.compile(p, re.IGNORECASE) for p in TOOL_POISONING_PATTERNS],
    AIVulnerabilityType.MCP_ATTACK: [re.compile(p, re.IGNORECASE) for p in MCP_ATTACK_PATTERNS],
    AIVulnerabilityType.RAG_ATTACK: [re.compile(p, re.IGNORECASE) for p in RAG_ATTACK_PATTERNS],
    AIVulnerabilityType.AGENT_SECURITY: [re.compile(p, re.IGNORECASE) for p in AGENT_SECURITY_PATTERNS],
    AIVulnerabilityType.PRIVILEGE_ESCALATION: [re.compile(p, re.IGNORECASE) for p in PRIVILEGE_ESCALATION_PATTERNS],
    AIVulnerabilityType.DATA_EXFILTRATION: [re.compile(p, re.IGNORECASE) for p in DATA_EXFILTRATION_PATTERNS],
    AIVulnerabilityType.PROMPT_LEAKAGE: [re.compile(p, re.IGNORECASE) for p in PROMPT_LEAKAGE_PATTERNS],
    AIVulnerabilityType.JAILBREAK: [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS],
    AIVulnerabilityType.INDIRECT_PROMPT_INJECTION: [
        re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS[-4:]
    ],
    AIVulnerabilityType.AUTHORIZATION_BYPASS: [re.compile(p, re.IGNORECASE) for p in PRIVILEGE_ESCALATION_PATTERNS],
    AIVulnerabilityType.MODEL_ABUSE: [],
    AIVulnerabilityType.SAFETY_BYPASS: [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS],
    AIVulnerabilityType.DATA_EXFILTRATION: [re.compile(p, re.IGNORECASE) for p in DATA_EXFILTRATION_PATTERNS],
    AIVulnerabilityType.MEMORY_POISONING: [re.compile(p, re.IGNORECASE) for p in AGENT_SECURITY_PATTERNS],
    AIVulnerabilityType.AGENT_TO_AGENT_ATTACK: [re.compile(p, re.IGNORECASE) for p in AGENT_SECURITY_PATTERNS],
}


class AISecurityScanner:
    """Scans inputs, outputs, and system interactions for AI-specific vulnerabilities."""

    def __init__(self, custom_patterns: dict[AIVulnerabilityType, list[re.Pattern]] | None = None):
        self.patterns = ALL_PATTERNS.copy()
        if custom_patterns:
            for vuln_type, patterns in custom_patterns.items():
                self.patterns[vuln_type].extend(patterns)

    def scan_text(self, text: str, context: str = "") -> list[AIVulnerability]:
        """Scan text for AI vulnerability patterns."""
        vulnerabilities = []

        for vuln_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    vuln = AIVulnerability(
                        vuln_type=vuln_type,
                        severity=self._assess_severity(vuln_type, len(matches)),
                        title=f"{vuln_type.value.replace('_', ' ').title()} Detected",
                        description=f"Pattern matching {vuln_type.value} found in {context or 'input'}",
                        evidence=[str(m) for m in matches[:5]],  # Limit evidence
                        affected_component=context,
                        attack_vector=vuln_type.value,
                        impact=self._assess_impact(vuln_type),
                        remediation=self._get_remediation(vuln_type),
                        confidence=min(0.5 + (len(matches) * 0.1), 0.95),
                        metadata={"match_count": len(matches), "context": context},
                    )
                    vulnerabilities.append(vuln)

        return vulnerabilities

    def scan_conversation(self, messages: list[dict[str, Any]]) -> list[AIVulnerability]:
        """Scan a conversation for AI vulnerabilities."""
        all_vulns = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                vulns = self.scan_text(content, f"{role} message")
                all_vulns.extend(vulns)

        return all_vulns

    def scan_agent_interaction(
        self,
        agent_input: str,
        agent_output: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> AIFinding:
        """Comprehensive scan of an agent interaction."""
        import time
        from datetime import datetime

        start_time = time.time()
        vulnerabilities = []

        # Scan input
        vulns = self.scan_text(agent_input, "agent input")
        vulnerabilities.extend(vulns)

        # Scan output
        vulns = self.scan_text(agent_output, "agent output")
        vulnerabilities.extend(vulns)

        # Scan tool calls
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.get("name", "unknown")
                tool_args = str(tc.get("arguments", ""))
                vulns = self.scan_text(f"Tool: {tool_name}\nArgs: {tool_args}", f"tool call: {tool_name}")
                vulnerabilities.extend(vulns)

        # Scan tool results
        if tool_results:
            for tr in tool_results:
                result_content = str(tr.get("result", ""))
                vulns = self.scan_text(result_content, "tool result")
                vulnerabilities.extend(vulns)

        scan_duration = (time.time() - start_time) * 1000

        return AIFinding(
            target="agent_interaction",
            scan_type="comprehensive",
            vulnerabilities=vulnerabilities,
            scan_duration_ms=scan_duration,
            scanned_at=datetime.now().isoformat(),
            metadata={
                "input_length": len(agent_input),
                "output_length": len(agent_output),
                "tool_calls_count": len(tool_calls) if tool_calls else 0,
            },
        )

    def _assess_severity(self, vuln_type: AIVulnerabilityType, match_count: int) -> AISeverity:
        """Assess severity based on vulnerability type and match count."""
        critical_types = {
            AIVulnerabilityType.PROMPT_INJECTION,
            AIVulnerabilityType.TOOL_POISONING,
            AIVulnerabilityType.MCP_ATTACK,
            AIVulnerabilityType.PRIVILEGE_ESCALATION,
            AIVulnerabilityType.DATA_EXFILTRATION,
            AIVulnerabilityType.AUTHORIZATION_BYPASS,
        }

        high_types = {
            AIVulnerabilityType.JAILBREAK,
            AIVulnerabilityType.PROMPT_LEAKAGE,
            AIVulnerabilityType.INDIRECT_PROMPT_INJECTION,
            AIVulnerabilityType.RAG_ATTACK,
            AIVulnerabilityType.AGENT_SECURITY,
            AIVulnerabilityType.AGENT_TO_AGENT_ATTACK,
            AIVulnerabilityType.MEMORY_POISONING,
        }

        if vuln_type in critical_types:
            return AISeverity.CRITICAL if match_count > 1 else AISeverity.HIGH
        elif vuln_type in high_types:
            return AISeverity.HIGH if match_count > 1 else AISeverity.MEDIUM
        else:
            return AISeverity.MEDIUM if match_count > 1 else AISeverity.LOW

    def _assess_impact(self, vuln_type: AIVulnerabilityType) -> str:
        """Assess potential impact of vulnerability."""
        impacts = {
            AIVulnerabilityType.PROMPT_INJECTION: "Full control over model behavior, potential data exfiltration",
            AIVulnerabilityType.INDIRECT_PROMPT_INJECTION: "Covert manipulation via external data sources",
            AIVulnerabilityType.TOOL_POISONING: "Arbitrary code execution via tool manipulation",
            AIVulnerabilityType.MCP_ATTACK: "Compromise of model context protocol, tool chain compromise",
            AIVulnerabilityType.RAG_ATTACK: "Poisoned knowledge base, corrupted retrievals",
            AIVulnerabilityType.AGENT_SECURITY: "Autonomous agent compromise, unauthorized actions",
            AIVulnerabilityType.PRIVILEGE_ESCALATION: "Unauthorized elevation of permissions",
            AIVulnerabilityType.DATA_EXFILTRATION: "Theft of sensitive data, credentials, PII",
            AIVulnerabilityType.MEMORY_POISONING: "Persistent agent memory corruption",
            AIVulnerabilityType.AGENT_TO_AGENT_ATTACK: "Cross-agent contamination, cascade failures",
            AIVulnerabilityType.PROMPT_LEAKAGE: "Exposure of system prompts, intellectual property",
            AIVulnerabilityType.JAILBREAK: "Complete bypass of safety controls",
            AIVulnerabilityType.MODEL_ABUSE: "Unauthorized use of model capabilities",
            AIVulnerabilityType.SAFETY_BYPASS: "Circumvention of safety guardrails",
            AIVulnerabilityType.AUTHORIZATION_BYPASS: "Unauthorized access to restricted functions",
            AIVulnerabilityType.TOOL_POISONING: "Malicious tool definitions leading to arbitrary actions",
            AIVulnerabilityType.MCP_ATTACK: "Model Context Protocol compromise",
            AIVulnerabilityType.RAG_ATTACK: "Retrieval-Augmented Generation poisoning",
        }
        return impacts.get(vuln_type, "Potential security impact")

    def _get_remediation(self, vuln_type: AIVulnerabilityType) -> str:
        """Get remediation guidance for vulnerability type."""
        remediations = {
            AIVulnerabilityType.PROMPT_INJECTION: "Implement input validation, use prompt templates, sanitize user input",
            AIVulnerabilityType.INDIRECT_PROMPT_INJECTION: "Validate and sanitize external data sources, use content security policies",
            AIVulnerabilityType.TOOL_POISONING: "Validate tool definitions, use allowlists, sandbox tool execution",
            AIVulnerabilityType.MCP_ATTACK: "Validate MCP server authenticity, verify tool definitions, monitor tool calls",
            AIVulnerabilityType.RAG_ATTACK: "Validate document sources, monitor embedding quality, implement content filtering",
            AIVulnerabilityType.AGENT_SECURITY: "Implement agent isolation, monitor inter-agent communication, audit tool usage",
            AIVulnerabilityType.PRIVILEGE_ESCALATION: "Enforce least privilege, validate authorization on every action",
            AIVulnerabilityType.DATA_EXFILTRATION: "Implement data loss prevention, monitor data access patterns",
            AIVulnerabilityType.MEMORY_POISONING: "Implement memory validation, regular memory audits, versioned memory",
            AIVulnerabilityType.AGENT_TO_AGENT_ATTACK: "Isolate agent communications, validate message authenticity",
            AIVulnerabilityType.PROMPT_LEAKAGE: "Never include sensitive info in prompts, use prompt templates",
            AIVulnerabilityType.JAILBREAK: "Implement robust guardrails, use constitutional AI, regular red-teaming",
            AIVulnerabilityType.INDIRECT_PROMPT_INJECTION: "Sanitize external inputs, validate data provenance",
            AIVulnerabilityType.AUTHORIZATION_BYPASS: "Enforce RBAC, validate permissions on every request",
            AIVulnerabilityType.MODEL_ABUSE: "Implement rate limiting, usage monitoring, content filtering",
            AIVulnerabilityType.SAFETY_BYPASS: "Multi-layer safety controls, constitutional AI, regular audits",
            AIVulnerabilityType.AUTHORIZATION_BYPASS: "Zero-trust architecture, continuous authorization validation",
            AIVulnerabilityType.TOOL_POISONING: "Tool definition validation, execution sandboxing",
            AIVulnerabilityType.MCP_ATTACK: "MCP server verification, tool definition integrity checks",
            AIVulnerabilityType.RAG_ATTACK: "Source validation, embedding monitoring, retrieval filtering",
        }
        return remediations.get(vuln_type, "Implement appropriate security controls")


# Convenience function for quick scanning
def quick_scan(text: str, context: str = "") -> list[AIVulnerability]:
    """Quick scan for AI vulnerabilities in text."""
    scanner = AISecurityScanner()
    return scanner.scan_text(text, context)


# Integration with existing validation system
class AISecurityValidator:
    """Integrates AI security scanning with the existing validation pipeline."""

    def __init__(self):
        self.scanner = AISecurityScanner()

    def validate_finding_report(self, finding_data: dict[str, Any]) -> list[AIVulnerability]:
        """Validate a bug bounty finding report for AI security issues."""
        vulnerabilities = []

        # Scan the finding description
        description = finding_data.get("description", "")
        if description:
            vulns = self.scanner.scan_text(description, "finding description")
            vulnerabilities.extend(vulns)

        # Scan PoC code if present
        poc = finding_data.get("poc", finding_data.get("proof_of_concept", ""))
        if poc:
            vulns = self.scanner.scan_text(poc, "PoC code")
            vulnerabilities.extend(vulns)

        # Scan steps to reproduce
        steps = finding_data.get("steps_to_reproduce", finding_data.get("reproduction_steps", ""))
        if steps:
            vulns = self.scanner.scan_text(str(steps), "reproduction steps")
            vulnerabilities.extend(vulns)

        return vulnerabilities

    def validate_agent_work(self, work_data: dict[str, Any]) -> AIFinding:
        """Validate agent-performed work for AI security issues."""
        return self.scanner.scan_agent_interaction(
            agent_input=work_data.get("input", ""),
            agent_output=work_data.get("output", ""),
            tool_calls=work_data.get("tool_calls"),
            tool_results=work_data.get("tool_results"),
        )


# Export main classes
__all__ = [
    "AIVulnerabilityType",
    "AISeverity",
    "AIVulnerability",
    "AIFinding",
    "AISecurityScanner",
    "AISecurityValidator",
    "quick_scan",
    "ALL_PATTERNS",
    "PROMPT_INJECTION_PATTERNS",
    "TOOL_POISONING_PATTERNS",
    "MCP_ATTACK_PATTERNS",
    "RAG_ATTACK_PATTERNS",
    "AGENT_SECURITY_PATTERNS",
    "PRIVILEGE_ESCALATION_PATTERNS",
    "DATA_EXFILTRATION_PATTERNS",
    "PROMPT_LEAKAGE_PATTERNS",
    "JAILBREAK_PATTERNS",
]
