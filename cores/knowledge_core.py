"""
OWNEX Knowledge Core - Memoria institucional y aprendizaje continuo
Captura cada iteración, extrae patrones, acumula experiencia.
"""

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class OutcomeType(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class TaskType(Enum):
    RECON = "recon"
    SCAN = "scan"
    EXPLOIT = "exploit"
    REPORT = "report"
    RESEARCH = "research"
    DEVELOPMENT = "development"
    ADMIN = "admin"


@dataclass
class TaskOutcome:
    """Resultado de una ejecución de tarea - la unidad atómica de aprendizaje"""

    task_id: str
    task_type: TaskType
    platform: str
    agent: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    cost_usd: float
    outcome: OutcomeType
    result_data: dict[str, Any]
    reward_usd: float = 0.0
    confidence: float = 1.0
    failure_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def efficiency(self) -> float:
        """Recompensa por unidad de costo (ROI bruto)"""
        if self.cost_usd <= 0:
            return 0.0
        return self.reward_usd / self.cost_usd

    @property
    def reward_rate(self) -> float:
        """Recompensa por hora de cómputo"""
        hours = self.duration_seconds / 3600
        if hours <= 0:
            return 0.0
        return self.reward_usd / hours


@dataclass
class PlatformExpertise:
    """Conocimiento acumulado por plataforma"""

    platform: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_reward: float = 0.0
    total_cost: float = 0.0
    avg_duration: float = 0.0
    best_agents: dict[str, float] = field(default_factory=dict)  # agent -> efficiency
    best_task_types: dict[str, float] = field(default_factory=dict)
    peak_hours: dict[int, float] = field(default_factory=dict)  # hour -> avg reward
    common_failures: dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def roi(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return self.total_reward / self.total_cost

    @property
    def expected_value_per_hour(self) -> float:
        """Valor esperado por hora basado en histórico"""
        if self.total_tasks == 0:
            return 0.0
        total_hours = sum(self.avg_duration for _ in range(self.total_tasks)) / 3600
        if total_hours == 0:
            return 0.0
        return self.total_reward / total_hours


@dataclass
class AgentProfile:
    """Perfil de rendimiento por agente"""

    agent: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_reward: float = 0.0
    total_cost: float = 0.0
    avg_duration: float = 0.0
    platform_affinity: dict[str, float] = field(default_factory=dict)
    task_type_affinity: dict[str, float] = field(default_factory=dict)
    failure_patterns: dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def efficiency(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return self.total_reward / self.total_cost


@dataclass
class DecisionRecord:
    """Registro de decisión para análisis post-hoc"""

    decision_id: str
    timestamp: datetime
    context: dict[str, Any]
    alternatives: list[dict[str, Any]]
    chosen: dict[str, Any]
    expected_value: float
    actual_outcome: TaskOutcome | None = None
    regret: float = 0.0  # Diferencia entre lo elegido y lo óptimo en retrospectiva


class KnowledgeGraph:
    """
    Núcleo de conocimiento de OWNEX.
    Captura, indexa y expone patrones para optimización.
    """

    def __init__(self, db_path: str = "~/.ownex/knowledge.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._init_db()

        # Caches en memoria para consultas rápidas
        self._platform_cache: dict[str, PlatformExpertise] = {}
        self._agent_cache: dict[str, AgentProfile] = {}
        self._recent_outcomes: list[TaskOutcome] = []
        self._decision_log: list[DecisionRecord] = []
        self._load_caches()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    cost_usd REAL NOT NULL,
                    outcome TEXT NOT NULL,
                    result_data TEXT NOT NULL,
                    reward_usd REAL DEFAULT 0,
                    confidence REAL DEFAULT 1.0,
                    failure_reason TEXT,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS platform_expertise (
                    platform TEXT PRIMARY KEY,
                    total_tasks INTEGER DEFAULT 0,
                    successful_tasks INTEGER DEFAULT 0,
                    total_reward REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    avg_duration REAL DEFAULT 0,
                    best_agents TEXT DEFAULT '{}',
                    best_task_types TEXT DEFAULT '{}',
                    peak_hours TEXT DEFAULT '{}',
                    common_failures TEXT DEFAULT '{}',
                    last_updated TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS agent_profiles (
                    agent TEXT PRIMARY KEY,
                    total_tasks INTEGER DEFAULT 0,
                    successful_tasks INTEGER DEFAULT 0,
                    total_reward REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    avg_duration REAL DEFAULT 0,
                    platform_affinity TEXT DEFAULT '{}',
                    task_type_affinity TEXT DEFAULT '{}',
                    failure_patterns TEXT DEFAULT '{}',
                    last_updated TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    context TEXT NOT NULL,
                    alternatives TEXT NOT NULL,
                    chosen TEXT NOT NULL,
                    expected_value REAL NOT NULL,
                    actual_outcome_id TEXT,
                    regret REAL DEFAULT 0,
                    FOREIGN KEY(actual_outcome_id) REFERENCES outcomes(task_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_outcomes_platform ON outcomes(platform);
                CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON outcomes(agent);
                CREATE INDEX IF NOT EXISTS idx_outcomes_time ON outcomes(completed_at);
                CREATE INDEX IF NOT EXISTS idx_decisions_time ON decisions(timestamp);
            """)

    def _load_caches(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Platform expertise
            for row in conn.execute("SELECT * FROM platform_expertise"):
                self._platform_cache[row["platform"]] = PlatformExpertise(
                    platform=row["platform"],
                    total_tasks=row["total_tasks"],
                    successful_tasks=row["successful_tasks"],
                    total_reward=row["total_reward"],
                    total_cost=row["total_cost"],
                    avg_duration=row["avg_duration"],
                    best_agents=json.loads(row["best_agents"]),
                    best_task_types=json.loads(row["best_task_types"]),
                    peak_hours={int(k): v for k, v in json.loads(row["peak_hours"]).items()},
                    common_failures=json.loads(row["common_failures"]),
                    last_updated=datetime.fromisoformat(row["last_updated"]),
                )

            # Agent profiles
            for row in conn.execute("SELECT * FROM agent_profiles"):
                self._agent_cache[row["agent"]] = AgentProfile(
                    agent=row["agent"],
                    total_tasks=row["total_tasks"],
                    successful_tasks=row["successful_tasks"],
                    total_reward=row["total_reward"],
                    total_cost=row["total_cost"],
                    avg_duration=row["avg_duration"],
                    platform_affinity=json.loads(row["platform_affinity"]),
                    task_type_affinity=json.loads(row["task_type_affinity"]),
                    failure_patterns=json.loads(row["failure_patterns"]),
                    last_updated=datetime.fromisoformat(row["last_updated"]),
                )

            # Recent outcomes (last 1000)
            for row in conn.execute("SELECT * FROM outcomes ORDER BY completed_at DESC LIMIT 1000"):
                self._recent_outcomes.append(self._row_to_outcome(row))

    def _row_to_outcome(self, row: sqlite3.Row) -> TaskOutcome:
        return TaskOutcome(
            task_id=row["task_id"],
            task_type=TaskType(row["task_type"]),
            platform=row["platform"],
            agent=row["agent"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]),
            duration_seconds=row["duration_seconds"],
            cost_usd=row["cost_usd"],
            outcome=OutcomeType(row["outcome"]),
            result_data=json.loads(row["result_data"]),
            reward_usd=row["reward_usd"],
            confidence=row["confidence"],
            failure_reason=row["failure_reason"],
            metadata=json.loads(row["metadata"]),
        )

    def record_outcome(self, outcome: TaskOutcome) -> None:
        """Registra un resultado y actualiza todo el conocimiento"""
        with self._lock:
            # Persistir
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        outcome.task_id,
                        outcome.task_type.value,
                        outcome.platform,
                        outcome.agent,
                        outcome.started_at.isoformat(),
                        outcome.completed_at.isoformat(),
                        outcome.duration_seconds,
                        outcome.cost_usd,
                        outcome.outcome.value,
                        json.dumps(outcome.result_data),
                        outcome.reward_usd,
                        outcome.confidence,
                        outcome.failure_reason,
                        json.dumps(outcome.metadata),
                    ),
                )

                # Actualizar platform expertise
                self._update_platform_expertise(conn, outcome)
                # Actualizar agent profile
                self._update_agent_profile(conn, outcome)

            # Actualizar caches
            self._recent_outcomes.insert(0, outcome)
            if len(self._recent_outcomes) > 1000:
                self._recent_outcomes.pop()

    def _update_platform_expertise(self, conn: sqlite3.Connection, outcome: TaskOutcome):
        plat = self._platform_cache.get(outcome.platform)
        if not plat:
            plat = PlatformExpertise(platform=outcome.platform)
            self._platform_cache[outcome.platform] = plat

        plat.total_tasks += 1
        if outcome.outcome == OutcomeType.SUCCESS:
            plat.successful_tasks += 1
        plat.total_reward += outcome.reward_usd
        plat.total_cost += outcome.cost_usd
        plat.avg_duration = (plat.avg_duration * (plat.total_tasks - 1) + outcome.duration_seconds) / plat.total_tasks

        # Agent efficiency
        agent_eff = outcome.efficiency
        if outcome.agent not in plat.best_agents or agent_eff > plat.best_agents[outcome.agent]:
            plat.best_agents[outcome.agent] = agent_eff

        # Task type efficiency
        task_eff = outcome.reward_rate
        ttype = outcome.task_type.value
        if ttype not in plat.best_task_types or task_eff > plat.best_task_types[ttype]:
            plat.best_task_types[ttype] = task_eff

        # Peak hours
        hour = outcome.completed_at.hour
        if outcome.reward_usd > 0:
            existing = plat.peak_hours.get(hour, 0)
            plat.peak_hours[hour] = (existing + outcome.reward_usd) / 2  # moving avg

        # Failure patterns
        if outcome.failure_reason:
            plat.common_failures[outcome.failure_reason] = plat.common_failures.get(outcome.failure_reason, 0) + 1

        plat.last_updated = datetime.utcnow()

        # Persist
        conn.execute(
            """
            INSERT OR REPLACE INTO platform_expertise VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                plat.platform,
                plat.total_tasks,
                plat.successful_tasks,
                plat.total_reward,
                plat.total_cost,
                plat.avg_duration,
                json.dumps(plat.best_agents),
                json.dumps(plat.best_task_types),
                json.dumps(plat.peak_hours),
                json.dumps(plat.common_failures),
                plat.last_updated.isoformat(),
            ),
        )

    def _update_agent_profile(self, conn: sqlite3.Connection, outcome: TaskOutcome):
        agent = self._agent_cache.get(outcome.agent)
        if not agent:
            agent = AgentProfile(agent=outcome.agent)
            self._agent_cache[outcome.agent] = agent

        agent.total_tasks += 1
        if outcome.outcome == OutcomeType.SUCCESS:
            agent.successful_tasks += 1
        agent.total_reward += outcome.reward_usd
        agent.total_cost += outcome.cost_usd
        agent.avg_duration = (
            agent.avg_duration * (agent.total_tasks - 1) + outcome.duration_seconds
        ) / agent.total_tasks

        # Platform affinity
        plat_eff = outcome.efficiency
        if outcome.platform not in agent.platform_affinity or plat_eff > agent.platform_affinity[outcome.platform]:
            agent.platform_affinity[outcome.platform] = plat_eff

        # Task type affinity
        ttype = outcome.task_type.value
        task_eff = outcome.reward_rate
        if ttype not in agent.task_type_affinity or task_eff > agent.task_type_affinity[ttype]:
            agent.task_type_affinity[ttype] = task_eff

        # Failure patterns
        if outcome.failure_reason:
            agent.failure_patterns[outcome.failure_reason] = agent.failure_patterns.get(outcome.failure_reason, 0) + 1

        agent.last_updated = datetime.utcnow()

        conn.execute(
            """
            INSERT OR REPLACE INTO agent_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                agent.agent,
                agent.total_tasks,
                agent.successful_tasks,
                agent.total_reward,
                agent.total_cost,
                agent.avg_duration,
                json.dumps(agent.platform_affinity),
                json.dumps(agent.task_type_affinity),
                json.dumps(agent.failure_patterns),
                agent.last_updated.isoformat(),
            ),
        )

    def record_decision(self, decision: DecisionRecord) -> None:
        """Registra una decisión para análisis de regret posterior"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        decision.decision_id,
                        decision.timestamp.isoformat(),
                        json.dumps(decision.context),
                        json.dumps(decision.alternatives),
                        json.dumps(decision.chosen),
                        decision.expected_value,
                        decision.actual_outcome.task_id if decision.actual_outcome else None,
                        decision.regret,
                    ),
                )
            self._decision_log.append(decision)

    def update_decision_outcome(self, decision_id: str, outcome: TaskOutcome) -> None:
        """Cierra el loop: compara lo esperado vs real"""
        with self._lock:
            for d in self._decision_log:
                if d.decision_id == decision_id:
                    d.actual_outcome = outcome
                    actual_value = outcome.reward_usd / max(outcome.cost_usd, 0.001)
                    d.regret = max(0, decision.expected_value - actual_value)
                    break

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE decisions SET actual_outcome_id=?, regret=?
                    WHERE decision_id=?
                """,
                    (outcome.task_id, d.regret, decision_id),
                )

    # === QUERY INTERFACE ===

    def get_platform_expertise(self, platform: str) -> PlatformExpertise | None:
        return self._platform_cache.get(platform)

    def get_agent_profile(self, agent: str) -> AgentProfile | None:
        return self._agent_cache.get(agent)

    def get_best_agent_for(self, platform: str, task_type: TaskType) -> str | None:
        """Mejor agente para una plataforma+tarea basado en histórico"""
        plat = self._platform_cache.get(platform)
        if not plat or not plat.best_agents:
            return None

        # Filtrar por afinidad con task_type
        candidates = []
        for agent, eff in plat.best_agents.items():
            agent_profile = self._agent_cache.get(agent)
            if agent_profile:
                type_affinity = agent_profile.task_type_affinity.get(task_type.value, 0)
                combined = eff * 0.7 + type_affinity * 0.3
                candidates.append((agent, combined))

        if not candidates:
            return max(plat.best_agents.items(), key=lambda x: x[1])[0]

        return max(candidates, key=lambda x: x[1])[0]

    def get_platform_roi(self, platform: str) -> float:
        plat = self._platform_cache.get(platform)
        return plat.roi if plat else 0.0

    def get_expected_value(self, platform: str, agent: str, task_type: TaskType) -> float:
        """Valor esperado basado en histórico"""
        plat = self._platform_cache.get(platform)
        ag = self._agent_cache.get(agent)

        if not plat or not ag:
            return 0.0

        base_rate = plat.expected_value_per_hour
        agent_mult = ag.efficiency if ag.efficiency > 0 else 1.0
        type_mult = ag.task_type_affinity.get(task_type.value, 1.0)
        plat_mult = ag.platform_affinity.get(platform, 1.0)

        return base_rate * agent_mult * type_mult * plat_mult

    def get_recent_failures(self, platform: str = None, limit: int = 20) -> list[TaskOutcome]:
        failures = [
            o
            for o in self._recent_outcomes
            if o.outcome in (OutcomeType.FAILURE, OutcomeType.ERROR, OutcomeType.TIMEOUT)
        ]
        if platform:
            failures = [f for f in failures if f.platform == platform]
        return failures[:limit]

    def get_decision_regret_stats(self, days: int = 30) -> dict[str, float]:
        """Estadísticas de regret para calibrar el motor de decisiones"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [d for d in self._decision_log if d.timestamp > cutoff and d.actual_outcome]

        if not recent:
            return {"avg_regret": 0, "max_regret": 0, "decisions": 0}

        regrets = [d.regret for d in recent]
        return {
            "avg_regret": sum(regrets) / len(regrets),
            "max_regret": max(regrets),
            "decisions": len(recent),
            "positive_regret_rate": sum(1 for r in regrets if r > 0) / len(regrets),
        }

    def export_knowledge(self) -> dict[str, Any]:
        """Exporta todo el conocimiento para backup/transferencia"""
        return {
            "platforms": {k: v.__dict__ for k, v in self._platform_cache.items()},
            "agents": {k: v.__dict__ for k, v in self._agent_cache.items()},
            "recent_outcomes": [o.__dict__ for o in self._recent_outcomes[:100]],
            "decisions": [d.__dict__ for d in self._decision_log[-100:]],
        }


# Singleton global
_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
