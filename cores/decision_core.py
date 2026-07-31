"""
OWNEX Decision Theory Core - Teoría de decisiones para selección óptima
Calcula VALOR ESPERADO real y decide qué tarea maximiza retorno.
"""

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .knowledge_core import KnowledgeGraph, OutcomeType, TaskType, get_knowledge_graph
from .operations_core import TaskCandidate


class DecisionPolicy(Enum):
    """Políticas de decisión disponibles"""

    MAX_EXPECTED_VALUE = "max_ev"  # Maximizar valor esperado puro
    MAX_EXPECTED_UTILITY = "max_eu"  # Utilidad esperada (risk-aware)
    MAX_SHARPE = "max_sharpe"  # Ratio retorno/riesgo
    MIN_REGRET = "min_regret"  # Minimizar arrepentimiento máximo
    THOMPSON_SAMPLING = "thompson"  # Exploración/explotación bayesiana
    UPPER_CONFIDENCE_BOUND = "ucb"  # UCB para bandidos multi-brazo


class RiskProfile(Enum):
    """Perfiles de riesgo"""

    CONSERVATIVE = "conservative"  # Evita varianza alta
    BALANCED = "balanced"  # Balance estándar
    AGGRESSIVE = "aggressive"  # Busca alto retorno, acepta riesgo


@dataclass
class BeliefDistribution:
    """Distribución de creencia bayesiana sobre recompensa"""

    # Usamos Beta para recompensa binaria (éxito/fracaso) o Gamma para continua
    alpha: float = 1.0  # éxitos + prior
    beta: float = 1.0  # fracasos + prior
    reward_sum: float = 0.0
    reward_sq_sum: float = 0.0
    count: int = 0

    @property
    def mean(self) -> float:
        if self.count == 0:
            return 0.0
        return self.reward_sum / self.count

    @property
    def variance(self) -> float:
        if self.count <= 1:
            return float("inf")
        mean = self.mean
        return (self.reward_sq_sum / self.count) - (mean * mean)

    @property
    def std(self) -> float:
        var = self.variance
        return math.sqrt(var) if var > 0 else 0.0

    def sample(self) -> float:
        """Thompson sampling: sample de la distribución posterior"""
        if self.count == 0:
            return 0.0
        # Aproximación normal para recompensa continua
        import random

        return max(0.0, self.mean + self.std * (random.random() - 0.5) * 2)

    def update(self, reward: float):
        self.reward_sum += reward
        self.reward_sq_sum += reward * reward
        self.count += 1
        if reward > 0:
            self.alpha += 1
        else:
            self.beta += 1

    def ucb_value(self, total_pulls: int, c: float = 2.0) -> float:
        """Upper Confidence Bound"""
        if self.count == 0:
            return float("inf")
        return self.mean + c * math.sqrt(math.log(total_pulls) / self.count)


@dataclass
class TaskBelief:
    """Creencia sobre una tarea específica (plataforma + tipo + agente)"""

    key: str
    platform: str
    task_type: TaskType
    agent: str
    reward_belief: BeliefDistribution = field(default_factory=BeliefDistribution)
    duration_belief: BeliefDistribution = field(default_factory=BeliefDistribution)
    cost_belief: BeliefDistribution = field(default_factory=BeliefDistribution)
    success_rate: BeliefDistribution = field(default_factory=BeliefDistribution)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def expected_reward(self) -> float:
        return self.reward_belief.mean

    @property
    def expected_duration(self) -> float:
        return max(60.0, self.duration_belief.mean)  # min 1 min

    @property
    def expected_cost(self) -> float:
        return max(0.01, self.cost_belief.mean)

    @property
    def success_probability(self) -> float:
        return self.success_rate.mean if self.success_rate.count > 0 else 0.5

    @property
    def expected_value(self) -> float:
        """EV = P(success) * E[reward|success] - E[cost]"""
        return self.success_probability * self.expected_reward - self.expected_cost

    @property
    def expected_roi(self) -> float:
        cost = self.expected_cost
        if cost <= 0:
            return 0.0
        return self.expected_value / cost

    @property
    def sharpe_ratio(self) -> float:
        """Ratio Sharpe aproximado"""
        std = self.reward_belief.std
        if std <= 0:
            return float("inf") if self.expected_value > 0 else 0.0
        return self.expected_value / std

    def update(self, reward: float, duration: float, cost: float, success: bool):
        self.reward_belief.update(reward)
        self.duration_belief.update(duration)
        self.cost_belief.update(cost)
        self.success_rate.update(1.0 if success else 0.0)
        self.last_updated = datetime.utcnow()


@dataclass
class DecisionContext:
    """Contexto para la decisión actual"""

    available_tasks: list[TaskCandidate]
    budget_usd: float
    time_horizon_hours: float
    risk_profile: RiskProfile = RiskProfile.BALANCED
    policy: DecisionPolicy = DecisionPolicy.MAX_EXPECTED_UTILITY
    current_time: datetime = field(default_factory=datetime.utcnow)
    agent_availability: dict[str, bool] = field(default_factory=dict)
    platform_access: dict[str, bool] = field(default_factory=dict)
    exploration_budget: float = 0.1  # % del presupuesto para exploración


@dataclass
class Decision:
    """Resultado de una decisión"""

    selected_task: TaskCandidate | None
    selected_agent: str
    expected_value: float
    confidence: float
    rationale: str
    alternatives: list[tuple[TaskCandidate, str, float]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    """
    Motor de Teoría de Decisiones para OWNEX.

    Dado un conjunto de tareas candidatas y creencias bayesianas,
    selecciona la acción que maximiza la utilidad esperada.
    """

    def __init__(self, kg: KnowledgeGraph | None = None):
        self.kg = kg or get_knowledge_graph()
        self._beliefs: dict[str, TaskBelief] = {}
        self._total_decisions = 0
        self._decision_history: list[Decision] = []

    def _get_belief_key(self, platform: str, task_type: TaskType, agent: str) -> str:
        return f"{platform}|{task_type.value}|{agent}"

    def get_belief(self, platform: str, task_type: TaskType, agent: str) -> TaskBelief:
        key = self._get_belief_key(platform, task_type, agent)
        if key not in self._beliefs:
            self._beliefs[key] = TaskBelief(key=key, platform=platform, task_type=task_type, agent=agent)
            # Inicializar con datos del KnowledgeGraph
            self._initialize_from_kg(self._beliefs[key])
        return self._beliefs[key]

    def _initialize_from_kg(self, belief: TaskBelief):
        """Inicializa creencias desde KnowledgeGraph histórico"""
        plat = self.kg.get_platform_expertise(belief.platform)
        if plat and plat.total_tasks > 0:
            # Usar datos históricos como prior
            for _ in range(min(plat.total_tasks, 50)):
                # Simular actualizaciones basadas en stats agregados
                avg_reward = plat.total_reward / plat.total_tasks if plat.total_tasks > 0 else 0
                avg_duration = plat.avg_duration if plat.avg_duration > 0 else 3600
                avg_cost = plat.total_cost / plat.total_tasks if plat.total_tasks > 0 else 1

                belief.reward_belief.update(avg_reward)
                belief.duration_belief.update(avg_duration)
                belief.cost_belief.update(avg_cost)
                belief.success_rate.update(1.0 if plat.success_rate > 0.5 else 0.0)

    def update_belief(self, outcome) -> None:
        """Actualiza creencias con resultado real (TaskOutcome del KG)"""
        self._get_belief_key(outcome.platform, outcome.task_type, outcome.agent)
        belief = self.get_belief(outcome.platform, outcome.task_type, outcome.agent)

        belief.update(
            reward=outcome.reward_usd,
            duration=outcome.duration_seconds,
            cost=outcome.cost_usd,
            success=outcome.outcome == OutcomeType.SUCCESS,
        )

    def evaluate_candidate(self, candidate: TaskCandidate, agent: str) -> tuple[float, float, dict]:
        """
        Evalúa un candidato con un agente específico.
        Returns: (expected_utility, confidence, details)
        """
        belief = self.get_belief(candidate.platform, candidate.task_type, agent)

        # Valor base
        base_ev = belief.expected_value

        # Ajustar por confianza del candidato (información específica de la tarea)
        adjusted_ev = base_ev * candidate.confidence

        # Ajustar por prioridad
        priority_mult = candidate.priority.value / 50.0  # MEDIUM = 1.0
        adjusted_ev *= priority_mult

        # Confianza combinada
        combined_confidence = (belief.success_rate.mean + candidate.confidence) / 2

        details = {
            "base_ev": base_ev,
            "belief_success_rate": belief.success_probability,
            "belief_expected_reward": belief.expected_reward,
            "belief_expected_cost": belief.expected_cost,
            "belief_expected_duration": belief.expected_duration,
            "candidate_confidence": candidate.confidence,
            "priority_multiplier": priority_mult,
            "combined_confidence": combined_confidence,
            "belief_count": belief.reward_belief.count,
        }

        return adjusted_ev, combined_confidence, details

    def decide(self, context: DecisionContext) -> Decision:
        """
        Decide la mejor acción según la política configurada.
        """
        self._total_decisions += 1

        # Filtrar tareas factibles
        feasible = self._filter_feasible(context)

        if not feasible:
            return Decision(
                selected_task=None,
                selected_agent="none",
                expected_value=0.0,
                confidence=0.0,
                rationale="No feasible tasks within budget/constraints",
            )

        # Evaluar cada (tarea, agente) factible
        evaluations = []
        for candidate in feasible:
            for agent in self._get_available_agents(candidate, context):
                ev, conf, details = self.evaluate_candidate(candidate, agent)

                # Calcular score según política
                score = self._score_by_policy(ev, conf, details, candidate, agent, context)

                evaluations.append((score, candidate, agent, ev, conf, details))

        if not evaluations:
            return Decision(
                selected_task=None,
                selected_agent="none",
                expected_value=0.0,
                confidence=0.0,
                rationale="No valid agent-task combinations",
            )

        # Ordenar por score
        evaluations.sort(key=lambda x: x[0], reverse=True)

        best_score, best_candidate, best_agent, best_ev, best_conf, best_details = evaluations[0]

        # Construir alternativas para transparencia
        alternatives = [(c, a, ev) for _, c, a, ev, _, _ in evaluations[1:6]]

        rationale = self._build_rationale(best_candidate, best_agent, best_ev, best_conf, best_details, context.policy)

        decision = Decision(
            selected_task=best_candidate,
            selected_agent=best_agent,
            expected_value=best_ev,
            confidence=best_conf,
            rationale=rationale,
            alternatives=alternatives,
            metadata={
                "policy": context.policy.value,
                "risk_profile": context.risk_profile.value,
                "total_evaluated": len(evaluations),
                "decision_number": self._total_decisions,
                "best_score": best_score,
            },
        )

        self._decision_history.append(decision)
        return decision

    def _filter_feasible(self, context: DecisionContext) -> list[TaskCandidate]:
        feasible = []
        for c in context.available_tasks:
            # Presupuesto
            if c.estimated_cost > context.budget_usd:
                continue
            # Tiempo
            if c.estimated_duration > context.time_horizon_hours * 3600:
                continue
            # Plataforma accesible
            if context.platform_access and not context.platform_access.get(c.platform, True):
                continue
            feasible.append(c)
        return feasible

    def _get_available_agents(self, candidate: TaskCandidate, context: DecisionContext) -> list[str]:
        if context.agent_availability:
            return [a for a, avail in context.agent_availability.items() if avail]

        # Default: todos los agentes conocidos
        agents = list(self.kg._agent_cache.keys())
        if not agents:
            agents = ["opencode", "hermes", "fcc", "claude-code"]

        # Preferir mejor agente para esta plataforma/tipo
        best = self.kg.get_best_agent_for(candidate.platform, candidate.task_type)
        if best and best in agents:
            agents.remove(best)
            agents.insert(0, best)

        return agents

    def _score_by_policy(
        self, ev: float, conf: float, details: dict, candidate: TaskCandidate, agent: str, context: DecisionContext
    ) -> float:
        """Calcula score según política de decisión"""
        policy = context.policy
        risk = context.risk_profile

        if policy == DecisionPolicy.MAX_EXPECTED_VALUE:
            return ev

        elif policy == DecisionPolicy.MAX_EXPECTED_UTILITY:
            # Utilidad con aversión al riesgo
            # U = EV - lambda * Var
            variance = details.get("belief_variance", 1.0)
            lambda_risk = {"conservative": 2.0, "balanced": 1.0, "aggressive": 0.3}[risk.value]
            return ev - lambda_risk * variance / max(details.get("belief_count", 1), 1)

        elif policy == DecisionPolicy.MAX_SHARPE:
            sharpe = details.get("sharpe", 0)
            return sharpe * conf

        elif policy == DecisionPolicy.MIN_REGRET:
            # Minimax regret: peor caso si elegimos esto vs la mejor alternativa
            # Approximación: penalizar opciones con alta varianza
            variance = details.get("belief_variance", 1.0)
            return ev - math.sqrt(variance / max(details.get("belief_count", 1), 1))

        elif policy == DecisionPolicy.THOMPSON_SAMPLING:
            # Sample de la distribución posterior
            belief = self.get_belief(candidate.platform, candidate.task_type, agent)
            sampled_reward = belief.reward_belief.sample()
            sampled_ev = (belief.success_probability * sampled_reward - belief.expected_cost) * candidate.confidence
            return sampled_ev

        elif policy == DecisionPolicy.UPPER_CONFIDENCE_BOUND:
            belief = self.get_belief(candidate.platform, candidate.task_type, agent)
            ucb = belief.reward_belief.ucb_value(self._total_decisions)
            # Convertir a EV aproximado
            return (belief.success_probability * ucb - belief.expected_cost) * candidate.confidence

        return ev

    def _build_rationale(
        self, candidate: TaskCandidate, agent: str, ev: float, conf: float, details: dict, policy: DecisionPolicy
    ) -> str:
        parts = [
            f"Policy: {policy.value}",
            f"EV: ${ev:.2f}/hr (base: ${details['base_ev']:.2f})",
            f"Confidence: {conf:.1%} (belief: {details['belief_success_rate']:.1%}, task: {details['candidate_confidence']:.1%})",
            f"Historical data: {details['belief_count']} samples",
            f"Agent {agent} fit for {candidate.platform}/{candidate.task_type.value}",
        ]
        return " | ".join(parts)

    def get_decision_stats(self) -> dict[str, Any]:
        if not self._decision_history:
            return {"decisions": 0}

        recent = self._decision_history[-100:]
        return {
            "total_decisions": self._total_decisions,
            "recent_avg_ev": statistics.mean(d.expected_value for d in recent),
            "recent_avg_confidence": statistics.mean(d.confidence for d in recent),
            "policy_distribution": self._policy_distribution(),
            "agent_selection_counts": self._agent_selection_counts(),
        }

    def _policy_distribution(self) -> dict[str, int]:
        dist = defaultdict(int)
        for d in self._decision_history:
            dist[d.metadata.get("policy", "unknown")] += 1
        return dict(dist)

    def _agent_selection_counts(self) -> dict[str, int]:
        counts = defaultdict(int)
        for d in self._decision_history:
            counts[d.selected_agent] += 1
        return dict(counts)


class BayesianBandit:
    """
    Multi-armed bandit bayesiano para exploración/explotación
    en selección continua de tareas.
    """

    def __init__(self, kg: KnowledgeGraph | None = None):
        self.kg = kg or get_knowledge_graph()
        self._arms: dict[str, BeliefDistribution] = {}
        self._total_pulls = 0

    def _arm_key(self, platform: str, task_type: TaskType, agent: str) -> str:
        return f"{platform}|{task_type.value}|{agent}"

    def get_arm(self, platform: str, task_type: TaskType, agent: str) -> BeliefDistribution:
        key = self._arm_key(platform, task_type, agent)
        if key not in self._arms:
            self._arms[key] = BeliefDistribution()
            # Inicializar desde KG
            plat = self.kg.get_platform_expertise(platform)
            if plat and plat.total_tasks > 0:
                for _ in range(min(plat.total_tasks, 20)):
                    avg_r = plat.total_reward / plat.total_tasks if plat.total_tasks > 0 else 0
                    self._arms[key].update(avg_r)
        return self._arms[key]

    def thompson_sample(self, candidates: list[tuple[str, TaskType, str]]) -> tuple[str, TaskType, str]:
        """Selecciona brazo via Thompson Sampling"""
        best = None
        best_sample = -1

        for platform, task_type, agent in candidates:
            arm = self.get_arm(platform, task_type, agent)
            sample = arm.sample()
            if sample > best_sample:
                best_sample = sample
                best = (platform, task_type, agent)

        return best or candidates[0]

    def ucb_select(self, candidates: list[tuple[str, TaskType, str]], c: float = 2.0) -> tuple[str, TaskType, str]:
        """Selecciona brazo via UCB"""
        best = None
        best_ucb = -1

        for platform, task_type, agent in candidates:
            arm = self.get_arm(platform, task_type, agent)
            ucb = arm.ucb_value(self._total_pulls, c)
            if ucb > best_ucb:
                best_ucb = ucb
                best = (platform, task_type, agent)

        return best or candidates[0]

    def update(self, platform: str, task_type: TaskType, agent: str, reward: float):
        arm = self.get_arm(platform, task_type, agent)
        arm.update(reward)
        self._total_pulls += 1

    def get_arm_stats(self) -> dict[str, dict]:
        return {
            k: {"mean": v.mean, "std": v.std, "count": v.count, "ucb": v.ucb_value(self._total_pulls)}
            for k, v in self._arms.items()
        }


# Factory functions
def create_decision_engine(kg: KnowledgeGraph | None = None) -> DecisionEngine:
    return DecisionEngine(kg)


def create_bayesian_bandit(kg: KnowledgeGraph | None = None) -> BayesianBandit:
    return BayesianBandit(kg)


def default_decision_context(
    tasks: list[TaskCandidate],
    budget: float = 50.0,
    hours: float = 8.0,
    policy: DecisionPolicy = DecisionPolicy.MAX_EXPECTED_UTILITY,
    risk: RiskProfile = RiskProfile.BALANCED,
) -> DecisionContext:
    return DecisionContext(
        available_tasks=tasks, budget_usd=budget, time_horizon_hours=hours, policy=policy, risk_profile=risk
    )
