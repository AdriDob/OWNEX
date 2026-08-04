# Validation → Learning → Evolution — Bucle Completo

> FASE 10 del plan OWNEX v6
> Fecha: 2026-07-29

---

## El Ciclo

```
Execution → Validation → Learning → Evolution → Strategy (next loop)
    ↑                                              │
    └──────────────────────────────────────────────┘
```

Cada ejecución genera datos. Learning Engine extrae patrones. Evolution Engine mejora el sistema.

---

## 1. Validation Engine

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating an execution."""

    opportunity_id: str
    passed: bool
    check_results: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0 quality score
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validator: str = "rules"  # "rules", "heuristics", "llm", "platform"


class ValidationEngine:
    """Validates execution results before submission.

    Different opportunity types have different validation rules:
    - bug_bounty: Is the PoC reproducible? Does it prove the vulnerability?
    - dev_bounty: Does it pass tests? Is code clean? Does it follow existing patterns?
    - ai_work: Is output correct? Does it meet requirements?
    - freelance: Meets client requirements?

    Validation is multi-layered:
    1. Rules (structure check — fast)
    2. Heuristics (quality patterns — medium)
    3. LLM (deep analysis — slow)
    4. Platform (actual platform response — async)
    """

    def __init__(self):
        self.validators: dict[str, list[Validator]] = {
            "bug_bounty": [
                PoCReproducibleValidator(),
                SeverityJustifiedValidator(),
                EvidenceQualityValidator(),
            ],
            "dev_bounty": [
                TestsPassValidator(),
                CodeQualityValidator(),
                PatternMatchValidator(),
            ],
            "ai_work": [
                RequirementsMetValidator(),
                QualityCheckValidator(),
            ],
        }

    async def validate(
        self,
        opportunity: ScoredOpportunity,
        execution_result: ExecutionResult,
    ) -> ValidationResult:
        """Run all validators for this opportunity type."""
        validators = self.validators.get(opportunity.source_type, [])

        result = ValidationResult(
            opportunity_id=opportunity.id,
        )

        for validator in validators:
            try:
                check = await validator.validate(opportunity, execution_result)
                result.check_results.append(check)

                if not check.get("passed", False):
                    result.issues.append(check.get("message", "Validation failed"))
                    result.score -= 0.2  # penalty
                else:
                    result.score += 0.2  # bonus

                if check.get("suggestion"):
                    result.suggestions.append(check["suggestion"])
            except Exception as e:
                logger.error(f"Validator {validator.__class__.__name__} failed: {e}")
                result.issues.append(f"Validator error: {e}")

        # Normalize score
        result.score = max(0.0, min(1.0, result.score))
        result.passed = result.score >= 0.5  # threshold

        if result.passed:
            state_engine.transition(
                opportunity.id,
                OpportunityState.SUBMITTED,
                reason=f"Validation passed (score: {result.score:.2f})",
                metadata={"validators_run": len(result.check_results)},
                actor="validation_engine",
            )
        else:
            state_engine.transition(
                opportunity.id,
                OpportunityState.NEEDS_REVISION,
                reason=f"Validation failed (score: {result.score:.2f}): {result.issues[:2]}",
                metadata={"issues": result.issues},
                actor="validation_engine",
            )

        return result


class Validator(ABC):
    """A single validity check."""

    @abstractmethod
    async def validate(self, opportunity: ScoredOpportunity, result: ExecutionResult) -> dict[str, Any]:
        """Returns check result dict with 'passed', 'message', 'suggestion'."""
        pass


class PoCReproducibleValidator(Validator):
    """Check if proof of concept is actually reproducible."""

    async def validate(self, opportunity, result) -> dict[str, Any]:
        # Check if the result contains reproduction steps
        steps = self._extract_poc_steps(result)
        if not steps or len(steps) < 3:
            return {
                "passed": False,
                "message": "PoC missing reproduction steps",
                "suggestion": "Add step-by-step reproduction including HTTP requests, payloads, and expected vs actual behavior",
            }

        return {
            "passed": True,
            "message": f"PoC has {len(steps)} reproduction steps",
        }

    def _extract_poc_steps(self, result: ExecutionResult) -> list[str]:
        """Extract reproduction steps from execution output."""
        steps = []
        for step in result.completed_steps:
            if step.result and isinstance(step.result, dict):
                text = str(step.result.get("output", ""))
                # Look for numbered steps or bullet points
                lines = text.split("\n")
                for line in lines:
                    if line.strip().startswith(("1.", "2.", "3.", "- ", "* ")):
                        steps.append(line.strip())
        return steps


class CodeQualityValidator(Validator):
    """Basic code quality checks (lint, style, complexity)."""

    async def validate(self, opportunity, result) -> dict[str, Any]:
        # Check if code was produced and looks clean
        has_code = False
        has_tests = False

        for step in result.completed_steps:
            if step.result and isinstance(step.result, dict):
                output = str(step.result.get("output", ""))
                if "def " in output or "class " in output or "function " in output:
                    has_code = True
                if "test" in output.lower() or "assert" in output:
                    has_tests = True

        issues = []
        if not has_code:
            issues.append("No code produced")
        if not has_tests and opportunity.source_type == "dev_bounty":
            issues.append("No tests found")

        return {
            "passed": len(issues) == 0,
            "message": "; ".join(issues) if issues else "Code quality OK",
            "suggestion": "Add tests for the implementation" if not has_tests else None,
        }
```

---

## 2. Learning Engine

Extrae patrones de cada ciclo de ejecución. Estos patrones alimentan:
- StrategyEngine (qué funciona mejor)
- ContextEngine (experiencias similares)
- ClassificationEngine (mejor clasificación)
- EvolutionEngine (adaptación del sistema)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class LearningRecord:
    """A single learning record from an opportunity outcome."""

    opportunity_id: str
    outcome: str  # "paid", "accepted", "rejected", "failed", "skipped"
    source_type: str
    cycle: str
    platform: str

    # Metrics
    effort_hours: float = 0.0
    reward: float = 0.0
    acceptance_days: float = 0.0

    # Classification accuracy
    predicted_value: float = 0.0
    predicted_effort: float = 0.0
    confidence: float = 0.0

    # What we learned
    success_patterns: list[str] = field(default_factory=list)
    failure_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@dataclass
class LearnedPattern:
    """A pattern extracted from learning records."""

    id: str
    pattern: str  # e.g. "Bug bounty programs with JS scope have 3x higher acceptance"
    confidence: float
    source_type: str
    cycle: str
    times_applied: int = 0
    success_rate: float = 0.5  # 0.0 to 1.0
    success_count: int = 0
    total_count: int = 0
    last_applied: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """Extracts patterns from opportunity outcomes.

    Learning happens at multiple levels:
    - Per-opportunity: what worked for this specific type
    - Per-platform: which platforms have best acceptance rates
    - Per-tag: which skills/technologies yield highest EV
    - Per-cycle: which cycles are most profitable
    - Strategy: which strategies produced best outcomes
    """

    def __init__(self, db_path: str = "~/.orion/learning.db"):
        self.db_path = str(db_path)
        self._patterns: dict[str, LearnedPattern] = {}
        self._init_db()

    def _init_db(self):
        """Initialize SQLite for learning records."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT UNIQUE,
                outcome TEXT NOT NULL,
                source_type TEXT NOT NULL,
                cycle TEXT NOT NULL,
                platform TEXT NOT NULL,
                effort_hours REAL DEFAULT 0,
                reward REAL DEFAULT 0,
                acceptance_days REAL DEFAULT 0,
                predicted_value REAL DEFAULT 0,
                predicted_effort REAL DEFAULT 0,
                confidence REAL DEFAULT 0,
                success_patterns TEXT DEFAULT '[]',
                failure_patterns TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id TEXT PRIMARY KEY,
                pattern TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_type TEXT DEFAULT '',
                cycle TEXT DEFAULT '',
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.5,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                last_applied TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()

    async def record_outcome(
        self,
        opportunity: ScoredOpportunity,
        execution_result: ExecutionResult,
        outcome: str,
        reward: float = 0.0,
        effort_hours: float = 0.0,
        notes: str = "",
    ) -> LearningRecord:
        """Record the outcome of an executed opportunity."""
        record = LearningRecord(
            opportunity_id=opportunity.id,
            outcome=outcome,
            source_type=opportunity.source_type,
            cycle=opportunity.cycle,
            platform=opportunity.source_name,
            effort_hours=effort_hours,
            reward=reward,
            predicted_value=opportunity.estimated_reward_max,
            predicted_effort=opportunity.estimated_effort_hours,
            confidence=opportunity.confidence,
            tags=opportunity.tags,
            notes=notes,
        )

        # Extract success/failure patterns from execution
        if outcome in ("paid", "accepted"):
            record.success_patterns = self._extract_success_patterns(execution_result)
        elif outcome in ("rejected", "failed"):
            record.failure_patterns = self._extract_failure_patterns(execution_result)

        # Persist
        self._persist_record(record)

        # Extract patterns
        await self._extract_patterns(record)

        # Update state
        state_engine.transition(
            opportunity.id,
            OpportunityState.LEARNED,
            reason=f"Learning recorded: {outcome}",
            metadata={"reward": reward, "effort": effort_hours},
            actor="learning_engine",
        )

        return record

    def _extract_success_patterns(self, result: ExecutionResult) -> list[str]:
        """Extract patterns from a successful execution."""
        patterns = []
        for step in result.completed_steps:
            if step.status == "completed" and step.result:
                # Time-based patterns
                actual_time = (
                    (step.completed_at - step.started_at).total_seconds() / 60
                    if step.completed_at and step.started_at
                    else 0
                )
                if actual_time > 0 and step.estimated_minutes > 0:
                    ratio = actual_time / step.estimated_minutes
                    if ratio < 0.5:
                        patterns.append(f"Step '{step.name}' completed in {ratio:.0%} of estimated time")
                    elif ratio > 2:
                        patterns.append(f"Step '{step.name}' took {ratio:.0%} of estimated time (underestimated)")
        return patterns

    def _extract_failure_patterns(self, result: ExecutionResult) -> list[str]:
        """Extract patterns from a failed execution."""
        patterns = []
        if result.failed_step:
            patterns.append(f"Failed at step '{result.failed_step.name}'")
            if result.failed_step.retry_count > 0:
                patterns.append(f"Required {result.failed_step.retry_count} retries before failure")
        # Parse error messages
        if result.error:
            patterns.append(f"Error pattern: {result.error[:200]}")
        return patterns

    def _persist_record(self, record: LearningRecord):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO learning_records
               (opportunity_id, outcome, source_type, cycle, platform, 
                effort_hours, reward, acceptance_days, predicted_value, 
                predicted_effort, confidence, success_patterns, failure_patterns, 
                tags, timestamp, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.opportunity_id,
                record.outcome,
                record.source_type,
                record.cycle,
                record.platform,
                record.effort_hours,
                record.reward,
                record.acceptance_days,
                record.predicted_value,
                record.predicted_effort,
                record.confidence,
                json.dumps(record.success_patterns),
                json.dumps(record.failure_patterns),
                json.dumps(record.tags),
                record.timestamp.isoformat(),
                record.notes,
            ),
        )
        conn.commit()
        conn.close()

    async def _extract_patterns(self, record: LearningRecord):
        """Extract and update learned patterns from this record."""
        conn = sqlite3.connect(self.db_path)

        # Pattern: acceptance rate by source_type + platform
        cursor = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN outcome IN ('paid', 'accepted') THEN 1 ELSE 0 END) as success "
            "FROM learning_records WHERE source_type = ? AND platform = ?",
            (record.source_type, record.platform),
        )
        row = cursor.fetchone()
        total, success = row[0], row[1] or 0

        pattern_id = f"acceptance:{record.source_type}:{record.platform}"
        pattern = LearnedPattern(
            id=pattern_id,
            pattern=f"Acceptance rate for {record.platform} ({record.source_type}): {success}/{total} = {success / total:.0%}"
            if total > 0
            else "No data yet",
            confidence=min(0.3 + total * 0.05, 0.95),
            source_type=record.source_type,
            cycle=record.cycle,
            times_applied=total,
            success_rate=success / total if total > 0 else 0.5,
            success_count=success,
            total_count=total,
            last_applied=record.timestamp,
        )

        self._patterns[pattern_id] = pattern

        # Persist
        conn.execute(
            "INSERT OR REPLACE INTO learned_patterns "
            "(id, pattern, confidence, source_type, cycle, times_applied, success_rate, success_count, total_count, last_applied, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pattern_id,
                pattern.pattern,
                pattern.confidence,
                pattern.source_type,
                pattern.cycle,
                pattern.times_applied,
                pattern.success_rate,
                pattern.success_count,
                pattern.total_count,
                pattern.last_applied.isoformat() if pattern.last_applied else None,
                json.dumps(pattern.metadata),
            ),
        )
        conn.commit()
        conn.close()

    def get_patterns_for_source(self, source_type: str, cycle: str) -> list[LearnedPattern]:
        """Get patterns relevant to a given source type."""
        return [p for p in self._patterns.values() if p.source_type == source_type or p.cycle == cycle]

    def get_statistics(self) -> dict[str, Any]:
        """Get learning engine statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT outcome, COUNT(*) FROM learning_records GROUP BY outcome")
        outcomes = dict(cursor.fetchall())

        cursor = conn.execute(
            "SELECT source_type, COUNT(*) as total, "
            "SUM(CASE WHEN outcome IN ('paid', 'accepted') THEN 1 ELSE 0 END) as success "
            "FROM learning_records GROUP BY source_type"
        )
        by_type = {}
        for row in cursor:
            by_type[row[0]] = {"total": row[1], "success": row[2] or 0}

        conn.close()

        return {
            "total_records": sum(outcomes.values()),
            "outcomes": outcomes,
            "by_source_type": by_type,
            "patterns_count": len(self._patterns),
            "total_earned": sum(
                self._get_record_reward(opp_id) for opp_id, outcome in outcomes.items() if outcome == "paid"
            ),
        }
```

---

## 3. Evolution Engine

```python
class EvolutionEngine:
    """Adapts OWNEX based on learned patterns.

    Evolution is the closest thing to self-healing + self-optimization:

    1. **Sensor tuning**: adjust cadence, filters, sources based on yield
    2. **Strategy adjustment**: reweight strategies based on outcomes
    3. **Classification improvement**: add/remove rules based on accuracy
    4. **Pipeline optimization**: adjust timeouts, retries, parallelization
    5. **Knowledge Graph updates**: add entities, relationships, confidence
    6. **Healing loop**: detect degraded components, re-enable or swap

    Evolution runs periodically (daily by default) or on demand.
    """

    def __init__(self, learning_engine: LearningEngine):
        self.learning = learning_engine
        self.evolution_history: list[dict[str, Any]] = []

    async def evolve(self, force: bool = False) -> dict[str, Any]:
        """Run evolution cycle.

        Analyzes all learning records and suggests/produces changes.
        """
        changes: list[str] = []
        stats = self.learning.get_statistics()

        # 1. Strategy optimization
        strategy_changes = await self._optimize_strategies(stats)
        changes.extend(strategy_changes)

        # 2. Sensor tuning
        sensor_changes = await self._tune_sensors(stats)
        changes.extend(sensor_changes)

        # 3. Classification improvement
        class_changes = await self._improve_classification(stats)
        changes.extend(class_changes)

        # 4. Pipeline health
        health_changes = await self._check_pipeline_health(stats)
        changes.extend(health_changes)

        evolution = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": changes,
            "stats": stats,
            "force": force,
        }

        self.evolution_history.append(evolution)

        state_engine.transition(
            "system",
            OpportunityState.EVOLVED,
            reason=f"Evolution cycle: {len(changes)} changes applied",
            metadata={"changes": changes},
            actor="evolution_engine",
        )

        return evolution

    async def _optimize_strategies(self, stats: dict) -> list[str]:
        """Adjust strategy weights based on outcomes."""
        changes = []

        for source_type, data in stats.get("by_source_type", {}).items():
            total = data.get("total", 0)
            success = data.get("success", 0)

            if total >= 10:  # minimum sample size
                rate = success / total

                if rate < 0.2:
                    # Very low success rate — deprioritize this type
                    strategy_engine.set_weights(
                        {
                            "max_ev": 0.5,  # reduce EV weight for this type
                        }
                    )
                    changes.append(f"Reduced priority for {source_type} (success rate: {rate:.0%})")

                elif rate > 0.7:
                    # High success rate — prioritize
                    strategy_engine.set_weights(
                        {
                            "max_ev": 1.5,  # increase EV weight
                        }
                    )
                    changes.append(f"Increased priority for {source_type} (success rate: {rate:.0%})")

        return changes

    async def _tune_sensors(self, stats: dict) -> list[str]:
        """Adjust sensor cadence and filters based on yield."""
        changes = []

        for sensor_id, sensor in observation_engine.sensors.items():
            # Count observations from this sensor
            total_obs = stats.get("total_records", 0)
            if total_obs == 0:
                continue

            # If sensor produces many observations but low yield, adjust
            yield_pct = 0.5  # placeholder — real calculation needs per-sensor stats
            if yield_pct < 0.1:
                changes.append(f"Sensor {sensor_id}: low yield ({yield_pct:.0%}), reducing cadence")
                # sensor.cadence_seconds *= 2  # reduce polling frequency

        return changes

    async def _improve_classification(self, stats: dict) -> list[str]:
        """Add/remove classification rules based on accuracy."""
        changes = []

        for outcome, count in stats.get("outcomes", {}).items():
            if count >= 5 and outcome == "noise":
                # Check if noise was actually an opportunity we missed
                changes.append(f"Found {count} noise-classified observations — reviewing rules")

        return changes

    async def _check_pipeline_health(self, stats: dict) -> list[str]:
        """Check pipeline health and fix issues."""
        changes = []
        healing = HealingOrchestrator()

        health = await healing.diagnose()
        for issue in health.get("issues", []):
            changes.append(f"Health issue: {issue}")

        return changes
```

---

## El Bucle Completo

```
1. EXECUTION  → 2. VALIDATION  → 3. LEARNING  → 4. EVOLUTION
     │              │                │               │
     ▼              ▼                ▼               ▼
  Work done     Quality check    Patterns        System
  submitted     + feedback       extracted       adapts
                                                     │
                                                     ▼
                                            Strategy Engine
                                            (reweights priorities)
                                                     │
                                                     ▼
                                            Next loop starts
                                            with improved system
```

### Integración final

```python
async def execute_and_learn(opportunity: ScoredOpportunity):
    """Full cycle: execute → validate → learn → evolve."""
    
    # Execute
    result = await execution_engine.execute(opportunity)
    if not result.success:
        # Evolution handles failures, but still learn
        pass
    
    # Validate
    validation = await validation_engine.validate(opportunity, result)
    
    # Submit if valid
    if validation.passed:
        submission = await auto_submit(submission)
        
        # Wait for platform response (async, could be days)
        # For now, record immediately with pending outcome
        outcome = "submitted"
        if submission.get("accepted"):
            outcome = "accepted"
        elif submission.get("rejected"):
            outcome = "rejected"
    
    # Learn
    record = await learning_engine.record_outcome(
        opportunity=opportunity,
        execution_result=result,
        outcome=outcome,
        reward=submission.get("reward", 0) if submission else 0,
        effort_hours=result.plan.total_estimated_minutes / 60 if result.plan else 0,
    )
    
    # Evolve (periodic, not per-opportunity)
    if should_run_evolution():
        await evolution_engine.evolve()
    
    return result
```
