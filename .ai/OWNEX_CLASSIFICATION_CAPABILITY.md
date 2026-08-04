# Classification Engine + Capability Engine

> FASE 7 del plan OWNEX v6
> Fecha: 2026-07-29

---

## 1. Classification Engine

La observación normalizada llega y el clasificador decide: **¿es oportunidad o ruido?**

### Árbol de decisión

```
Observation → ClassificationEngine
         │
         ├── ¿Tiene reward? NO → NOISE (descartar)
         │
         ├── ¿Tiene scope/url? NO → NOISE
         │
         ├── ¿Es actionable? NO → NOISE
         │
         ├── ¿Ya la vimos? SÍ → DUPLICATE
         │
         └── SÍ → ¿Qué tipo?
              │
              ├── bug_bounty  → cycle: "security",  source_type: "bug_bounty"
              ├── dev_bounty  → cycle: "forge",     source_type: "dev_bounty"
              ├── ai_work     → cycle: "pulse",     source_type: "ai_work"
              ├── freelance   → cycle: "forge",     source_type: "freelance"
              ├── investment  → cycle: "vault",     source_type: "investment"
              ├── intelligence→ cycle: "atlas",     source_type: "intel"
              └── unknown     → cycle: "atlas",     source_type: "unknown"
```

### Clasificación por capas

```
Layer 1: REGLAS (rápido, 90% de casos)
  - regex patterns en título/descripción
  - source_type ya definido por el sensor
  - tags conocidos → mapeo directo a ciclo

Layer 2: HEURÍSTICAS (medio, 9% de casos)
  - reward > X y effort < Y → alta prioridad
  - plataforma conocida → pattern match
  - frecuencia de cambio (nuevo vs actualizado)

Layer 3: LLM (lento, 1% de casos)
  - descripciones ambiguas
  - nuevas plataformas no catalogadas
  - observaciones con bajo confidence (< 0.5)
```

### Interfaz

```python
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClassificationResult:
    """Result of classifying an observation."""

    opportunity_id: str | None  # None if noise
    is_opportunity: bool
    cycle: str | None  # "security", "forge", "pulse", "vault", "atlas"
    source_type: str | None  # "bug_bounty", "dev_bounty", "ai_work", etc.
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    layer: str = "rules"  # "rules", "heuristics", "llm"


class Classifier(ABC):
    """A classifier decides if an observation is an opportunity."""

    @abstractmethod
    async def classify(self, observation: Observation) -> ClassificationResult:
        pass


# ── Rule-based classifiers (Layer 1) ─────────────────────────────────────


class SourceTypeClassifier(Classifier):
    """Classifies based on the sensor's source_type.

    If the sensor already tagged it as "bug_bounty", the classifier
    just confirms it. This is the fastest path.
    """

    SOURCE_TYPE_MAP = {
        "bug_bounty": "security",
        "dev_bounty": "forge",
        "ai_work": "pulse",
        "microtask": "pulse",
        "freelance": "forge",
        "oss_sponsor": "forge",
        "job_application": "pulse",
        "investment": "vault",
        "intel": "atlas",
    }

    async def classify(self, observation: Observation) -> ClassificationResult:
        source_type = observation.source_type
        cycle = self.SOURCE_TYPE_MAP.get(source_type)

        if cycle:
            return ClassificationResult(
                is_opportunity=True,
                cycle=cycle,
                source_type=source_type,
                confidence=0.9,
                reason=f"Source type {source_type} → cycle {cycle}",
                layer="rules",
            )
        return ClassificationResult(
            is_opportunity=False,
            reason=f"Unknown source type: {source_type}",
            layer="rules",
        )


class RewardClassifier(Classifier):
    """Classifies based on reward presence and magnitude."""

    MIN_REWARD_THRESHOLD = 5.0  # $5 minimum to be an opportunity

    async def classify(self, observation: Observation) -> ClassificationResult:
        if observation.estimated_reward_max < self.MIN_REWARD_THRESHOLD:
            return ClassificationResult(
                is_opportunity=False,
                reason=f"Reward ${observation.estimated_reward_max:.2f} below threshold ${self.MIN_REWARD_THRESHOLD:.2f}",
                layer="rules",
            )

        # Has reward → opportunity, but need more info for cycle
        return ClassificationResult(
            is_opportunity=True,
            confidence=0.6,
            reason="Has reward above threshold",
            layer="rules",
        )


class PatternClassifier(Classifier):
    """Classifies by regex patterns in title/description/tags.

    "xss", "sql injection", "bug bounty" → security
    "bounty", "issue hunt", "algora"   → forge
    "ai training", "data labeling"     → pulse
    "investment", "defi", "nft"        → vault
    """

    PATTERNS: dict[str, list[str]] = {
        "security": [
            r"\b(bug\s*bounty|bbp|vdp)\b",
            r"\b(xss|csrf|ssrf|sqli|rce|lfi|idor)\b",
            r"\b(vulnerability|exploit|cve|pentest)\b",
            r"\b(hackerone|bugcrowd|intigriti|immunefi|yeswehack)\b",
        ],
        "forge": [
            r"\b(bounty|bounties)\b",
            r"\b(issue\s*hunt|algora|opire|superteam)\b",
            r"\b(gitcoin|bountysource)\b",
            r"\b(sponsor|funding|grant)\b",
        ],
        "pulse": [
            r"\b(ai\s*train|data\s*label|data\s*annot)\b",
            r"\b(microtask|micro.task)\b",
            r"\b(outlier|mindrift|remotask)\b",
            r"\b(hourly\s*rate|per\s*hour)\b",
        ],
        "vault": [
            r"\b(invest|trading|defi|yield)\b",
            r"\b(audit|smart\s*contract)\b",
        ],
    }

    async def classify(self, observation: Observation) -> ClassificationResult:
        text = f"{observation.title} {observation.description} {' '.join(observation.tags)}".lower()

        scores = {}
        for cycle, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                score += len(matches)
            if score > 0:
                scores[cycle] = score

        if not scores:
            return ClassificationResult(
                is_opportunity=False,
                reason="No pattern matched title/description/tags",
                layer="rules",
            )

        best_cycle = max(scores, key=scores.get)
        return ClassificationResult(
            is_opportunity=True,
            cycle=best_cycle,
            source_type="unknown",
            tags=observation.tags,
            confidence=min(0.5 + scores[best_cycle] * 0.1, 0.95),
            reason=f"Pattern match: {best_cycle} ({scores[best_cycle]} hits)",
            layer="rules",
        )


class CompositeClassifier(Classifier):
    """Runs classifiers in order, stops when confident enough.

    Fast path: rules (Layer 1, <1ms, 90% of cases)
    Medium path: heuristics (Layer 2, <100ms, 9% of cases)
    Slow path: LLM (Layer 3, >1s, 1% of cases)
    """

    def __init__(self):
        self.rules: list[Classifier] = [
            SourceTypeClassifier(),
            RewardClassifier(),
            PatternClassifier(),
        ]
        self.heuristics: list[Classifier] = []
        self.llm: Classifier | None = None

    async def classify(self, observation: Observation) -> ClassificationResult:
        # Layer 1: Rules
        for classifier in self.rules:
            result = await classifier.classify(observation)
            if result.is_opportunity and result.confidence >= 0.8:
                return result
            if not result.is_opportunity and result.confidence >= 0.9:
                return result

        # Layer 2: Heuristics
        for classifier in self.heuristics:
            result = await classifier.classify(observation)
            if result.is_opportunity and result.confidence >= 0.7:
                return result

        # Layer 3: LLM
        if self.llm:
            result = await self.llm.classify(observation)
            return result

        # Fallback: noise
        return ClassificationResult(
            is_opportunity=False,
            reason="All classifiers failed to reach confidence threshold",
            layer="rules",
        )


# ── Classification Engine ────────────────────────────────────────────────


class ClassificationEngine:
    """Orchestrates classification of observations.

    Observation → ClassificationResult → ScoredOpportunity | discarding
    """

    def __init__(self):
        self.classifier = CompositeClassifier()
        self.event_bus = None

    async def classify(self, observation: Observation) -> ScoredOpportunity | None:
        """Classify a single observation.

        Returns ScoredOpportunity if it's an opportunity, None if noise.
        Emits events for both cases.
        """
        result = await self.classifier.classify(observation)

        if not result.is_opportunity:
            await self._emit(
                "observation:discarded",
                {
                    "observation_id": observation.id,
                    "reason": result.reason,
                    "layer": result.layer,
                },
            )
            return None

        # Create ScoredOpportunity
        opportunity = ScoredOpportunity(
            id=observation.id,
            name=observation.title,
            description=observation.description,
            url=observation.url,
            cycle=result.cycle or "atlas",
            source_type=result.source_type or "unknown",
            source_name=observation.sensor_id,
            tags=result.tags or observation.tags,
            estimated_reward_min=observation.estimated_reward_min,
            estimated_reward_max=observation.estimated_reward_max,
            estimated_effort_hours=observation.estimated_effort_hours,
            confidence=result.confidence,
            raw_data=observation.raw_data,
        )

        await self._emit(
            "opportunity:created",
            {
                "opportunity_id": opportunity.id,
                "cycle": opportunity.cycle,
                "source_type": opportunity.source_type,
            },
        )

        return opportunity

    async def _emit(self, event: str, data: dict):
        if self.event_bus:
            await self.event_bus.emit(event, data)
```

---

## 2. Capability Engine

OWNEX necesita saber **qué sabe hacer**. No "qué modelos tiene". **Qué capacidades posee**.

### Catálogo de Capacidades

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    """A capability is something OWNEX can do.

    Not a tool. A capability.
    Tools implement capabilities.
    """

    id: str  # "web_scraping", "code_execution", "git_ops"
    name: str  # "Web Scraping"
    description: str
    category: str  # "data_collection", "analysis", "execution"

    # Tools that provide this capability
    providers: list[str] = field(default_factory=list)

    # Models that are good at this
    preferred_models: list[str] = field(default_factory=list)

    # Required credentials
    required_credentials: list[str] = field(default_factory=list)

    # Cost estimation
    estimated_cost_per_run: float = 0.0
    estimated_time_per_run: int = 60  # seconds

    # Availability
    available: bool = True
    requires_user: bool = False  # needs user approval
```

### Capacidades Iniciales

```python
# Built-in capabilities (concrete from existing code)
CAPABILITIES = {
    "web_scraping": Capability(
        id="web_scraping",
        name="Web Scraping",
        description="Fetch and parse web pages, APIs, RSS feeds",
        category="data_collection",
        providers=["httpx", "urllib", "playwright", "feedparser"],
        estimated_cost_per_run=0.001,
    ),
    "code_execution": Capability(
        id="code_execution",
        name="Code Execution",
        description="Execute Python, Node.js, shell scripts",
        category="execution",
        providers=["pipeline_engine", "agent_registry"],
        estimated_cost_per_run=0.01,
    ),
    "git_operations": Capability(
        id="git_operations",
        name="Git Operations",
        description="Clone, pull, commit, push, create PR",
        category="execution",
        providers=["shell"],
        estimated_cost_per_run=0.001,
    ),
    "browser_automation": Capability(
        id="browser_automation",
        name="Browser Automation",
        description="Control browser for JS-heavy sites, form filling, screenshots",
        category="data_collection",
        providers=["playwright"],
        estimated_cost_per_run=0.01,
        estimated_time_per_run=300,
    ),
    "llm_reasoning": Capability(
        id="llm_reasoning",
        name="LLM Reasoning",
        description="Use AI models for analysis, planning, classification, generation",
        category="analysis",
        providers=["provider_router"],
        estimated_cost_per_run=0.02,
    ),
    "document_parsing": Capability(
        id="document_parsing",
        name="Document Parsing",
        description="Parse PDF, DOCX, HTML, Markdown, JSON, YAML",
        category="data_collection",
        providers=["pymupdf", "python-docx", "beautifulsoup4"],
        estimated_cost_per_run=0.001,
    ),
    "api_interaction": Capability(
        id="api_interaction",
        name="API Interaction",
        description="Call REST APIs, handle auth, pagination, rate limiting",
        category="data_collection",
        providers=["httpx"],
        estimated_cost_per_run=0.001,
    ),
    "network_scanning": Capability(
        id="network_scanning",
        name="Network Scanning",
        description="Port scanning, subdomain discovery, technology fingerprinting",
        category="analysis",
        providers=["nmap", "nuclei", "httpx_tools"],
        requires_user=True,
        estimated_cost_per_run=0.05,
    ),
    "ocr": Capability(
        id="ocr",
        name="OCR",
        description="Extract text from images, screenshots, scanned documents",
        category="data_collection",
        providers=["tesseract"],
        estimated_cost_per_run=0.01,
    ),
    "automation_scripting": Capability(
        id="automation_scripting",
        name="Automation Scripting",
        description="Write and execute automation scripts in bash, Python",
        category="execution",
        providers=["pipeline_engine"],
        estimated_cost_per_run=0.001,
    ),
}
```

### Capability Engine

```python
class CapabilityEngine:
    """Matches opportunity requirements to OWNEX capabilities.

    The Planner asks: "What do I need to execute this opportunity?"
    CapabilityEngine answers: "These 3 capabilities, available via these providers."
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._register_builtin()

    def _register_builtin(self):
        for cap in CAPABILITIES.values():
            self._capabilities[cap.id] = cap

    def register(self, capability: Capability):
        """Register a new capability."""
        self._capabilities[capability.id] = capability

    def get(self, capability_id: str) -> Capability | None:
        return self._capabilities.get(capability_id)

    def list_all(self) -> dict[str, Capability]:
        return dict(self._capabilities)

    def list_by_category(self, category: str) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.category == category]

    def match_opportunity(
        self,
        opportunity: ScoredOpportunity,
        source_type: str | None = None,
    ) -> list[Capability]:
        """Match opportunity requirements to capabilities.

        Different opportunity types need different capabilities:
        - bug_bounty: web_scraping, network_scanning, api_interaction, llm_reasoning
        - dev_bounty: git_operations, code_execution, api_interaction
        - ai_work: code_execution, document_parsing, llm_reasoning
        - freelance: varies widely
        """
        type_requirements = {
            "bug_bounty": ["web_scraping", "api_interaction", "network_scanning", "llm_reasoning", "git_operations"],
            "dev_bounty": ["git_operations", "code_execution", "api_interaction"],
            "ai_work": ["code_execution", "document_parsing", "llm_reasoning"],
            "microtask": ["browser_automation", "automation_scripting"],
            "freelance": ["all"],  # needs all available
            "oss_sponsor": ["git_operations", "code_execution"],
            "job_application": ["browser_automation", "document_parsing"],
        }

        source = source_type or opportunity.source_type
        required = type_requirements.get(source, ["llm_reasoning"])

        if "all" in required:
            return list(self._capabilities.values())

        return [self._capabilities[r] for r in required if r in self._capabilities]

    def can_execute(self, opportunity: ScoredOpportunity) -> tuple[bool, list[str]]:
        """Check if OWNEX has all capabilities for this opportunity.

        Returns (can_execute, missing_capabilities)
        """
        required = self.match_opportunity(opportunity)
        missing = []
        for cap in required:
            if not cap.available:
                missing.append(cap.id)
        return len(missing) == 0, missing

    def estimate_cost(self, opportunity: ScoredOpportunity) -> float:
        """Estimate cost to execute this opportunity."""
        required = self.match_opportunity(opportunity)
        return sum(c.estimated_cost_per_run for c in required)

    def get_statistics(self) -> dict[str, Any]:
        """Get capability engine statistics."""
        categories = {}
        for cap in self._capabilities.values():
            categories.setdefault(cap.category, [])
            categories[cap.category].append(cap.id)

        return {
            "total_capabilities": len(self._capabilities),
            "available": sum(1 for c in self._capabilities.values() if c.available),
            "requires_user": sum(1 for c in self._capabilities.values() if c.requires_user),
            "by_category": categories,
        }
```

### Integración: Classifier + Capability → Opportunity

```python
# Wiring example:


async def process_observation(obs: Observation) -> ScoredOpportunity | None:
    # 1. Classify
    opportunity = await classification_engine.classify(obs)
    if not opportunity:
        return None

    # 2. Check capabilities
    can_do, missing = capability_engine.can_execute(opportunity)
    if not can_do:
        logger.warning(f"Cannot execute {opportunity.id}: missing {missing}")
        # Could still queue for user review
        opportunity.confidence *= 0.5

    # 3. Estimate cost
    cost = capability_engine.estimate_cost(opportunity)
    opportunity.estimated_cost = cost

    # 4. Update state
    state_engine.transition(
        obs.id,
        OpportunityState.CLASSIFIED,
        reason=f"Classified as {opportunity.cycle}/{opportunity.source_type}, cost ${cost:.2f}, missing caps: {missing}"
        if missing
        else "All required capabilities available",
    )

    return opportunity
```
