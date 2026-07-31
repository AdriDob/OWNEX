from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from threading import Lock
from concurrent.futures import ThreadPoolExecutor


class AgentRole(str, Enum):
    RECON = "recon"
    FUZZER = "fuzzer"
    EXPLOITER = "exploiter"
    VALIDATOR = "validator"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SwarmStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class SwarmAgent:
    id: str
    role: AgentRole
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"
    current_task: str | None = None
    performance_score: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SwarmTask:
    id: str
    name: str
    role: AgentRole
    payload: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    max_retries: int = 3
    priority: int = 0


@dataclass(slots=True)
class Swarm:
    id: str
    target: str
    objective: str
    status: SwarmStatus = SwarmStatus.INITIALIZING
    agents: dict[str, SwarmAgent] = field(default_factory=dict)
    tasks: dict[str, SwarmTask] = field(default_factory=dict)
    graph_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SwarmCoordinator:
    def __init__(self, max_workers: int = 10):
        self._swarms: dict[str, Swarm] = {}
        self._task_executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = Lock()
        self._agent_executors: dict[AgentRole, Callable] = {}
        self._completion_callbacks: list[Callable] = []
        self._running = True

    def register_executor(self, role: AgentRole, executor: Callable) -> None:
        self._agent_executors[role] = executor

    def on_task_complete(self, callback: Callable) -> None:
        self._completion_callbacks.append(callback)

    def create_swarm(self, target: str, objective: str, roles: list[AgentRole]) -> str:
        swarm_id = f"swarm_{uuid.uuid4().hex[:12]}"
        swarm = Swarm(id=swarm_id, target=target, objective=objective)
        for role in roles:
            agent_id = f"{swarm_id}_{role.value}_{uuid.uuid4().hex[:6]}"
            agent = SwarmAgent(id=agent_id, role=role)
            swarm.agents[agent_id] = agent
        with self._lock:
            self._swarms[swarm_id] = swarm
        return swarm_id

    def decompose_objective(self, swarm_id: str, objective: str) -> list[SwarmTask]:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return []

        task_templates = self._get_task_templates(objective)
        tasks = []
        name_to_id = {}
        for i, template in enumerate(task_templates):
            task_id = f"{swarm.id}_task_{template['name']}"
            name_to_id[template["name"]] = task_id
            task = SwarmTask(
                id=task_id,
                name=template["name"],
                role=template["role"],
                payload=template["payload"],
                dependencies=template.get("dependencies", []),
                priority=template.get("priority", 0),
            )
            tasks.append(task)
            swarm.tasks[task.id] = task
        # Resolve dependencies to IDs
        for task in tasks:
            task.dependencies = [name_to_id.get(d, d) for d in task.dependencies]
        return tasks

    def _get_task_templates(self, objective: str) -> list[dict[str, Any]]:
        obj_lower = objective.lower()
        if "recon" in obj_lower or "map" in obj_lower:
            return [
                {
                    "name": "subdomain_enum",
                    "role": AgentRole.RECON,
                    "payload": {"action": "subdomain_enum"},
                    "priority": 10,
                },
                {
                    "name": "port_scan",
                    "role": AgentRole.RECON,
                    "payload": {"action": "port_scan"},
                    "dependencies": ["subdomain_enum"],
                    "priority": 9,
                },
                {
                    "name": "tech_fingerprint",
                    "role": AgentRole.RECON,
                    "payload": {"action": "tech_fingerprint"},
                    "dependencies": ["port_scan"],
                    "priority": 8,
                },
                {
                    "name": "endpoint_discovery",
                    "role": AgentRole.RECON,
                    "payload": {"action": "endpoint_discovery"},
                    "dependencies": ["tech_fingerprint"],
                    "priority": 7,
                },
            ]
        elif "exploit" in obj_lower or "vuln" in obj_lower:
            return [
                {"name": "vuln_scan", "role": AgentRole.FUZZER, "payload": {"action": "vuln_scan"}, "priority": 10},
                {
                    "name": "exploit_gen",
                    "role": AgentRole.EXPLOITER,
                    "payload": {"action": "exploit_gen"},
                    "dependencies": ["vuln_scan"],
                    "priority": 9,
                },
                {
                    "name": "poc_gen",
                    "role": AgentRole.EXPLOITER,
                    "payload": {"action": "poc_gen"},
                    "dependencies": ["exploit_gen"],
                    "priority": 8,
                },
            ]
        elif "validate" in obj_lower or "verify" in obj_lower:
            return [
                {
                    "name": "poc_validate",
                    "role": AgentRole.VALIDATOR,
                    "payload": {"action": "poc_validate"},
                    "priority": 10,
                },
                {
                    "name": "evidence_collect",
                    "role": AgentRole.VALIDATOR,
                    "payload": {"action": "evidence_collect"},
                    "dependencies": ["poc_validate"],
                    "priority": 9,
                },
            ]
        return [
            {
                "name": "generic_task",
                "role": AgentRole.SPECIALIST,
                "payload": {"action": "custom", "objective": objective},
                "priority": 5,
            }
        ]

    def assign_tasks(self, swarm_id: str) -> int:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return 0
        assigned = 0
        for task in swarm.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps_done = all(swarm.tasks[d].status == TaskStatus.COMPLETED for d in task.dependencies)
            if not deps_done:
                continue
            available = [a for a in swarm.agents.values() if a.role == task.role and a.status == "idle"]
            if not available:
                continue
            agent = max(available, key=lambda a: a.performance_score)
            task.status = TaskStatus.ASSIGNED
            task.assigned_agent = agent.id
            agent.status = "busy"
            agent.current_task = task.id
            self._execute_task_async(swarm_id, task.id)
            assigned += 1
        return assigned

    def _execute_task_async(self, swarm_id: str, task_id: str) -> None:
        def run():
            self._execute_task(swarm_id, task_id)

        self._task_executor.submit(run)

    def _execute_task(self, swarm_id: str, task_id: str) -> None:
        swarm = self._swarms.get(swarm_id)
        task = swarm.tasks.get(task_id) if swarm else None
        if not task or not task.assigned_agent:
            return
        agent = swarm.agents.get(task.assigned_agent)
        executor = self._agent_executors.get(task.role)
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        if agent:
            agent.status = "busy"
        try:
            if executor:
                result = executor(task.payload, agent.metadata if agent else {})
            else:
                result = {"status": "simulated", "data": f"completed {task.name}"}
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            if agent:
                agent.performance_score = min(2.0, agent.performance_score * 1.05)
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            if agent:
                agent.performance_score = max(0.1, agent.performance_score * 0.9)
        finally:
            if agent:
                agent.status = "idle"
                agent.current_task = None
            for cb in self._completion_callbacks:
                try:
                    cb(swarm_id, task)
                except Exception:
                    pass

    def get_swarm_status(self, swarm_id: str) -> dict[str, Any] | None:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return None
        task_counts = defaultdict(int)
        for t in swarm.tasks.values():
            task_counts[t.status.value] += 1
        return {
            "swarm_id": swarm.id,
            "target": swarm.target,
            "objective": swarm.objective,
            "status": swarm.status.value,
            "agents": len(swarm.agents),
            "tasks": dict(task_counts),
            "progress": task_counts[TaskStatus.COMPLETED.value] / max(1, len(swarm.tasks)),
        }

    def start_swarm(self, swarm_id: str) -> bool:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False
        self.decompose_objective(swarm_id, swarm.objective)
        swarm.status = SwarmStatus.ACTIVE
        swarm.started_at = datetime.utcnow()
        self.assign_tasks(swarm_id)
        return True

    def pause_swarm(self, swarm_id: str) -> bool:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False
        swarm.status = SwarmStatus.PAUSED
        return True

    def shutdown(self) -> None:
        self._running = False
        self._task_executor.shutdown(wait=True)


coordinator = SwarmCoordinator()
