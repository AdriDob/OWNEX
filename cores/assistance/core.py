"""
OWNEX Assistance Core — The heart of the system.

Flow:
1. User writes objective
2. OWNEX understands (parses, clarifies, contextualizes)
3. Divides task into subtasks
4. Proposes plan (with time estimates, tools needed)
5. Executes tools (with progress, checkpoints)
6. Delivers result (formatted, actionable)
7. Learns (records outcome, updates patterns)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cores.ai.runtime import TaskType, get_oar
from cores.memory.system import (
    MemoryNamespace,
    MemoryTier,
    get_learning_engine,
    get_memory_store,
    learn_task_outcome,
    learn_tool_usage,
)

logger = logging.getLogger("ownex.assistance")


class AssistanceMode(StrEnum):
    """Assistance modes for different user experience levels."""

    BEGINNER = "beginner"  # Explains everything, asks for confirmation
    NORMAL = "normal"  # Helps and automates, shows key decisions
    EXPERT = "expert"  # Shows technical details, minimal handholding


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubTask:
    """A single subtask in a plan."""

    id: str
    name: str
    description: str
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_seconds: float = 0.0


@dataclass
class Plan:
    """Execution plan for an objective."""

    id: str
    objective: str
    subtasks: list[SubTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    estimated_total_duration: float = 0.0
    mode: AssistanceMode = AssistanceMode.NORMAL
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class ExecutionResult:
    """Result of plan execution."""

    plan_id: str
    success: bool
    completed_subtasks: int
    failed_subtasks: int
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    learnings: list[str] = field(default_factory=list)


class ObjectiveParser:
    """Parses and understands user objectives."""

    def __init__(self):
        self.oar = get_oar()

    async def parse(self, objective: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Parse objective into structured understanding."""

        prompt = f"""
Analyze this user objective and extract:
1. Core goal (one sentence)
2. Domain/category (coding, research, analysis, automation, writing, etc.)
3. Complexity (simple, moderate, complex)
4. Required capabilities (tools, skills, knowledge)
5. Estimated time range (minutes)
6. Potential subtasks (3-7)
7. Clarifying questions (if ambiguous)
8. Success criteria (measurable)

Objective: "{objective}"

Context: {json.dumps(context or {})}

Return JSON only.
"""
        response = await self.oar.chat(
            prompt,
            task_type=TaskType.REASONING,
            temperature=0.2,
            max_tokens=2000,
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "goal": objective,
                "domain": "general",
                "complexity": "moderate",
                "capabilities": [],
                "estimated_minutes": 30,
                "subtasks": [],
                "questions": [],
                "success_criteria": ["Objective completed"],
            }


class TaskPlanner:
    """Creates execution plans from understood objectives."""

    def __init__(self):
        self.oar = get_oar()

    async def create_plan(
        self,
        understanding: dict[str, Any],
        mode: AssistanceMode = AssistanceMode.NORMAL,
    ) -> Plan:
        """Create detailed execution plan."""

        plan = Plan(
            id=str(uuid.uuid4())[:8],
            objective=understanding.get("goal", ""),
            mode=mode,
        )

        subtasks_data = understanding.get("subtasks", [])
        if not subtasks_data:
            subtasks_data = await self._generate_subtasks(understanding)

        for i, st_data in enumerate(subtasks_data):
            subtask = SubTask(
                id=f"{plan.id}_{i}",
                name=st_data.get("name", f"Step {i + 1}"),
                description=st_data.get("description", ""),
                tool=st_data.get("tool"),
                args=st_data.get("args", {}),
                depends_on=st_data.get("depends_on", []),
                estimated_duration_seconds=st_data.get("estimated_seconds", 60),
            )
            plan.subtasks.append(subtask)
            plan.estimated_total_duration += subtask.estimated_duration_seconds

        return plan

    async def _generate_subtasks(self, understanding: dict[str, Any]) -> list[dict[str, Any]]:
        prompt = f"""
Break down this objective into 3-7 concrete, executable subtasks.

Objective: {understanding.get("goal")}
Domain: {understanding.get("domain")}
Complexity: {understanding.get("complexity")}

Each subtask should have:
- name: short descriptive name
- description: what it does
- tool: tool name if applicable (code, search, analyze, write, etc.)
- args: arguments for the tool
- depends_on: list of subtask names this depends on
- estimated_seconds: rough time estimate

Return JSON array only.
"""
        response = await self.oar.chat(
            prompt,
            task_type=TaskType.REASONING,
            temperature=0.3,
            max_tokens=2000,
        )

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return [
                {"name": "Analyze", "description": "Analyze the problem", "tool": "analyze", "estimated_seconds": 60},
                {"name": "Execute", "description": "Execute the solution", "tool": "execute", "estimated_seconds": 120},
                {"name": "Verify", "description": "Verify results", "tool": "verify", "estimated_seconds": 60},
            ]


class ToolExecutor:
    """Executes tools with monitoring and learning."""

    def __init__(self):
        self.oar = get_oar()
        self._tool_registry: dict[str, Any] = {}

    def register_tool(self, name: str, tool: Any) -> None:
        self._tool_registry[name] = tool

    async def execute(self, subtask: SubTask) -> Any:
        start_time = datetime.now(UTC)
        subtask.status = TaskStatus.IN_PROGRESS
        subtask.started_at = start_time

        try:
            tool = self._tool_registry.get(subtask.tool)
            if tool is None:
                result = await self._execute_with_ai(subtask)
            else:
                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**subtask.args)
                else:
                    result = tool(**subtask.args)

            subtask.status = TaskStatus.COMPLETED
            subtask.result = result
            subtask.completed_at = datetime.now(UTC)

            duration_ms = (subtask.completed_at - start_time).total_seconds() * 1000
            learn_tool_usage(subtask.tool or "ai", True, duration_ms, subtask.args)

            return result

        except Exception as e:
            subtask.status = TaskStatus.FAILED
            subtask.error = str(e)
            subtask.completed_at = datetime.now(UTC)
            duration_ms = (subtask.completed_at - start_time).total_seconds() * 1000
            learn_tool_usage(subtask.tool or "ai", False, duration_ms, subtask.args)
            raise

    async def _execute_with_ai(self, subtask: SubTask) -> Any:
        prompt = f"""
Execute this subtask:
Name: {subtask.name}
Description: {subtask.description}
Args: {subtask.args}

Provide a concrete, actionable result. If this requires code, write it.
If it requires analysis, provide the analysis. If it requires writing, write it.
"""
        response = await self.oar.chat(
            prompt,
            task_type=TaskType.CODE if subtask.tool == "code" else TaskType.REASONING,
            temperature=0.2,
        )
        return response.content


class AssistanceEngine:
    """Main assistance engine orchestrating the full flow."""

    def __init__(self):
        self.parser = ObjectiveParser()
        self.planner = TaskPlanner()
        self.executor = ToolExecutor()
        self.memory = get_memory_store()
        self.learning = get_learning_engine()

    async def process_objective(
        self,
        objective: str,
        mode: AssistanceMode = AssistanceMode.NORMAL,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        start_time = datetime.now(UTC)
        session_id = str(uuid.uuid4())[:8]

        context = context or {}
        context["session_id"] = session_id
        context["mode"] = mode.value

        # 1. UNDERSTAND
        if mode == AssistanceMode.BEGINNER:
            print(f"🤔 Understanding: {objective}")

        understanding = await self.parser.parse(objective, context)

        if mode == AssistanceMode.BEGINNER:
            print(f"   Goal: {understanding.get('goal')}")
            print(f"   Domain: {understanding.get('domain')}")
            print(f"   Complexity: {understanding.get('complexity')}")
            if understanding.get("questions"):
                for q in understanding["questions"]:
                    print(f"   ❓ {q}")

        # 2. PLAN
        if mode == AssistanceMode.BEGINNER:
            print("📋 Creating plan...")

        plan = await self.planner.create_plan(understanding, mode)

        if mode in (AssistanceMode.BEGINNER, AssistanceMode.NORMAL):
            print(f"   Plan: {len(plan.subtasks)} steps, ~{plan.estimated_total_duration:.0f}s")
            for st in plan.subtasks:
                dep = f" (after: {', '.join(st.depends_on)})" if st.depends_on else ""
                print(f"   • {st.name}: {st.description}{dep}")

        # 3. EXECUTE
        if mode == AssistanceMode.BEGINNER:
            confirm = input("   Proceed? (y/n): ").strip().lower()
            if confirm != "y":
                return ExecutionResult(
                    plan_id=plan.id,
                    success=False,
                    completed_subtasks=0,
                    failed_subtasks=0,
                    errors={"cancelled": "User cancelled"},
                )

        results = await self._execute_plan(plan, mode)

        # 4. DELIVER
        if mode in (AssistanceMode.BEGINNER, AssistanceMode.NORMAL):
            print(f"✅ Completed: {results.completed_subtasks}/{len(plan.subtasks)} steps")
            if results.errors:
                print(f"⚠️ Errors: {len(results.errors)}")

        # 5. LEARN
        total_duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
        learn_task_outcome(
            task_type=understanding.get("domain", "general"),
            success=results.success,
            duration_ms=total_duration_ms,
            tools_used=[st.tool for st in plan.subtasks if st.tool],
            learnings=results.learnings,
        )

        self.memory.set(
            MemoryNamespace.CONVERSATION,
            f"session_{session_id}",
            {
                "objective": objective,
                "understanding": understanding,
                "plan_id": plan.id,
                "results": {
                    "success": results.success,
                    "completed": results.completed_subtasks,
                    "failed": results.failed_subtasks,
                    "duration_ms": total_duration_ms,
                },
            },
            tier=MemoryTier.TEMPORARY,
            ttl_seconds=86400,
        )

        results.total_duration_ms = total_duration_ms
        return results

    async def _execute_plan(self, plan: Plan, mode: AssistanceMode) -> ExecutionResult:
        completed = set()
        results = {}
        errors = {}
        learnings = []

        pending = {st.id: st for st in plan.subtasks}

        while pending:
            ready = [st for st in pending.values() if all(dep in completed for dep in st.depends_on)]

            if not ready:
                for st in pending.values():
                    st.status = TaskStatus.FAILED
                    st.error = "Dependency resolution failed"
                break

            for subtask in ready:
                if mode == AssistanceMode.BEGINNER:
                    print(f"   ▶ {subtask.name}...")

                try:
                    result = await self.executor.execute(subtask)
                    results[subtask.id] = result
                    completed.add(subtask.id)

                    if mode == AssistanceMode.BEGINNER:
                        print("      ✓ Done")

                    if isinstance(result, str) and len(result) > 100:
                        learnings.append(f"{subtask.name}: {result[:200]}...")

                except Exception as e:
                    errors[subtask.id] = str(e)
                    if mode != AssistanceMode.EXPERT:
                        print(f"      ✗ Failed: {e}")

            for st in ready:
                del pending[st.id]

        success = len(errors) == 0
        return ExecutionResult(
            plan_id=plan.id,
            success=success,
            completed_subtasks=len(completed),
            failed_subtasks=len(errors),
            results=results,
            errors=errors,
            learnings=learnings,
        )


_assistance_engine: AssistanceEngine | None = None


def get_assistance_engine() -> AssistanceEngine:
    global _assistance_engine
    if _assistance_engine is None:
        _assistance_engine = AssistanceEngine()
    return _assistance_engine


async def process_objective(
    objective: str,
    mode: AssistanceMode = AssistanceMode.NORMAL,
    context: dict[str, Any] | None = None,
) -> ExecutionResult:
    engine = get_assistance_engine()
    return await engine.process_objective(objective, mode, context)


def set_mode(mode: AssistanceMode) -> None:
    get_memory_store().set(
        MemoryNamespace.PREFERENCES,
        "assistance_mode",
        mode.value,
        tier=MemoryTier.PERMANENT,
    )


def get_mode() -> AssistanceMode:
    mode_str = get_memory_store().get(MemoryNamespace.PREFERENCES, "assistance_mode", "normal")
    return AssistanceMode(mode_str)
