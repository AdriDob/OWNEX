"""
OWNEX Operations Research Core - Motor de planificación y optimización
Decide QUÉ hacer, CUÁNDO, con QUÉ AGENTE, por CUÁNTO TIEMPO.
"""

import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .knowledge_core import (
    KnowledgeGraph,
    OutcomeType,
    TaskOutcome,
    TaskType,
    get_knowledge_graph,
)


class TaskPriority(Enum):
    CRITICAL = 100
    HIGH = 75
    MEDIUM = 50
    LOW = 25
    BACKGROUND = 10


@dataclass
class TaskCandidate:
    """Una tarea candidata para ejecución"""

    task_id: str
    task_type: TaskType
    platform: str
    description: str
    estimated_duration: float  # segundos
    estimated_cost: float  # USD
    estimated_reward: float  # USD esperado
    confidence: float  # 0-1
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    deadline: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expected_value(self) -> float:
        """Valor esperado bruto"""
        return self.estimated_reward * self.confidence

    @property
    def expected_roi(self) -> float:
        """ROI esperado"""
        if self.estimated_cost <= 0:
            return 0.0
        return self.expected_value / self.estimated_cost

    @property
    def expected_rate(self) -> float:
        """Valor esperado por hora"""
        hours = self.estimated_duration / 3600
        if hours <= 0:
            return 0.0
        return self.expected_value / hours


@dataclass
class ResourceBudget:
    """Presupuesto de recursos para una ventana de planificación"""

    max_compute_hours: float
    max_cost_usd: float
    max_parallel_tasks: int
    preferred_agents: list[str] = field(default_factory=list)
    excluded_platforms: list[str] = field(default_factory=list)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None


@dataclass
class ScheduledTask:
    """Tarea programada con asignación de recursos"""

    candidate: TaskCandidate
    assigned_agent: str
    start_time: datetime
    end_time: datetime
    expected_value: float
    confidence: float
    rationale: str


class OperationsResearchEngine:
    """
    Motor de Investigación Operativa para OWNEX.

    Resuelve: dado un conjunto de tareas candidatas y recursos limitados,
    ¿cuál es la secuencia óptima de ejecución?
    """

    def __init__(self, kg: KnowledgeGraph | None = None):
        self.kg = kg or get_knowledge_graph()
        self._task_queue: list[TaskCandidate] = []
        self._running_tasks: dict[str, ScheduledTask] = {}
        self._completed_tasks: list[ScheduledTask] = []

    def add_task(self, candidate: TaskCandidate) -> None:
        """Añade tarea candidata a la cola"""
        heapq.heappush(self._task_queue, (-candidate.expected_rate, candidate.task_id, candidate))

    def add_tasks(self, candidates: list[TaskCandidate]) -> None:
        for c in candidates:
            self.add_task(c)

    def plan(self, budget: ResourceBudget, candidates: list[TaskCandidate] | None = None) -> list[ScheduledTask]:
        """
        Planifica la ejecución óptima dentro del presupuesto.

        Usa heurística greedy con backtracking limitado:
        1. Estima valor esperado por cada (tarea, agente) usando KnowledgeGraph
        2. Ordena por valor esperado por hora (rate)
        3. Asigna recursos respetando dependencias y límites
        4. Ajusta por ventana temporal y deadlines
        """
        if candidates:
            work_queue = list(candidates)
        else:
            work_queue = [c for _, _, c in self._task_queue]

        # Enriquecer con estimaciones basadas en conocimiento
        enriched = self._enrich_candidates(work_queue)

        # Filtrar por presupuesto y exclusiones
        feasible = self._filter_feasible(enriched, budget)

        # Ordenar por score compuesto
        scored = self._score_candidates(feasible, budget)

        # Asignar agentes y tiempos (greedy con lookahead)
        schedule = self._schedule_greedy(scored, budget)

        return schedule

    def _enrich_candidates(self, candidates: list[TaskCandidate]) -> list[TaskCandidate]:
        """Mejora estimaciones usando histórico del KnowledgeGraph"""
        enriched = []
        for c in candidates:
            # Estimar recompensa basada en histórico de plataforma
            plat = self.kg.get_platform_expertise(c.platform)
            if plat and plat.total_tasks > 5:
                # Ajustar confianza y recompensa esperada
                historical_rate = plat.expected_value_per_hour
                if historical_rate > 0:
                    est_reward = historical_rate * (c.estimated_duration / 3600)
                    # Blend con estimación original
                    c.estimated_reward = 0.7 * c.estimated_reward + 0.3 * est_reward
                    c.confidence = min(1.0, c.confidence * 1.1)  # boost confidence

            enriched.append(c)
        return enriched

    def _filter_feasible(self, candidates: list[TaskCandidate], budget: ResourceBudget) -> list[TaskCandidate]:
        feasible = []
        for c in candidates:
            if c.platform in budget.excluded_platforms:
                continue
            if c.estimated_cost > budget.max_cost_usd:
                continue
            if budget.time_window_start and c.deadline:
                if c.deadline < budget.time_window_start:
                    continue
            if budget.time_window_end and c.deadline:
                if c.deadline > budget.time_window_end:
                    continue
            feasible.append(c)
        return feasible

    def _score_candidates(
        self, candidates: list[TaskCandidate], budget: ResourceBudget
    ) -> list[tuple[float, TaskCandidate]]:
        """Score compuesto: rate * confidence * priority * urgency * agent_fit"""
        scored = []
        now = datetime.utcnow()

        for c in candidates:
            # Base rate
            rate = c.expected_rate

            # Confidence weight
            conf_weight = c.confidence

            # Priority weight
            pri_weight = c.priority.value / 100.0

            # Urgency (deadline proximity)
            urg_weight = 1.0
            if c.deadline:
                hours_until = (c.deadline - now).total_seconds() / 3600
                if hours_until > 0:
                    urg_weight = min(2.0, 24.0 / max(hours_until, 1.0))

            # Best agent fit
            best_agent = self.kg.get_best_agent_for(c.platform, c.task_type)
            agent_fit = 1.0
            if best_agent and best_agent in budget.preferred_agents:
                agent_fit = 1.2
            elif best_agent:
                agent_fit = 1.1

            # Composite score
            score = rate * conf_weight * pri_weight * urg_weight * agent_fit
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _schedule_greedy(
        self, scored: list[tuple[float, TaskCandidate]], budget: ResourceBudget
    ) -> list[ScheduledTask]:
        """Asignación greedy con simulación de paralelismo"""
        schedule = []
        used_cost = 0.0
        used_hours = 0.0
        agent_timelines: dict[str, datetime] = defaultdict(lambda: datetime.utcnow())
        parallel_slots = budget.max_parallel_tasks

        # Agentes disponibles
        available_agents = budget.preferred_agents or list(self.kg._agent_cache.keys())
        if not available_agents:
            available_agents = ["opencode", "hermes", "claude-code", "fcc"]

        for score, candidate in scored:
            if used_cost >= budget.max_cost_usd:
                break
            if used_hours >= budget.max_compute_hours:
                break

            # Seleccionar mejor agente disponible
            agent = self._select_best_agent(candidate, available_agents, agent_timelines)
            if not agent:
                continue

            # Calcular tiempo de inicio (respetando dependencias y disponibilidad agente)
            start = self._calculate_start_time(candidate, agent, agent_timelines, budget)
            end = start + timedelta(seconds=candidate.estimated_duration)

            # Verificar presupuesto
            if used_cost + candidate.estimated_cost > budget.max_cost_usd:
                continue
            if (end - datetime.utcnow()).total_seconds() / 3600 > budget.max_compute_hours:
                continue

            # Verificar paralelismo
            concurrent = sum(1 for s in schedule if s.start_time <= start < s.end_time)
            if concurrent >= parallel_slots:
                continue

            # Crear tarea programada
            scheduled = ScheduledTask(
                candidate=candidate,
                assigned_agent=agent,
                start_time=start,
                end_time=end,
                expected_value=candidate.expected_value,
                confidence=candidate.confidence,
                rationale=f"Score: {score:.2f}, Agent fit: {agent}, Rate: {candidate.expected_rate:.2f}/hr",
            )

            schedule.append(scheduled)
            used_cost += candidate.estimated_cost
            used_hours += candidate.estimated_duration / 3600
            agent_timelines[agent] = end

        return schedule

    def _select_best_agent(
        self, candidate: TaskCandidate, available: list[str], timelines: dict[str, datetime]
    ) -> str | None:
        """Selecciona el mejor agente para la tarea"""
        best_agent = self.kg.get_best_agent_for(candidate.platform, candidate.task_type)

        if best_agent and best_agent in available:
            return best_agent

        # Fallback: agente disponible con mejor perfil
        best = None
        best_score = -1
        for agent_name in available:
            profile = self.kg.get_agent_profile(agent_name)
            if not profile:
                score = 0.5  # unknown
            else:
                score = profile.efficiency * profile.success_rate

            if score > best_score:
                best_score = score
                best = agent_name

        return best

    def _calculate_start_time(
        self, candidate: TaskCandidate, agent: str, timelines: dict[str, datetime], budget: ResourceBudget
    ) -> datetime:
        """Calcula hora de inicio respetando dependencias y disponibilidad"""
        earliest = max(timelines[agent], budget.time_window_start or datetime.utcnow())

        # Verificar dependencias
        for dep_id in candidate.dependencies:
            for scheduled in self._completed_tasks:
                if scheduled.candidate.task_id == dep_id:
                    earliest = max(earliest, scheduled.end_time)
                    break

        return earliest

    def execute_plan(self, schedule: list[ScheduledTask]) -> list[TaskOutcome]:
        """
        Ejecuta el plan y registra resultados en KnowledgeGraph.
        En producción, esto dispararía la ejecución real de agentes.
        """
        outcomes = []
        for scheduled in schedule:
            # Simular ejecución (en producción: lanzar agente real)
            outcome = self._simulate_execution(scheduled)
            outcomes.append(outcome)

            # Registrar en KnowledgeGraph
            self.kg.record_outcome(outcome)

            # Actualizar decisión si existe
            # (requiere tracking de decision_id)

        self._completed_tasks.extend(schedule)
        return outcomes

    def _simulate_execution(self, scheduled: ScheduledTask) -> TaskOutcome:
        """Simula ejecución para testing. Reemplazar por llamada real a agente."""
        import random

        c = scheduled.candidate
        success = random.random() < c.confidence

        return TaskOutcome(
            task_id=c.task_id,
            task_type=c.task_type,
            platform=c.platform,
            agent=scheduled.assigned_agent,
            started_at=scheduled.start_time,
            completed_at=scheduled.end_time,
            duration_seconds=c.estimated_duration,
            cost_usd=c.estimated_cost,
            outcome=OutcomeType.SUCCESS if success else OutcomeType.FAILURE,
            result_data={"simulated": True},
            reward_usd=c.estimated_reward if success else 0,
            confidence=c.confidence,
            failure_reason=None if success else "simulated_failure",
        )

    def reoptimize(self, budget: ResourceBudget, new_candidates: list[TaskCandidate]) -> list[ScheduledTask]:
        """Re-optimiza el plan con nueva información"""
        # Combinar pendientes + nuevos
        all_candidates = [s.candidate for s in self._task_queue] + new_candidates
        return self.plan(budget, all_candidates)

    def get_utilization_stats(self) -> dict[str, Any]:
        """Estadísticas de utilización de recursos"""
        if not self._completed_tasks:
            return {"tasks_completed": 0}

        total_reward = sum(s.expected_value for s in self._completed_tasks)
        total_cost = sum(s.candidate.estimated_cost for s in self._completed_tasks)
        total_hours = sum((s.end_time - s.start_time).total_seconds() / 3600 for s in self._completed_tasks)

        by_agent = defaultdict(lambda: {"tasks": 0, "reward": 0.0, "hours": 0.0})
        for s in self._completed_tasks:
            by_agent[s.assigned_agent]["tasks"] += 1
            by_agent[s.assigned_agent]["reward"] += s.expected_value
            by_agent[s.assigned_agent]["hours"] += (s.end_time - s.start_time).total_seconds() / 3600

        return {
            "tasks_completed": len(self._completed_tasks),
            "total_expected_reward": total_reward,
            "total_cost": total_cost,
            "total_compute_hours": total_hours,
            "avg_roi": total_reward / total_cost if total_cost > 0 else 0,
            "avg_rate_per_hour": total_reward / total_hours if total_hours > 0 else 0,
            "by_agent": dict(by_agent),
        }


class ContinuousPlanner:
    """
    Planificador continuo que re-evalúa y ajusta el plan
    basado en resultados reales y nuevas oportunidades.
    """

    def __init__(self, engine: OperationsResearchEngine):
        self.engine = engine
        self.current_budget: ResourceBudget | None = None
        self.current_schedule: list[ScheduledTask] = []
        self.last_replan = datetime.utcnow()
        self.replan_interval = timedelta(minutes=15)

    def set_budget(self, budget: ResourceBudget):
        self.current_budget = budget
        self.replan()

    def add_opportunity(self, candidate: TaskCandidate):
        """Nueva oportunidad detectada - trigger re-evaluación"""
        self.engine.add_task(candidate)
        if self._should_replan():
            self.replan()

    def _should_replan(self) -> bool:
        return datetime.utcnow() - self.last_replan > self.replan_interval

    def replan(self) -> list[ScheduledTask]:
        if not self.current_budget:
            return []

        # Obtener tareas pendientes (no ejecutadas)
        pending = [c for _, _, c in self.engine._task_queue]

        # Re-planificar
        new_schedule = self.engine.plan(self.current_budget, pending)
        self.current_schedule = new_schedule
        self.last_replan = datetime.utcnow()

        return new_schedule

    def on_task_complete(self, outcome: TaskOutcome):
        """Callback cuando termina una tarea - aprende y re-evalúa"""
        # El KnowledgeGraph ya se actualizó en engine.execute_plan
        # Aquí podríamos trigger re-plan inmediato si el resultado
        # difiere significativamente de lo esperado
        if self._should_replan():
            self.replan()

    def get_next_action(self) -> ScheduledTask | None:
        """Próxima acción a ejecutar"""
        if not self.current_schedule:
            self.replan()

        now = datetime.utcnow()
        for s in self.current_schedule:
            if s.start_time <= now < s.end_time:
                return s
            if s.start_time > now:
                return s  # próxima programada

        return None


# Funciones de conveniencia
def create_default_budget(
    max_hours: float = 8.0, max_cost: float = 50.0, max_parallel: int = 3, agents: list[str] = None
) -> ResourceBudget:
    return ResourceBudget(
        max_compute_hours=max_hours,
        max_cost_usd=max_cost,
        max_parallel_tasks=max_parallel,
        preferred_agents=agents or ["opencode", "hermes", "fcc", "claude-code"],
    )


def create_candidate(
    task_id: str,
    task_type: TaskType,
    platform: str,
    description: str,
    duration_minutes: float,
    cost_usd: float,
    reward_usd: float,
    confidence: float = 0.7,
    priority: TaskPriority = TaskPriority.MEDIUM,
) -> TaskCandidate:
    return TaskCandidate(
        task_id=task_id,
        task_type=task_type,
        platform=platform,
        description=description,
        estimated_duration=duration_minutes * 60,
        estimated_cost=cost_usd,
        estimated_reward=reward_usd,
        confidence=confidence,
        priority=priority,
    )
