# Context Engine + Strategy Engine

> FASE 8 del plan OWNEX v6
> Fecha: 2026-07-29

---

## 1. Context Engine

### El problema que resuelve

Hoy las IAs reciben prompts. OWNEX debe entregar **expedientes completos**.

```
Prompt típico:                     Contexto OWNEX:
"Analiza esta oportunidad"         "Aquí tienes:
                                   - La oportunidad (datos crudos + prescoring)
                                   - Scope del programa (reglas, exclusión)
                                   - Historial del usuario en esta plataforma
                                   - Experiencias previas similares
                                   - Documentación del repo/API
                                   - Credenciales disponibles
                                   - Estrategia actual del usuario
                                   - Cards pendientes y deadlines
                                   - Estado actual del sistema
                                   Ahora analiza."
```

### Fuentes de contexto

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ContextFragment:
    """A single piece of context from one source."""

    source: str  # "platform_docs", "user_history", "memory", "credentials"
    content: str
    relevance: float = 1.0  # 0.0 to 1.0, for prioritization
    token_estimate: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Full context prepared for an AI call.

    This is what the model actually receives.
    Everything is structured, no naked prompts.
    """

    opportunity: ScoredOpportunity
    fragments: list[ContextFragment] = field(default_factory=list)
    system_prompt: str = ""
    built_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_tokens: int = 0
    depth: str = "standard"

    def add(self, fragment: ContextFragment):
        self.fragments.append(fragment)
        self.total_tokens += fragment.token_estimate

    def to_prompt(self) -> str:
        """Convert context to a structured prompt for the model."""
        parts = ["# OWNEX Agent Context", ""]
        parts.append(f"## Opportunity: {self.opportunity.name}")
        parts.append(f"- ID: {self.opportunity.id}")
        parts.append(f"- Cycle: {self.opportunity.cycle}")
        parts.append(f"- Source: {self.opportunity.source_type} / {self.opportunity.source_name}")
        parts.append(f"- Estimated Value: ${self.opportunity.estimated_reward_max:.2f}")
        parts.append(f"- Estimated Effort: {self.opportunity.estimated_effort_hours}h")
        parts.append(f"- URL: {self.opportunity.url}")
        parts.append("")

        # Add fragments sorted by relevance
        sorted_frags = sorted(self.fragments, key=lambda f: f.relevance, reverse=True)
        for frag in sorted_frags:
            parts.append(f"## Context: {frag.source}")
            parts.append(frag.content)
            parts.append("")

        if self.system_prompt:
            parts.append("## System Instructions")
            parts.append(self.system_prompt)

        return "\n".join(parts)

    def token_count(self) -> int:
        """Rough token estimate."""
        return sum(f.token_estimate for f in self.fragments) + len(self.system_prompt) // 4


class ContextSource(ABC):
    """A source of context for the context engine."""

    @abstractmethod
    async def fetch(self, opportunity: ScoredOpportunity, depth: str = "standard") -> ContextFragment | None:
        pass


# ── Concrete context sources ─────────────────────────────────────────────


class PlatformDocsSource(ContextSource):
    """Fetches platform documentation, scope, rules."""

    async def fetch(self, opportunity: ScoredOpportunity, depth: str = "standard") -> ContextFragment | None:
        """Get platform-specific docs.

        For bug bounty: program scope, rules, exclusions
        For dev bounty: repo README, issues, contributing guide
        For freelance: project description, requirements
        """
        source = opportunity.source_name.lower()

        if source == "hackerone" and opportunity.url:
            # Fetch program page for scope/rules
            content = await self._fetch_program_page(opportunity.url)
            if content:
                return ContextFragment(
                    source="platform_docs",
                    content=f"Platform: HackerOne\nProgram URL: {opportunity.url}\nScope:\n{content[:2000]}",
                    relevance=0.9,
                    token_estimate=len(content) // 4,
                )

        # Generic fallback
        return ContextFragment(
            source="platform_docs",
            content=f"Platform: {opportunity.source_name}\nType: {opportunity.source_type}\nURL: {opportunity.url}",
            relevance=0.5,
            token_estimate=50,
        )

    async def _fetch_program_page(self, url: str) -> str | None:
        """Fetch and extract text from program page."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15)
                if resp.status_code == 200:
                    # Extract text from HTML
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(resp.text, "html.parser")
                    return soup.get_text(separator="\n", strip=True)[:3000]
        except Exception:
            return None


class UserHistorySource(ContextSource):
    """Fetches user's history on this platform."""

    async def fetch(self, opportunity: ScoredOpportunity, depth: str = "standard") -> ContextFragment | None:
        """Get user's past submissions, acceptance rate, earnings."""
        platform = opportunity.source_name.lower()

        # Query MemoryStore for history
        history = memory_store.get_by_platform(platform)
        if not history:
            return None

        text = (
            f"User history on {platform}:\n"
            f"- Total submissions: {history.total_submissions}\n"
            f"- Accepted: {history.total_accepted}\n"
            f"- Acceptance rate: {history.personal_acceptance_rate:.0%}\n"
            f"- Avg payout: ${history.personal_avg_payout:.2f}\n"
            f"- Avg days to complete: {history.personal_avg_days:.1f}"
        )

        return ContextFragment(
            source="user_history",
            content=text,
            relevance=0.85,
            token_estimate=len(text) // 4,
        )


class LearningSource(ContextSource):
    """Fetches patterns extracted by the Learning Engine."""

    async def fetch(self, opportunity: ScoredOpportunity, depth: str = "standard") -> ContextFragment | None:
        """Get patterns from similar past opportunities."""
        patterns = learning_system.get_patterns_for_source(
            source_type=opportunity.source_type,
            cycle=opportunity.cycle,
        )

        if not patterns:
            return None

        text_lines = ["Learned patterns for similar opportunities:"]
        for p in patterns[:5]:
            text_lines.append(f"- Pattern: {p.pattern}")
            text_lines.append(f"  Confidence: {p.confidence:.0%}")
            text_lines.append(f"  Applied: {p.times_applied}x, Success: {p.success_rate:.0%}")

        text = "\n".join(text_lines)

        return ContextFragment(
            source="learning_system",
            content=text,
            relevance=0.7,
            token_estimate=len(text) // 4,
        )


# ── Context Engine (the orchestrator) ────────────────────────────────────


class ContextEngine:
    """Builds enriched context for AI calls.

    Before ANY provider call, the ContextEngine assembles:
    - Platform docs (scope, rules, API)
    - User history (past submissions, acceptance rate)
    - Learning patterns (similar past opportunities)
    - Credentials (account info from Vault)
    - Current state (state machine)
    - Strategy context (current priorities)
    - Memory (persistent user memory)

    The result is a structured AgentContext that the model can consume.
    """

    def __init__(self):
        self.sources: list[ContextSource] = [
            PlatformDocsSource(),
            UserHistorySource(),
            LearningSource(),
            # More sources added as they're built
        ]
        self.max_tokens: int = 8000  # max context tokens

    def add_source(self, source: ContextSource):
        """Register a new context source."""
        self.sources.append(source)

    async def build_context(
        self,
        opportunity: ScoredOpportunity,
        depth: str = "standard",
        system_prompt: str = "",
    ) -> AgentContext:
        """Build full context for an opportunity.

        Args:
            opportunity: The opportunity to build context for
            depth: "light" (quick), "standard" (full), "deep" (exhaustive)
            system_prompt: Additional system instructions

        Returns:
            AgentContext with all fragments
        """
        context = AgentContext(
            opportunity=opportunity,
            system_prompt=system_prompt,
            depth=depth,
        )

        # Add opportunity itself as first context
        context.add(
            ContextFragment(
                source="opportunity",
                content=f"Name: {opportunity.name}\n"
                f"Description: {opportunity.description}\n"
                f"Value: ${opportunity.estimated_reward_max:.2f}\n"
                f"Effort: {opportunity.estimated_effort_hours}h\n"
                f"Tags: {', '.join(opportunity.tags)}\n"
                f"Confidence: {opportunity.confidence:.0%}",
                relevance=1.0,
                token_estimate=100,
            )
        )

        # Add state
        machine = state_engine.get_or_create(opportunity.id)
        context.add(
            ContextFragment(
                source="state",
                content=f"Current state: {machine.current_state.value}\n"
                f"Time in state: {machine.time_in_state() / 3600:.1f}h\n"
                f"Transitions: {machine.transitions_count}",
                relevance=0.8,
                token_estimate=30,
            )
        )

        # Fetch from all context sources
        for source in self.sources:
            try:
                fragment = await source.fetch(opportunity, depth)
                if fragment and context.total_tokens + (fragment.token_estimate or 0) < self.max_tokens:
                    context.add(fragment)
            except Exception as e:
                logger.warning(f"Context source {source.__class__.__name__} failed: {e}")

        # Sort by relevance
        context.fragments.sort(key=lambda f: f.relevance, reverse=True)

        return context

    async def build_system_prompt(
        self,
        context: AgentContext,
        role: str = "analyst",
    ) -> str:
        """Build a system prompt from the context.

        Different roles get different prompt templates:
        - analyst: "Analyze this opportunity..."
        - planner: "Plan execution for..."
        - executor: "Execute this plan..."
        - validator: "Validate these results..."
        """
        prompts = {
            "analyst": (
                "You are an autonomous work analyst for OWNEX. "
                "Given an opportunity and its context, provide:\n"
                "1. Technical assessment (feasibility, difficulty)\n"
                "2. Value assessment (is this worth doing?)\n"
                "3. Risk assessment (what could go wrong?)\n"
                "4. Recommended approach\n"
            ),
            "planner": (
                "You are an autonomous work planner for OWNEX. "
                "Given an opportunity and context, create a detailed execution plan:\n"
                "1. Steps required (in order)\n"
                "2. Capabilities needed\n"
                "3. Estimated time per step\n"
                "4. Potential blockers\n"
                "5. Fallback strategies\n"
            ),
        }

        base = prompts.get(role, prompts["analyst"])
        return f"{base}\n\n{context.to_prompt()}"
```

---

## 2. Strategy Engine

### El problema

```
Llegan simultáneamente:
- 3 bug bounty críticos (EV alto, competencia alta)
- 15 dev bounties (EV medio, competencia baja)
- 300 microtasks (EV bajo, competencia muy baja, inmediato)

Estrategia para HOY:
- ¿Hago los 3 bounties? (8h, EV esperado $3000, pero 50% competencia)
- ¿Hago 15 dev bounties? (4h, EV esperado $800, competencia baja)
- ¿Hago 300 microtasks? (2h, EV esperado $200, 100% realizables)
- ¿Split? ¿Prioridad por EV/hora?
```

La StrategyEngine **no planifica**. **Decide en qué trabajar AHORA**.

### Estrategias

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PrioritizedOpportunity:
    """An opportunity with a strategy decision attached."""

    opportunity: ScoredOpportunity
    priority: float  # 0.0 to 1.0
    reason: str  # why this priority?
    estimated_ev: float  # expected value after strategy
    estimated_time: float  # estimated hours
    due_by: datetime | None = None
    strategy_applied: str = ""


class Strategy(ABC):
    """A strategy decides what to work on.

    Each strategy has a weight. The overall score is weighted sum.
    """

    name: str = ""
    weight: float = 1.0

    @abstractmethod
    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        """Score 0.0 to 1.0. Higher = more priority."""
        pass


# ── Concrete strategies ──────────────────────────────────────────────────


class MaxEVStrategy(Strategy):
    """Prioritize opportunities with highest expected value."""

    name = "max_ev"
    weight = 1.0

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        """EV score: normalized to [0, 1] based on max EV in the batch."""
        max_ev = max((o.estimated_reward_max * o.confidence for o in context.opportunities), default=1.0)
        if max_ev == 0:
            return 0.0
        ev = opportunity.estimated_reward_max * opportunity.confidence
        return min(ev / max_ev, 1.0)


class BestEffortRatioStrategy(Strategy):
    """Prioritize best $/hour ratio."""

    name = "best_effort_ratio"
    weight = 0.8

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        ev = opportunity.estimated_reward_max * opportunity.confidence
        hours = max(opportunity.estimated_effort_hours, 0.5)
        ratio = ev / hours
        max_ratio = max(
            (o.estimated_reward_max * o.confidence / max(o.estimated_effort_hours, 0.5) for o in context.opportunities),
            default=1.0,
        )
        if max_ratio == 0:
            return 0.0
        return min(ratio / max_ratio, 1.0)


class LowCompetitionStrategy(Strategy):
    """Prioritize opportunities with least competition."""

    name = "low_competition"
    weight = 0.6

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        # Low competition = high personal_fit, low overall competition
        score = (1 - opportunity.competition) * 0.5 + opportunity.personal_fit * 0.5
        return score


class TimeSensitiveStrategy(Strategy):
    """Prioritize opportunities with approaching deadlines."""

    name = "time_sensitive"
    weight = 0.7

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        if not opportunity.due_by:
            return 0.0
        hours_left = (opportunity.due_by - datetime.now(timezone.utc)).total_seconds() / 3600
        if hours_left <= 0:
            return 0.0  # already past due
        if hours_left < 24:
            return 1.0  # due within 24h
        return max(0, 1.0 - hours_left / (7 * 24))  # linear decay over a week


class QuickWinStrategy(Strategy):
    """Prioritize opportunities that can be done quickly (< 2h).

    Good for filling short time slots or building momentum.
    """

    name = "quick_win"
    weight = 0.4

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        if opportunity.estimated_effort_hours <= 0:
            return 0.0
        if opportunity.estimated_effort_hours <= 1:
            return 1.0
        if opportunity.estimated_effort_hours <= 2:
            return 0.7
        return max(0, 1.0 - opportunity.estimated_effort_hours / 8)


class AvailabilityStrategy(Strategy):
    """Filter by current time availability."""

    name = "availability"
    weight = 0.5

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        """If we have 30 min, prefer quick wins."""
        available_hours = context.available_time_hours
        if available_hours <= 0:
            return 0.0
        if opportunity.estimated_effort_hours <= available_hours:
            return 1.0
        # Partial score if it can be started
        return available_hours / opportunity.estimated_effort_hours


class CycleBalanceStrategy(Strategy):
    """Ensure we're not doing only one type of work."""

    name = "cycle_balance"
    weight = 0.3

    def score(self, opportunity: ScoredOpportunity, context: WorkContext) -> float:
        """Score higher for underrepresented cycles."""
        cycle_counts = context.get_cycle_counts()
        total = sum(cycle_counts.values())
        if total == 0:
            return 0.5
        current = cycle_counts.get(opportunity.cycle, 0)
        proportion = current / total
        # Boost if this cycle is underrepresented
        return 1.0 - proportion


# ── Work Context ─────────────────────────────────────────────────────────


@dataclass
class WorkContext:
    """Current work context for strategy decisions."""

    opportunities: list[ScoredOpportunity]
    available_time_hours: float = 8.0  # available work hours today
    current_cycle: str | None = None  # what we're doing right now
    energy_level: str = "normal"  # "low", "normal", "high"
    financial_goal_month: float = 10000.0  # monthly target
    financial_goal_week: float = 2500.0  # weekly target
    earned_this_month: float = 0.0
    earned_this_week: float = 0.0
    last_strategy: str = "balanced"
    user_preferences: dict[str, float] = field(default_factory=dict)

    def get_cycle_counts(self) -> dict[str, int]:
        counts = {}
        for o in self.opportunities:
            counts[o.cycle] = counts.get(o.cycle, 0) + 1
        return counts

    def get_cycle_ev(self) -> dict[str, float]:
        evs = {}
        for o in self.opportunities:
            ev = o.estimated_reward_max * o.confidence
            evs[o.cycle] = evs.get(o.cycle, 0) + ev
        return evs


# ── Strategy Engine ──────────────────────────────────────────────────────


class StrategyEngine:
    """Decides what to work on RIGHT NOW.

    Not planning — DECIDING.
    Runs every time the queue needs prioritization.
    """

    def __init__(self):
        self.strategies: list[Strategy] = [
            MaxEVStrategy(),
            BestEffortRatioStrategy(),
            LowCompetitionStrategy(),
            TimeSensitiveStrategy(),
            QuickWinStrategy(),
            AvailabilityStrategy(),
            CycleBalanceStrategy(),
        ]

    def add_strategy(self, strategy: Strategy):
        self.strategies.append(strategy)

    def set_weights(self, weights: dict[str, float]):
        """Override strategy weights dynamically."""
        for s in self.strategies:
            if s.name in weights:
                s.weight = weights[s.name]

    async def decide(
        self,
        opportunities: list[ScoredOpportunity],
        context: WorkContext | None = None,
    ) -> list[PrioritizedOpportunity]:
        """Score all opportunities and return prioritized list."""
        if context is None:
            context = WorkContext(opportunities=opportunities)

        context.opportunities = opportunities

        scored: list[PrioritizedOpportunity] = []
        for opp in opportunities:
            total_score = 0.0
            total_weight = 0.0

            reasons = []
            for strategy in self.strategies:
                try:
                    score = strategy.score(opp, context)
                    total_score += score * strategy.weight
                    total_weight += strategy.weight
                    if score > 0.3:
                        reasons.append(f"{strategy.name}={score:.2f}")
                except Exception as e:
                    logger.warning(f"Strategy {strategy.name} failed for {opp.id}: {e}")

            priority = total_score / total_weight if total_weight > 0 else 0.0

            ev = opp.estimated_reward_max * opp.confidence
            po = PrioritizedOpportunity(
                opportunity=opp,
                priority=priority,
                reason=" | ".join(reasons),
                estimated_ev=ev,
                estimated_time=opp.estimated_effort_hours,
                strategy_applied=self.__class__.__name__,
            )
            scored.append(po)

        # Sort by priority descending
        scored.sort(key=lambda p: p.priority, reverse=True)

        await self._emit_strategy(scored)

        return scored

    async def _emit_strategy(self, prioritized: list[PrioritizedOpportunity]):
        if event_bus:
            top = prioritized[:5]
            await event_bus.emit(
                "strategy:decided",
                {
                    "top_choice": top[0].opportunity.id if top else None,
                    "total_considered": len(prioritized),
                    "top_5": [p.opportunity.name for p in top],
                },
            )

    async def should_continue(
        self,
        current: ScoredOpportunity,
        new_opportunities: list[ScoredOpportunity],
        context: WorkContext,
    ) -> tuple[bool, str]:
        """Should we continue current work or switch?

        Returns (keep_going, reason)
        """
        if not new_opportunities:
            return (True, "No new opportunities to consider")

        # Score current vs best alternative
        best = await self.decide([current] + new_opportunities, context)

        if len(best) < 2:
            return (True, "Only one option")

        current_rank = next(i for i, p in enumerate(best) if p.opportunity.id == current.id)

        if current_rank == 0:
            return (True, "Current is still highest priority")

        best_alt = best[0]
        current_score = best[current_rank]

        # Switch only if alternative is significantly better
        if best_alt.priority > current_score.priority * 1.5:
            return (
                False,
                f"Better opportunity: {best_alt.opportunity.name} "
                f"(priority {best_alt.priority:.2f} vs {current_score.priority:.2f})",
            )

        return (True, "Current priority within acceptable range")

    def get_statistics(self) -> dict[str, Any]:
        return {
            "strategies": [s.name for s in self.strategies],
            "weights": {s.name: s.weight for s in self.strategies},
        }
```

---

## Integración Context + Strategy

```python
# Wiring:
# 1. StrategyEngine decide() → top opportunity
# 2. ContextEngine build_context() for that opportunity
# 3. PipelineEngine executes with the full context


async def decide_and_execute():
    # Get all scored opportunities
    opportunities = opportunity_engine.get_scored(status="scored")

    if not opportunities:
        logger.info("No opportunities to process")
        return

    # Build work context
    work_context = WorkContext(
        opportunities=opportunities,
        available_time_hours=8.0,
        energy_level="normal",
        financial_goal_month=10000.0,
        earned_this_month=await vault.get_monthly_earnings(),
    )

    # Decide
    prioritized = await strategy_engine.decide(opportunities, work_context)

    if not prioritized:
        return

    # Take top opportunity
    top = prioritized[0]

    # Build context
    context = await context_engine.build_context(
        top.opportunity,
        depth="standard",
    )

    # Execute
    await pipeline_engine.execute(
        opportunity=top.opportunity,
        context=context,
    )
```
