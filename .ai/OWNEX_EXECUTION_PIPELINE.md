# Execution Pipeline — Planning → Preparation → Execution

> FASE 9 del plan OWNEX v6
> Fecha: 2026-07-29

---

## Visión General

La pipeline de ejecución OWNEX v6 extiende el PipelineEngine existente (v5) con dos motores previos (Planning + Preparation) y un contrato de datos unificado.

```
PipelineEngine v5 existente:
  Pipeline → run() → AgentAdapter → Execution → Result

PipelineEngine v6:
  Opportunity → PLANNING → PREPARATION → EXECUTION → result
                  │            │              │
                  │     ContextEngine      CapabilityEngine
                  ▼            ▼              ▼
             Plan doc     Env ready      Agent running
```

## 1. Planning Engine

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str
    name: str
    description: str
    order: int
    capability: str                # capability ID needed
    estimated_minutes: int = 0
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_max: int = 3
    
    # Result placeholder
    result: Any = None
    status: str = "pending"        # pending | running | completed | failed | skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class ExecutionPlan:
    """Full execution plan for an opportunity."""
    id: str
    opportunity_id: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_estimated_minutes: int = 0
    context_hash: str = ""
    status: str = "created"        # created | running | completed | failed
    
    def add_step(self, step: PlanStep):
        self.steps.append(step)
        self.total_estimated_minutes += step.estimated_minutes


class PlanningEngine:
    """Given an opportunity + context, creates an execution plan.
    
    Uses templates for known opportunity types and LLM for novel ones.
    """
    
    # Plans by source_type (templates)
    TEMPLATES = {
        "bug_bounty": lambda o: [
            PlanStep("recon", "Reconnaissance", "Gather intel: subdomains, endpoints, tech stack", 
                     order=1, capability="network_scanning", estimated_minutes=15),
            PlanStep("scope", "Scope Analysis", "Analyze program scope, rules, exclusions", 
                     order=2, capability="web_scraping", estimated_minutes=10),
            PlanStep("test", "Vulnerability Testing", "Systematic testing per methodology", 
                     order=3, capability="llm_reasoning", estimated_minutes=120),
            PlanStep("report", "Report Writing", "Write findings report with PoC", 
                     order=4, capability="llm_reasoning", estimated_minutes=30),
            PlanStep("submit", "Submission", "Submit finding to platform", 
                     order=5, capability="api_interaction", estimated_minutes=5),
        ],
        "dev_bounty": lambda o: [
            PlanStep("clone", "Clone Repository", "Clone repo and set up environment", 
                     order=1, capability="git_operations", estimated_minutes=5),
            PlanStep("understand", "Code Understanding", "Read existing code, understand patterns", 
                     order=2, capability="code_execution", estimated_minutes=30),
            PlanStep("implement", "Implementation", "Write code to solve the issue", 
                     order=3, capability="code_execution", estimated_minutes=120),
            PlanStep("test", "Testing", "Run tests, verify solution", 
                     order=4, capability="code_execution", estimated_minutes=15),
            PlanStep("submit", "Submit PR", "Create pull request with solution", 
                     order=5, capability="git_operations", estimated_minutes=5),
        ],
        "ai_work": lambda o: [
            PlanStep("analyze", "Analyze Task", "Read task description and requirements", 
                     order=1, capability="llm_reasoning", estimated_minutes=5),
            PlanStep("execute", "Execute Task", "Complete the AI work task", 
                     order=2, capability="code_execution", estimated_minutes=60),
            PlanStep("verify", "Verify Output", "Check quality before submission", 
                     order=3, capability="llm_reasoning", estimated_minutes=10),
            PlanStep("submit", "Submit", "Submit completed work", 
                     order=4, capability="api_interaction", estimated_minutes=2),
        ],
    }
    
    async def create_plan(
        self,
        opportunity: ScoredOpportunity,
        context: AgentContext,
    ) -> ExecutionPlan:
        """Create an execution plan for an opportunity."""
        template = self.TEMPLATES.get(opportunity.source_type)
        
        if template:
            steps = template(opportunity)
        else:
            # Generic plan for unknown types
            steps = [
                PlanStep("assess", "Assessment", f"Assess {opportunity.name}", 
                         order=1, capability="llm_reasoning", estimated_minutes=15),
                PlanStep("execute", "Execution", "Execute the work", 
                         order=2, capability="code_execution", estimated_minutes=60),
                PlanStep("submit", "Submission", "Submit results", 
                         order=3, capability="api_interaction", estimated_minutes=5),
            ]
        
        plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity.id,
            steps=steps,
            context_hash=self._hash_context(context),
        )
        
        state_engine.transition(
            opportunity.id,
            OpportunityState.IN_PROGRESS,
            reason=f"Plan created with {len(steps)} steps",
            metadata={"steps": [s.name for s in steps]},
            actor="planning_engine",
        )
        
        return plan
    
    def _hash_context(self, context: AgentContext) -> str:
        return hashlib.sha256(context.to_prompt().encode()).hexdigest()[:16]
```

---

## 2. Preparation Engine

```python
class PreparationEngine:
    """Sets up the environment before execution.
    
    For each step, the preparation engine ensures:
    - Required tools are installed
    - Credentials are available
    - Working directory exists
    - Dependencies are satisfied
    - Git repos are cloned
    - Browser instances are ready
    
    Preparation is idempotent — running it twice on the same step
    should not cause issues.
    """
    
    async def prepare(self, plan: ExecutionPlan, capability: CapabilityEngine) -> dict[str, Any]:
        """Prepare environment for all steps in a plan.
        
        Returns preparation status per step capability.
        """
        results = {}
        
        step_capabilities = set()
        for step in plan.steps:
            cap = capability.get(step.capability)
            if cap:
                step_capabilities.add(cap.id)
                # Check availability
                if not cap.available:
                    logger.warning(f"Capability {cap.id} is not available for step {step.name}")
                    step.status = "failed"
                    step.result = {"error": f"Capability {cap.id} not available"}
                if cap.requires_user:
                    logger.info(f"Step {step.name} requires user interaction")
        
        # Prepare each capability once
        for cap_id in step_capabilities:
            result = await self._prepare_capability(cap_id)
            results[cap_id] = result
        
        state_engine.transition(
            plan.opportunity_id,
            OpportunityState.ACTIVE,
            reason="Environment prepared",
            metadata={"capabilities_ready": list(step_capabilities)},
        )
        
        return results
    
    async def _prepare_capability(self, capability_id: str) -> dict[str, Any]:
        """Prepare a single capability.
        
        This is where we check:
        - git_operations → is git installed?
        - code_execution → is python available?
        - network_scanning → are tools installed?
        """
        checks = {
            "git_operations": self._check_git,
            "code_execution": self._check_code_exec,
            "web_scraping": self._check_http,
            "network_scanning": self._check_network_tools,
            "browser_automation": self._check_browser,
        }
        
        checker = checks.get(capability_id)
        if checker:
            return await checker()
        
        return {"capability": capability_id, "status": "unknown", "available": True}
    
    async def _check_git(self) -> dict[str, Any]:
        import subprocess
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        return {
            "capability": "git_operations",
            "status": "ready" if result.returncode == 0 else "not_found",
            "version": result.stdout.strip() if result.returncode == 0 else None,
            "available": result.returncode == 0,
        }
    
    async def _check_code_exec(self) -> dict[str, Any]:
        import sys
        return {
            "capability": "code_execution",
            "status": "ready",
            "version": sys.version,
            "available": True,
        }
    
    async def _check_http(self) -> dict[str, Any]:
        try:
            import httpx
            return {"capability": "web_scraping", "status": "ready", "available": True}
        except ImportError:
            return {"capability": "web_scraping", "status": "missing_dependency", "available": False}
    
    async def _check_network_tools(self) -> dict[str, Any]:
        import subprocess
        result = subprocess.run(["which", "nmap"], capture_output=True, text=True)
        return {
            "capability": "network_scanning",
            "status": "ready" if result.returncode == 0 else "not_found",
            "available": result.returncode == 0,
        }
    
    async def _check_browser(self) -> dict[str, Any]:
        try:
            import playwright
            return {"capability": "browser_automation", "status": "ready", "available": True}
        except ImportError:
            return {"capability": "browser_automation", "status": "missing_dependency", "available": False}
```

---

## 3. Execution Engine — Integración con PipelineEngine v5

El PipelineEngine existente (v5) se preserva y extiende:

```python
from core.pipeline.engine import PipelineEngine as BasePipelineEngine


class ExecutionEngine(BasePipelineEngine):
    """OWNEX v6 execution engine.
    
    Extends PipelineEngine v5 with:
    - Pre-fetch context from ContextEngine
    - Step-by-step execution with state tracking
    - Error recovery per step
    - Integration with StateEngine for lifecycle
    - Capability-aware step routing
    """
    
    def __init__(self, pipeline_config: str = "config/engine.yaml"):
        super().__init__(pipeline_config)
        self.planner = PlanningEngine()
        self.preparer = PreparationEngine()
        self.context_engine = None
        self.capability_engine = None
    
    async def execute(
        self,
        opportunity: ScoredOpportunity,
        plan: ExecutionPlan | None = None,
        context: AgentContext | None = None,
    ) -> ExecutionResult:
        """Execute an opportunity from plan to submission.
        
        Full flow:
        1. Create plan (if not provided)
        2. Prepare environment
        3. Execute each step
        4. Track state transitions
        5. Return results
        """
        # 1. Plan
        if plan is None and self.context_engine:
            context = context or await self.context_engine.build_context(opportunity)
            plan = await self.planner.create_plan(opportunity, context)
        
        if not plan:
            return ExecutionResult(success=False, error="No plan could be created")
        
        # 2. Prepare
        if self.capability_engine:
            prep_results = await self.preparer.prepare(plan, self.capability_engine)
            
            # Check all capabilities ready
            all_ready = all(
                r.get("available", False) 
                for r in prep_results.values()
            )
            if not all_ready:
                unavailable = [
                    cap_id for cap_id, r in prep_results.items()
                    if not r.get("available", False)
                ]
                logger.warning(f"Unavailable capabilities: {unavailable}")
                # Could still try, but flag it
        
        # 3. Execute each step
        for step in plan.steps:
            step.started_at = datetime.now(timezone.utc)
            step.status = "running"
            
            logger.info(f"Executing step {step.order}/{len(plan.steps)}: {step.name}")
            
            try:
                result = await self._execute_step(step, context)
                step.result = result
                step.status = "completed" if result.get("success") else "failed"
                
                if not result.get("success"):
                    error = result.get("error", "Unknown error")
                    logger.error(f"Step {step.name} failed: {error}")
                    
                    # Auto-retry
                    if step.retry_count < step.retry_max:
                        step.retry_count += 1
                        step.status = "pending"  # retry
                        logger.info(f"Retrying step {step.name} ({step.retry_count}/{step.retry_max})")
                        continue
                    
                    # Step failed -> whole plan fails
                    state_engine.transition(
                        opportunity.id,
                        OpportunityState.BLOCKED,
                        reason=f"Step {step.name} failed: {error}",
                        actor="execution_engine",
                    )
                    
                    return ExecutionResult(
                        success=False,
                        error=f"Step {step.name} failed: {error}",
                        plan=plan,
                        completed_steps=[s for s in plan.steps if s.status == "completed"],
                        failed_step=step,
                    )
            
            except Exception as e:
                step.status = "failed"
                step.result = {"error": str(e)}
                logger.exception(f"Step {step.name} raised unhandled exception")
                
                state_engine.transition(
                    opportunity.id,
                    OpportunityState.BLOCKED,
                    reason=f"Unhandled exception in step {step.name}: {e}",
                    actor="execution_engine",
                )
                
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    plan=plan,
                    completed_steps=[s for s in plan.steps if s.status == "completed"],
                    failed_step=step,
                )
            
            step.completed_at = datetime.now(timezone.utc)
        
        # All steps completed
        state_engine.transition(
            opportunity.id,
            OpportunityState.SUBMITTED,
            reason=f"Execution completed: {len(plan.steps)} steps",
            metadata={"steps": [s.name for s in plan.steps if s.status == "completed"]},
            actor="execution_engine",
        )
        
        return ExecutionResult(
            success=True,
            plan=plan,
            completed_steps=plan.steps,
        )
    
    async def _execute_step(
        self, 
        step: PlanStep, 
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        """Execute a single plan step using PipelineEngine."""
        
        # Check if existing pipeline can handle this
        # PipelineEngine has AgentAdapter that runs agents
        
        if step.capability == "code_execution":
            # Use existing PipelineEngine to run code
            return await self.run_pipeline("code_execution", {
                "step": step,
                "context": context.to_prompt() if context else None,
            })
        
        elif step.capability == "git_operations":
            return await self.run_pipeline("git_operations", {
                "step": step,
            })
        
        elif step.capability == "llm_reasoning":
            # Use existing ProviderRouter / agents
            return await self.run_pipeline("reasoning", {
                "step": step,
                "context": context.to_prompt() if context else None,
            })
        
        elif step.capability == "api_interaction":
            return await self.run_pipeline("api_interaction", {
                "step": step,
            })
        
        # For unknown capabilities, try the generic agent pipeline
        return await self.run_pipeline("generic", {
            "step": step,
            "context": context.to_prompt() if context else None,
        })


@dataclass
class ExecutionResult:
    """Result of executing an opportunity."""
    success: bool
    error: str = ""
    plan: ExecutionPlan | None = None
    completed_steps: list[PlanStep] = field(default_factory=list)
    failed_step: PlanStep | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
```

---

## 4. Pipeline Completo

### Flujo integrado

```python
async def full_pipeline(observation: Observation) -> ExecutionResult | None:
    """Complete OWNEX v6 pipeline from raw observation to execution."""
    
    # 1. Normalize
    obs = normalization_engine.normalize(observation)
    
    # 2. Identify
    entity = identity_engine.resolve(obs)
    obs.entity_id = entity.id
    
    # 3. Classify
    opportunity = await classification_engine.classify(obs)
    if not opportunity:
        logger.info(f"Observation {obs.id} classified as noise")
        return None
    
    # 4. Score
    opportunity = opportunity_engine.score(opportunity)
    
    # 5. Strategy
    context = WorkContext(
        opportunities=[opportunity],  # simplified; normally batch
        available_time_hours=8,
    )
    prioritized = await strategy_engine.decide([opportunity], context)
    if not prioritized:
        logger.info(f"No strategy matched for {opportunity.id}")
        return None
    
    top = prioritized[0]
    
    # 6. Context
    agent_context = await context_engine.build_context(top.opportunity)
    
    # 7. Execute
    result = await execution_engine.execute(top.opportunity, context=agent_context)
    
    return result
```

### Arquitectura de conexiones

```
                      ┌─────────────────────┐
                      │    EventBus         │
                      │  (observabilidad)   │
                      └──┬──────────────────┘
                         │
┌─────────────────────────────────────────────────────────────┐
│                     PipelineEngine                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Planning  │→│Preparat. │→│Execution │→│Validat. │  │
│  │Engine    │ │Engine    │ │Engine    │ │Engine   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                         ↓                               │
│                    AgentAdapter                          │
│               (Model: Provider Router)                   │
└─────────────────────────────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    ▼                    ▼                    ▼
 Agent A            Agent B             Agent C
 (security)         (forge)             (pulse)
```

### Lo que NO cambia del PipelineEngine v5

- `PipelineEngine.run_pipeline()` — sigue igual
- `pipeline_config = "config/engine.yaml"` — idem
- Agentes registrados — mismos imports
- EventBus — misma interfaz
- HealingOrchestrator — mismo recovery
- AutoSubmitPipeline — mismo auto-submit

### Lo que SE AÑADE

- `PlanningEngine` — antes de ejecutar
- `PreparationEngine` — antes de ejecutar
- Step tracking con `PlanStep.status`
- StateEngine transiciones por paso
- ContextEngine integración
- CapabilityEngine check por paso
