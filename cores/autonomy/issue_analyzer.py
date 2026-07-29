"""Issue Analyzer — Parse issues, extract bug/feature details, reproduction steps."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.autonomy.repo_analyzer import BrowserResult


@dataclass
class IssueAnalysis:
    """Parsed analysis of an issue."""

    # Basic info
    issue_id: str
    title: str
    body: str
    url: str
    platform: str  # algora, opire, issuehunt, github, gitlab

    # Classification
    issue_type: str  # bug, feature, enhancement, documentation, refactor, security
    severity: str  # critical, high, medium, low, info
    confidence: float  # 0-1

    # Technical details
    affected_files: list[str] = field(default_factory=list)
    affected_functions: list[str] = field(default_factory=list)
    reproduction_steps: list[str] = field(default_factory=list)
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    error_messages: list[str] = field(default_factory=list)
    stack_traces: list[str] = field(default_factory=list)

    # Context
    language: str | None = None
    framework: str | None = None
    dependencies: list[str] = field(default_factory=list)
    related_issues: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    # Bounty specific
    bounty_amount: float | None = None
    bounty_currency: str = "USD"
    difficulty_estimate: str | None = None  # easy, medium, hard
    estimated_hours: float | None = None


class IssueAnalyzer:
    """Analyzes issue content to extract actionable information for fixing."""

    # Keywords for issue type classification
    BUG_KEYWORDS = [
        "bug",
        "error",
        "crash",
        "fail",
        "broken",
        "not working",
        "issue",
        "exception",
        "traceback",
        "segfault",
        "panic",
        "hang",
        "freeze",
        "memory leak",
        "race condition",
        "deadlock",
        "timeout",
        "regression",
        "incorrect",
        "wrong",
        "unexpected",
        "fail",
        "doesn't work",
        "not work",
    ]

    FEATURE_KEYWORDS = [
        "feature",
        "enhancement",
        "add",
        "implement",
        "support",
        "request",
        "new",
        "proposal",
        "rfc",
        "would like",
        "wish",
        "improvement",
        "extend",
        "customize",
        "option",
        "config",
        "setting",
    ]

    SECURITY_KEYWORDS = [
        "security",
        "vulnerability",
        "exploit",
        "xss",
        "csrf",
        "sql injection",
        "rce",
        "auth bypass",
        "privilege escalation",
        "information disclosure",
        "cve",
        "cwe",
        "injection",
        "xss",
        "ssrf",
        "rce",
        "lfi",
        "rfi",
        "path traversal",
        "deserialization",
        "xxe",
        "idor",
        "authentication",
        "authorization",
        "session",
        "token",
        "jwt",
        "oauth",
        "saml",
    ]

    DOC_KEYWORDS = [
        "doc",
        "documentation",
        "readme",
        "guide",
        "tutorial",
        "example",
        "typo",
        "comment",
        "docstring",
        "changelog",
        "api doc",
    ]

    REFACTOR_KEYWORDS = [
        "refactor",
        "cleanup",
        "technical debt",
        "code smell",
        "duplicated",
        "complex",
        "simplify",
        "restructure",
        "modernize",
        "migrate",
        "upgrade",
    ]

    # Severity indicators
    CRITICAL_INDICATORS = [
        "critical",
        "urgent",
        "blocker",
        "production down",
        "data loss",
        "security",
        "vulnerability",
        "exploit",
        "rce",
        "auth bypass",
    ]

    HIGH_INDICATORS = [
        "high",
        "major",
        "important",
        "breaking",
        "regression",
        "crash",
        "data corruption",
        "memory leak",
        "performance degradation",
    ]

    MEDIUM_INDICATORS = [
        "medium",
        "moderate",
        "bug",
        "error",
        "incorrect",
        "wrong",
        "not working",
        "fail",
        "timeout",
        "slow",
    ]

    LOW_INDICATORS = ["low", "minor", "cosmetic", "ui", "typo", "style", "lint", "format"]

    # Difficulty indicators
    EASY_INDICATORS = [
        "easy",
        "simple",
        "trivial",
        "good first issue",
        "beginner",
        "starter",
        "quick fix",
        "one line",
        "typo",
        "documentation",
    ]

    HARD_INDICATORS = [
        "hard",
        "complex",
        "difficult",
        "challenging",
        "expert",
        "architecture",
        "refactor",
        "redesign",
        "migration",
        "performance",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def analyze_issue(
        self,
        issue_data: dict[str, Any],
        repo_info: Any | None = None,
    ) -> BrowserResult:
        """Analyze issue and extract structured information."""
        try:
            # Extract basic info
            analysis = self._extract_basic_info(issue_data)

            # Classify issue type
            analysis.issue_type = self._classify_issue_type(analysis.title, analysis.body)
            analysis.severity = self._classify_severity(analysis.title, analysis.body)
            analysis.difficulty_estimate = self._estimate_difficulty(analysis.title, analysis.body)

            # Extract technical details
            analysis.reproduction_steps = self._extract_reproduction_steps(analysis.body)
            analysis.expected_behavior = self._extract_expected_behavior(analysis.body)
            analysis.actual_behavior = self._extract_actual_behavior(analysis.body)
            analysis.error_messages = self._extract_error_messages(analysis.body)
            analysis.stack_traces = self._extract_stack_traces(analysis.body)

            # Extract code references
            analysis.affected_files = self._extract_file_references(analysis.body)
            analysis.affected_functions = self._extract_function_references(analysis.body)

            # Platform-specific extraction
            self._extract_platform_specific(analysis, issue_data)

            # Estimate hours
            analysis.estimated_hours = self._estimate_hours(analysis)

            # Confidence based on information completeness
            analysis.confidence = self._calculate_confidence(analysis)

            return BrowserResult(
                True, "analyze_issue", analysis.issue_id, "Issue analyzed successfully", data={"analysis": analysis}
            )

        except Exception as e:
            return BrowserResult(False, "analyze_issue", issue_data.get("id", "unknown"), error=f"Analysis failed: {e}")

    def _extract_basic_info(self, issue_data: dict[str, Any]) -> IssueAnalysis:
        """Extract basic issue information."""
        # Handle different platform formats
        if "number" in issue_data:  # GitHub/GitLab
            issue_id = str(issue_data["number"])
        elif "id" in issue_data:  # Algora/Opire/IssueHunt
            issue_id = str(issue_data["id"])
        elif "bounty_id" in issue_data:  # Algora specific
            issue_id = str(issue_data["bounty_id"])
        else:
            issue_id = "unknown"

        title = issue_data.get("title") or issue_data.get("name") or ""
        body = issue_data.get("body") or issue_data.get("description") or issue_data.get("details") or ""
        url = issue_data.get("url") or issue_data.get("html_url") or issue_data.get("issue_url") or ""
        platform = issue_data.get("platform") or issue_data.get("source") or "unknown"

        labels = [
            str(label.get("name") if isinstance(label, dict) else label)
            for label in issue_data.get("labels", [])
            if label
        ]

        return IssueAnalysis(
            issue_id=issue_id,
            title=title,
            body=body,
            url=url,
            platform=platform,
            issue_type="unknown",
            severity="medium",
            confidence=0.5,
            labels=labels,
        )

    def _classify_issue_type(self, title: str, body: str) -> str:
        """Classify issue type from content."""
        text = f"{title} {body}".lower()

        # Check security first (highest priority)
        if any(kw in text for kw in self.SECURITY_KEYWORDS):
            return "security"

        # Check bug
        if any(kw in text for kw in self.BUG_KEYWORDS):
            return "bug"

        # Check feature
        if any(kw in text for kw in self.FEATURE_KEYWORDS):
            return "feature"

        # Check docs
        if any(kw in text for kw in self.DOC_KEYWORDS):
            return "documentation"

        # Check refactor
        if any(kw in text for kw in self.REFACTOR_KEYWORDS):
            return "refactor"

        # Default to bug if unclear
        return "bug"

    def _classify_severity(self, title: str, body: str) -> str:
        """Classify severity from content."""
        text = f"{title} {body}".lower()

        if any(kw in text for kw in self.CRITICAL_INDICATORS):
            return "critical"
        if any(kw in text for kw in self.HIGH_INDICATORS):
            return "high"
        if any(kw in text for kw in self.MEDIUM_INDICATORS):
            return "medium"
        if any(kw in text for kw in self.LOW_INDICATORS):
            return "low"

        return "medium"

    def _estimate_difficulty(self, title: str, body: str) -> str:
        """Estimate difficulty level."""
        text = f"{title} {body}".lower()

        if any(kw in text for kw in self.EASY_INDICATORS):
            return "easy"
        if any(kw in text for kw in self.HARD_INDICATORS):
            return "hard"

        # Heuristic based on content length and complexity
        if len(body) > 2000 or body.count("\n") > 20:
            return "hard"
        if len(body) < 200 and body.count("\n") < 5:
            return "easy"

        return "medium"

    def _extract_reproduction_steps(self, body: str) -> list[str]:
        """Extract reproduction steps from issue body."""
        steps = []

        # Common patterns for reproduction steps
        patterns = [
            r"(?:steps? to reproduce|reproduction steps?|how to reproduce|to reproduce)[:\s]*\n?(.*?)(?:\n\n|\n[A-Z]|\Z)",
            r"(?:repro|reproduce)[:\s]*\n?(.*?)(?:\n\n|\n[A-Z]|\Z)",
            r"(?:1\.\s*.*?\n)(?:2\.\s*.*?\n)(?:3\.\s*.*?\n)?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE | re.DOTALL)
            for match in matches:
                lines = [line.strip() for line in match.split("\n") if line.strip()]
                for line in lines:
                    # Clean up numbering
                    clean = re.sub(r"^\d+[\.\)]\s*", "", line)
                    clean = re.sub(r"^[-*]\s*", "", clean)
                    if clean and len(clean) > 5:
                        steps.append(clean)

        # Deduplicate
        seen = set()
        unique = []
        for step in steps:
            if step not in seen:
                seen.add(step)
                unique.append(step)

        return unique[:10]  # Max 10 steps

    def _extract_expected_behavior(self, body: str) -> str | None:
        """Extract expected behavior."""
        patterns = [
            r"(?:expected|should|expect)[:\s]+(.*?)(?:\n\n|\n[A-Z]|\Z)",
            r"(?:desired behavior|desired outcome)[:\s]+(.*?)(?:\n\n|\n[A-Z]|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        return None

    def _extract_actual_behavior(self, body: str) -> str | None:
        """Extract actual behavior."""
        patterns = [
            r"(?:actual|currently|happens|behavior)[:\s]+(.*?)(?:\n\n|\n[A-Z]|\Z)",
            r"(?:actual behavior|current behavior)[:\s]+(.*?)(?:\n\n|\n[A-Z]|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        return None

    def _extract_error_messages(self, body: str) -> list[str]:
        """Extract error messages."""
        errors = []

        # Pattern for error messages in code blocks or quotes
        patterns = [
            r"```\w*\n(.*?(?:Error|Exception|Error:|Exception:|FAILED|FAIL|Traceback).*?)\n```",
            r"`([^`]*(?:Error|Exception|Error:|Exception:)[^`]*)`",
            r"^.*?(?:Error|Exception|Error:|Exception:).*$",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                clean = match.strip()
                if len(clean) > 10 and len(clean) < 1000:
                    errors.append(clean)

        return errors[:10]

    def _extract_stack_traces(self, body: str) -> list[str]:
        """Extract stack traces."""
        traces = []

        # Stack trace patterns
        patterns = [
            r"```\w*\n(.*?Traceback.*?)\n```",
            r"```\w*\n(.*?at\s+\S+.*?)\n```",
            r"(Traceback \(most recent call last\):.*?)(?:\n\n|\n```|\Z)",
            r"(.*?at\s+\S+\.\w+\s*\(.*?\)\s*\n)+(?:\n|\Z)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean = match.strip()
                if len(clean) > 50:
                    traces.append(clean[:3000])

        return traces[:5]

    def _extract_file_references(self, body: str) -> list[str]:
        """Extract file paths mentioned in issue."""
        files = []

        # File path patterns
        patterns = [
            r"`([^`]+\.(?:py|js|ts|jsx|tsx|go|rs|java|cpp|cc|c|h|hpp|cs|php|rb|swift|kt|scala|rs))`",
            r"([a-zA-Z0-9_\-./]+\.(?:py|js|ts|jsx|tsx|go|rs|java|cpp|cc|c|h|hpp|cs|php|rb|swift|kt|scala))",
            r"(?:file|path)[:\s]+([a-zA-Z0-9_\-./]+\.\w+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                clean = match.strip("`")
                if clean and not clean.startswith("http"):
                    files.append(clean)

        # Deduplicate
        seen = set()
        unique = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique.append(f)

        return unique[:20]

    def _extract_function_references(self, body: str) -> list[str]:
        """Extract function/method names mentioned."""
        functions = []

        # Function patterns
        patterns = [
            r"`(\w+\(\))`",  # func()
            r"function\s+(\w+)",
            r"def\s+(\w+)",
            r"fn\s+(\w+)",
            r"func\s+(\w+)",
            r"method\s+(\w+)",
            r"(\w+)\(\)",  # func() in text
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body)
            functions.extend(matches)

        # Deduplicate
        seen = set()
        unique = []
        for f in functions:
            if f not in seen and len(f) > 2:
                seen.add(f)
                unique.append(f)

        return unique[:20]

    def _extract_platform_specific(self, analysis: IssueAnalysis, issue_data: dict[str, Any]) -> None:
        """Extract platform-specific information."""
        platform = analysis.platform.lower()

        if platform == "algora":
            analysis.bounty_amount = issue_data.get("bounty_amount") or issue_data.get("amount")
            analysis.bounty_currency = issue_data.get("currency", "USD")
            if "repository" in issue_data:
                repo = issue_data["repository"]
                if isinstance(repo, dict):
                    analysis.affected_files.append(repo.get("full_name", ""))

        elif platform == "opire":
            analysis.bounty_amount = issue_data.get("reward") or issue_data.get("bounty")
            analysis.bounty_currency = issue_data.get("currency", "USD")

        elif platform == "issuehunt":
            analysis.bounty_amount = issue_data.get("bounty") or issue_data.get("reward")
            analysis.bounty_currency = "USD"

        elif platform == "github":
            # GitHub issue - check for bounty labels
            for label in analysis.labels:
                if "bounty" in label.lower() or "$" in label:
                    # Try to extract amount
                    amounts = re.findall(r"\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", label)
                    if amounts:
                        analysis.bounty_amount = float(amounts[0].replace(",", ""))

    def _estimate_hours(self, analysis: IssueAnalysis) -> float:
        """Estimate hours to fix."""
        base_hours = {
            "easy": 2.0,
            "medium": 8.0,
            "hard": 24.0,
        }.get(analysis.difficulty_estimate, 8.0)

        # Adjust by issue type
        type_multiplier = {
            "bug": 1.0,
            "feature": 1.5,
            "security": 2.0,
            "documentation": 0.3,
            "refactor": 1.2,
        }.get(analysis.issue_type, 1.0)

        # Adjust by severity
        severity_multiplier = {
            "critical": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8,
        }.get(analysis.severity, 1.0)

        return round(base_hours * type_multiplier * severity_multiplier, 1)

    def _calculate_confidence(self, analysis: IssueAnalysis) -> float:
        """Calculate confidence in analysis (0-1)."""
        score = 0.3  # Base

        if analysis.title and len(analysis.title) > 5:
            score += 0.1
        if analysis.body and len(analysis.body) > 50:
            score += 0.15
        if analysis.reproduction_steps:
            score += 0.15
        if analysis.error_messages:
            score += 0.1
        if analysis.stack_traces:
            score += 0.1
        if analysis.affected_files:
            score += 0.1
        if analysis.expected_behavior:
            score += 0.05
        if analysis.actual_behavior:
            score += 0.05

        return min(score, 1.0)
