"""
OWNEX Observability Core - Observabilidad continua del sistema
Registra QUÉ agente trabajó, CUÁNTO tardó, CUÁNTO costó, QUÉ produjo, QUÉ falló, POR QUÉ, RETORNO.
La base para mejorar objetivamente en lugar de por intuición.
"""

import json
import sqlite3
import statistics
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Punto de métrica individual"""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecution:
    """Ejecución completa de un agente - la unidad de observabilidad"""

    execution_id: str
    agent: str
    task_id: str
    task_type: str
    platform: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    api_calls: int = 0
    outcome: str = "running"  # running, success, failure, timeout, error
    result_summary: str = ""
    reward_usd: float = 0.0
    error_message: str | None = None
    error_category: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Métricas de calidad
    findings_count: int = 0
    findings_validated: int = 0
    findings_rejected: int = 0
    evidence_quality_score: float = 0.0

    # Retorno
    roi: float = 0.0
    reward_rate: float = 0.0  # USD/hora

    def complete(self, outcome: str, reward: float = 0.0, error: str | None = None, category: str | None = None):
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.outcome = outcome
        self.reward_usd = reward
        self.error_message = error
        self.error_category = category

        if self.cost_usd > 0:
            self.roi = reward / self.cost_usd
        if self.duration_seconds > 0:
            self.reward_rate = reward / (self.duration_seconds / 3600)


@dataclass
class SystemHealth:
    """Snapshot de salud del sistema"""

    timestamp: datetime
    active_agents: int
    queued_tasks: int
    running_tasks: int
    completed_last_hour: int
    failed_last_hour: int
    avg_reward_rate: float
    total_cost_last_hour: float
    total_reward_last_hour: float
    error_rate: float
    agent_health: dict[str, dict] = field(default_factory=dict)
    alerts: list[dict] = field(default_factory=list)


@dataclass
class Alert:
    """Alerta del sistema"""

    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved_at: datetime | None = None


class MetricsCollector:
    """Colector de métricas en tiempo real"""

    def __init__(self, db_path: str = "~/.ownex/observability.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._metrics: dict[str, list[MetricPoint]] = defaultdict(list)
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._timers: dict[str, list[float]] = defaultdict(list)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    labels TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL DEFAULT 0,
                    cost_usd REAL DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    api_calls INTEGER DEFAULT 0,
                    outcome TEXT DEFAULT 'running',
                    result_summary TEXT DEFAULT '',
                    reward_usd REAL DEFAULT 0,
                    error_message TEXT,
                    error_category TEXT,
                    metadata TEXT DEFAULT '{}',
                    findings_count INTEGER DEFAULT 0,
                    findings_validated INTEGER DEFAULT 0,
                    findings_rejected INTEGER DEFAULT 0,
                    evidence_quality_score REAL DEFAULT 0,
                    roi REAL DEFAULT 0,
                    reward_rate REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    acknowledged INTEGER DEFAULT 0,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    active_agents INTEGER,
                    queued_tasks INTEGER,
                    running_tasks INTEGER,
                    completed_last_hour INTEGER,
                    failed_last_hour INTEGER,
                    avg_reward_rate REAL,
                    total_cost_last_hour REAL,
                    total_reward_last_hour REAL,
                    error_rate REAL,
                    agent_health TEXT DEFAULT '{}',
                    alerts TEXT DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON metrics(name, timestamp);
                CREATE INDEX IF NOT EXISTS idx_executions_agent_time ON executions(agent, started_at);
                CREATE INDEX IF NOT EXISTS idx_executions_platform_time ON executions(platform, started_at);
                CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp);
                CREATE INDEX IF NOT EXISTS idx_health_time ON health_snapshots(timestamp);
            """)

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None):
        with self._lock:
            self._counters[name] += value
            point = MetricPoint(
                name=name,
                value=self._counters[name],
                metric_type=MetricType.COUNTER,
                timestamp=datetime.utcnow(),
                labels=labels or {},
            )
            self._metrics[name].append(point)

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None):
        with self._lock:
            self._gauges[name] = value
            point = MetricPoint(
                name=name, value=value, metric_type=MetricType.GAUGE, timestamp=datetime.utcnow(), labels=labels or {}
            )
            self._metrics[name].append(point)

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None):
        with self._lock:
            self._histograms[name].append(value)
            point = MetricPoint(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.utcnow(),
                labels=labels or {},
            )
            self._metrics[name].append(point)

    def timer(self, name: str, duration_seconds: float, labels: dict[str, str] | None = None):
        with self._lock:
            self._timers[name].append(duration_seconds)
            point = MetricPoint(
                name=name,
                value=duration_seconds,
                metric_type=MetricType.TIMER,
                timestamp=datetime.utcnow(),
                labels=labels or {},
            )
            self._metrics[name].append(point)

    @contextmanager
    def time(self, name: str, labels: dict[str, str] = None):
        """Context manager para medir duración"""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.timer(name, duration, labels)

    def record_execution(self, execution: AgentExecution):
        """Registra una ejecución completa"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO executions VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """,
                    (
                        execution.execution_id,
                        execution.agent,
                        execution.task_id,
                        execution.task_type,
                        execution.platform,
                        execution.started_at.isoformat(),
                        execution.completed_at.isoformat() if execution.completed_at else None,
                        execution.duration_seconds,
                        execution.cost_usd,
                        execution.tokens_used,
                        execution.api_calls,
                        execution.outcome,
                        execution.result_summary,
                        execution.reward_usd,
                        execution.error_message,
                        execution.error_category,
                        json.dumps(execution.metadata),
                        execution.findings_count,
                        execution.findings_validated,
                        execution.findings_rejected,
                        execution.evidence_quality_score,
                        execution.roi,
                        execution.reward_rate,
                    ),
                )

            # Métricas derivadas
            self.increment("executions_total", labels={"agent": execution.agent, "outcome": execution.outcome})
            self.increment("executions_reward_usd", execution.reward_usd, labels={"agent": execution.agent})
            self.increment("executions_cost_usd", execution.cost_usd, labels={"agent": execution.agent})
            self.histogram("execution_duration_seconds", execution.duration_seconds, labels={"agent": execution.agent})
            self.histogram("execution_roi", execution.roi, labels={"agent": execution.agent})

            if execution.outcome in ("failure", "error", "timeout"):
                self.increment(
                    "executions_failed",
                    labels={"agent": execution.agent, "category": execution.error_category or "unknown"},
                )

    def create_alert(
        self, severity: AlertSeverity, title: str, message: str, source: str, metadata: dict = None
    ) -> Alert:
        alert = Alert(
            alert_id=f"alert_{int(time.time() * 1000)}",
            severity=severity,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        alert.alert_id,
                        alert.severity.value,
                        alert.title,
                        alert.message,
                        alert.source,
                        alert.timestamp.isoformat(),
                        json.dumps(alert.metadata),
                        0,
                        None,
                    ),
                )

            self.increment("alerts_total", labels={"severity": severity.value, "source": source})

        return alert

    def get_metric_stats(self, name: str, window_minutes: int = 60) -> dict[str, float]:
        """Estadísticas de una métrica en ventana temporal"""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        points = [p for p in self._metrics.get(name, []) if p.timestamp > cutoff]

        if not points:
            return {"count": 0}

        values = [p.value for p in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1],
        }

    def get_execution_stats(self, agent: str = None, hours: int = 24) -> dict[str, Any]:
        """Estadísticas de ejecuciones"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM executions WHERE started_at > ?"
            params = [cutoff.isoformat()]
            if agent:
                query += " AND agent = ?"
                params.append(agent)

            rows = conn.execute(query, params).fetchall()

        if not rows:
            return {"total": 0}

        total = len(rows)
        successful = sum(1 for r in rows if r["outcome"] == "success")
        failed = sum(1 for r in rows if r["outcome"] in ("failure", "error", "timeout"))
        total_reward = sum(r["reward_usd"] for r in rows)
        total_cost = sum(r["cost_usd"] for r in rows)
        total_duration = sum(r["duration_seconds"] for r in rows)

        by_platform = defaultdict(lambda: {"count": 0, "reward": 0.0, "cost": 0.0, "success": 0})
        by_outcome = defaultdict(int)

        for r in rows:
            by_platform[r["platform"]]["count"] += 1
            by_platform[r["platform"]]["reward"] += r["reward_usd"]
            by_platform[r["platform"]]["cost"] += r["cost_usd"]
            if r["outcome"] == "success":
                by_platform[r["platform"]]["success"] += 1
            by_outcome[r["outcome"]] += 1

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "total_reward": total_reward,
            "total_cost": total_cost,
            "net_profit": total_reward - total_cost,
            "roi": total_reward / total_cost if total_cost > 0 else 0,
            "avg_duration_seconds": total_duration / total if total > 0 else 0,
            "reward_rate_per_hour": total_reward / (total_duration / 3600) if total_duration > 0 else 0,
            "by_platform": dict(by_platform),
            "by_outcome": dict(by_outcome),
        }

    def get_agent_comparison(self, hours: int = 24) -> dict[str, dict]:
        """Compara rendimiento entre agentes"""
        agents = set()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT agent FROM executions").fetchall()
            agents = {r[0] for r in rows}

        comparison = {}
        for agent in agents:
            comparison[agent] = self.get_execution_stats(agent, hours)

        return comparison

    def get_error_analysis(self, hours: int = 168) -> dict[str, Any]:
        """Análisis de errores por categoría"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT error_category, agent, platform, COUNT(*) as count,
                       GROUP_CONCAT(DISTINCT error_message) as messages
                FROM executions
                WHERE started_at > ? AND outcome IN ('failure', 'error', 'timeout')
                GROUP BY error_category, agent, platform
                ORDER BY count DESC
            """,
                [cutoff.isoformat()],
            ).fetchall()

        by_category = defaultdict(int)
        by_agent = defaultdict(int)
        by_platform = defaultdict(int)
        details = []

        for r in rows:
            cat = r["error_category"] or "unknown"
            by_category[cat] += r["count"]
            by_agent[r["agent"]] += r["count"]
            by_platform[r["platform"]] += r["count"]
            details.append(
                {
                    "category": cat,
                    "agent": r["agent"],
                    "platform": r["platform"],
                    "count": r["count"],
                    "sample_messages": r["messages"].split(",")[:3] if r["messages"] else [],
                }
            )

        return {
            "total_errors": sum(by_category.values()),
            "by_category": dict(by_category),
            "by_agent": dict(by_agent),
            "by_platform": dict(by_platform),
            "details": details[:20],
        }

    def snapshot_health(self, active_agents: int, queued_tasks: int, running_tasks: int) -> SystemHealth:
        """Toma snapshot de salud del sistema"""
        stats_1h = self.get_execution_stats(hours=1)

        health = SystemHealth(
            timestamp=datetime.utcnow(),
            active_agents=active_agents,
            queued_tasks=queued_tasks,
            running_tasks=running_tasks,
            completed_last_hour=stats_1h.get("successful", 0),
            failed_last_hour=stats_1h.get("failed", 0),
            avg_reward_rate=stats_1h.get("reward_rate_per_hour", 0),
            total_cost_last_hour=stats_1h.get("total_cost", 0),
            total_reward_last_hour=stats_1h.get("total_reward", 0),
            error_rate=stats_1h.get("failed", 0) / max(stats_1h.get("total", 1), 1),
        )

        # Verificar alertas automáticas
        if health.error_rate > 0.5:
            self.create_alert(
                AlertSeverity.WARNING,
                "High error rate",
                f"Error rate {health.error_rate:.1%} in last hour",
                "health_monitor",
            )
        if health.avg_reward_rate < 1.0 and stats_1h.get("total", 0) > 5:
            self.create_alert(
                AlertSeverity.WARNING,
                "Low reward rate",
                f"Reward rate ${health.avg_reward_rate:.2f}/hr",
                "health_monitor",
            )
        if health.total_cost_last_hour > 100:
            self.create_alert(
                AlertSeverity.CRITICAL,
                "High cost burn",
                f"${health.total_cost_last_hour:.2f} spent in last hour",
                "health_monitor",
            )

        # Persistir snapshot
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO health_snapshots
                (timestamp, active_agents, queued_tasks, running_tasks,
                 completed_last_hour, failed_last_hour, avg_reward_rate,
                 total_cost_last_hour, total_reward_last_hour, error_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    health.timestamp.isoformat(),
                    health.active_agents,
                    health.queued_tasks,
                    health.running_tasks,
                    health.completed_last_hour,
                    health.failed_last_hour,
                    health.avg_reward_rate,
                    health.total_cost_last_hour,
                    health.total_reward_last_hour,
                    health.error_rate,
                ),
            )

        return health

    def get_recent_health(self, hours: int = 24) -> list[SystemHealth]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM health_snapshots WHERE timestamp > ?
                ORDER BY timestamp DESC
            """,
                [cutoff.isoformat()],
            ).fetchall()

        return [
            SystemHealth(
                timestamp=datetime.fromisoformat(r["timestamp"]),
                active_agents=r["active_agents"],
                queued_tasks=r["queued_tasks"],
                running_tasks=r["running_tasks"],
                completed_last_hour=r["completed_last_hour"],
                failed_last_hour=r["failed_last_hour"],
                avg_reward_rate=r["avg_reward_rate"],
                total_cost_last_hour=r["total_cost_last_hour"],
                total_reward_last_hour=r["total_reward_last_hour"],
                error_rate=r["error_rate"],
            )
            for r in rows
        ]


class ExecutionTracker:
    """Tracker de alto nivel para ejecuciones de agentes"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self._active: dict[str, AgentExecution] = {}
        self._lock = threading.RLock()

    @contextmanager
    def track(self, agent: str, task_id: str, task_type: str, platform: str, metadata: dict = None):
        """Context manager para trackear ejecución completa"""
        execution_id = f"{agent}_{task_id}_{int(time.time() * 1000)}"
        execution = AgentExecution(
            execution_id=execution_id,
            agent=agent,
            task_id=task_id,
            task_type=task_type,
            platform=platform,
            started_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        with self._lock:
            self._active[execution_id] = execution

        try:
            yield execution
            # Si sale sin excepción, asumir éxito
            if execution.outcome == "running":
                execution.complete("success")
        except Exception as e:
            execution.complete("error", error=str(e), category=type(e).__name__)
            raise
        finally:
            with self._lock:
                self.collector.record_execution(execution)
                self._active.pop(execution_id, None)

    def start_execution(
        self, agent: str, task_id: str, task_type: str, platform: str, metadata: dict = None
    ) -> AgentExecution:
        """Inicia tracking manual (para casos sin context manager)"""
        execution_id = f"{agent}_{task_id}_{int(time.time() * 1000)}"
        execution = AgentExecution(
            execution_id=execution_id,
            agent=agent,
            task_id=task_id,
            task_type=task_type,
            platform=platform,
            started_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        with self._lock:
            self._active[execution_id] = execution

        return execution

    def complete_execution(
        self, execution: AgentExecution, outcome: str, reward: float = 0.0, error: str = None, category: str = None
    ):
        """Completa tracking manual"""
        execution.complete(outcome, reward, error, category)
        self.collector.record_execution(execution)

        with self._lock:
            self._active.pop(execution.execution_id, None)


# Singleton global
_metrics_collector: MetricsCollector | None = None
_execution_tracker: ExecutionTracker | None = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_execution_tracker() -> ExecutionTracker:
    global _execution_tracker
    if _execution_tracker is None:
        _execution_tracker = ExecutionTracker(get_metrics_collector())
    return _execution_tracker


# Decorador conveniente
def track_execution(agent: str, task_type: str, platform: str):
    """Decorador para trackear funciones de agentes"""

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            task_id = kwargs.get("task_id", f"{func.__name__}_{int(time.time())}")
            tracker = get_execution_tracker()
            with tracker.track(agent, task_id, task_type, platform) as exec:
                result = func(*args, **kwargs)
                # Intentar extraer recompensa del resultado
                if isinstance(result, dict):
                    reward = result.get("reward_usd", 0)
                    if reward:
                        exec.reward_usd = reward
                return result

        return wrapper

    return decorator
