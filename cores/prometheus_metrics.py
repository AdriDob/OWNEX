"""Prometheus metrics integration for OWNEX v6.

Provides Counter, Gauge, Histogram, Summary metrics with proper labeling
for all system components: sensors, agents, revenue, opportunities, etc.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# Create a custom registry for OWNEX metrics
OWNEX_REGISTRY = CollectorRegistry()


# ──────────────────────────────────────────────────────────────────────────
# SENSOR NETWORK METRICS
# ──────────────────────────────────────────────────────────────────────────

SENSOR_FETCH_TOTAL = Counter(
    "ownex_sensor_fetch_total",
    "Total number of sensor fetch operations",
    ["sensor_id", "source_type", "source_name", "status"],
    registry=OWNEX_REGISTRY,
)

SENSOR_OBSERVATIONS_COLLECTED = Counter(
    "ownex_sensor_observations_collected_total",
    "Total observations collected by sensors",
    ["sensor_id", "source_type", "source_name"],
    registry=OWNEX_REGISTRY,
)

SENSOR_OBSERVATIONS_DEDUPED = Counter(
    "ownex_sensor_observations_deduped_total",
    "Total observations removed as duplicates",
    ["sensor_id"],
    registry=OWNEX_REGISTRY,
)

SENSOR_FETCH_DURATION_SECONDS = Histogram(
    "ownex_sensor_fetch_duration_seconds",
    "Time spent fetching from sensors",
    ["sensor_id", "source_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=OWNEX_REGISTRY,
)

SENSOR_HEALTH_STATUS = Gauge(
    "ownex_sensor_health_status",
    "Sensor health status (1=healthy, 0=degraded, -1=error)",
    ["sensor_id", "source_type", "source_name"],
    registry=OWNEX_REGISTRY,
)

SENSOR_ACTIVE_COUNT = Gauge(
    "ownex_sensor_active_total",
    "Number of active sensors",
    ["source_type"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# OBSERVATION ENGINE METRICS
# ──────────────────────────────────────────────────────────────────────────

OBSERVATION_ENGINE_COLLECTIONS_TOTAL = Counter(
    "ownex_observation_engine_collections_total",
    "Total observation collection runs",
    ["status"],
    registry=OWNEX_REGISTRY,
)

OBSERVATIONS_EMITTED_TOTAL = Counter(
    "ownex_observations_emitted_total",
    "Total observations emitted to pipeline",
    ["source_type", "source_name"],
    registry=OWNEX_REGISTRY,
)

OBSERVATION_CACHE_SIZE = Gauge(
    "ownex_observation_cache_size",
    "Current size of observation deduplication cache",
    registry=OWNEX_REGISTRY,
)

OBSERVATION_PIPELINE_STAGE = Gauge(
    "ownex_observation_pipeline_stage",
    "Observations in each pipeline stage",
    ["stage"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# AGENT SYSTEM METRICS
# ──────────────────────────────────────────────────────────────────────────

AGENT_EVENTS_RECEIVED = Counter(
    "ownex_agent_events_received_total",
    "Total events received by agents",
    ["agent_id", "event_type"],
    registry=OWNEX_REGISTRY,
)

AGENT_EVENTS_PROCESSED = Counter(
    "ownex_agent_events_processed_total",
    "Total events successfully processed by agents",
    ["agent_id", "event_type"],
    registry=OWNEX_REGISTRY,
)

AGENT_EVENTS_FAILED = Counter(
    "ownex_agent_events_failed_total",
    "Total events that failed processing",
    ["agent_id", "event_type", "error_type"],
    registry=OWNEX_REGISTRY,
)

AGENT_PROCESSING_DURATION = Histogram(
    "ownex_agent_processing_duration_seconds",
    "Agent event processing duration",
    ["agent_id", "event_type"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0),
    registry=OWNEX_REGISTRY,
)

AGENT_ACTIVE_PIPELINES = Gauge(
    "ownex_agent_active_pipelines",
    "Number of active pipelines per agent",
    ["agent_id"],
    registry=OWNEX_REGISTRY,
)

AGENT_HEALTH_STATUS = Gauge(
    "ownex_agent_health_status",
    "Agent health status (1=healthy, 0=degraded, -1=error)",
    ["agent_id"],
    registry=OWNEX_REGISTRY,
)

COORDINATOR_PIPELINE_STATE = Gauge(
    "ownex_coordinator_pipeline_state",
    "Pipeline state (1=running, 0=paused, -1=failed, -2=completed)",
    ["pipeline_id", "target_name", "state"],
    registry=OWNEX_REGISTRY,
)

COORDINATOR_PIPELINE_DURATION = Histogram(
    "ownex_coordinator_pipeline_duration_seconds",
    "Total pipeline execution duration",
    ["target_name", "final_state"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 86400),
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# REVENUE / FINANCIAL METRICS
# ──────────────────────────────────────────────────────────────────────────

REVENUE_TOTAL = Counter(
    "ownex_revenue_total",
    "Total revenue received",
    ["currency", "platform", "vulnerability_type", "severity"],
    registry=OWNEX_REGISTRY,
)

REVENUE_PAYOUT_RECEIVED = Counter(
    "ownex_revenue_payout_received_total",
    "Total payouts received",
    ["platform", "currency", "vulnerability_type"],
    registry=OWNEX_REGISTRY,
)

REVENUE_PENDING = Gauge(
    "ownex_revenue_pending",
    "Current pending revenue awaiting payment",
    ["currency", "platform"],
    registry=OWNEX_REGISTRY,
)

REVENUE_ESTIMATED = Gauge(
    "ownex_revenue_estimated",
    "Estimated revenue from submitted/pending reports",
    ["currency", "platform"],
    registry=OWNEX_REGISTRY,
)

REVENUE_GOAL_PROGRESS = Gauge(
    "ownex_revenue_goal_progress",
    "Progress towards financial goals (0-1)",
    ["goal_id", "goal_name", "currency"],
    registry=OWNEX_REGISTRY,
)

REVENUE_MONTHLY_TOTAL = Gauge(
    "ownex_revenue_monthly_total",
    "Monthly revenue total",
    ["year", "month", "currency"],
    registry=OWNEX_REGISTRY,
)

REVENUE_PLATFORM_BREAKDOWN = Gauge(
    "ownex_revenue_platform_breakdown",
    "Revenue breakdown by platform",
    ["platform", "currency"],
    registry=OWNEX_REGISTRY,
)

# Argentine payment specific
REVENUE_ARGENTINA_PAYOUT = Counter(
    "ownex_revenue_argentina_payout_total",
    "Argentine payouts received",
    ["method", "currency"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# OPPORTUNITY / INTELLIGENCE METRICS
# ──────────────────────────────────────────────────────────────────────────

OPPORTUNITIES_TOTAL = Gauge(
    "ownex_opportunities_total",
    "Total opportunities discovered",
    ["category", "priority"],
    registry=OWNEX_REGISTRY,
)

OPPORTUNITIES_DISCOVERED = Counter(
    "ownex_opportunities_discovered_total",
    "Total opportunities discovered",
    ["source", "category"],
    registry=OWNEX_REGISTRY,
)

OPPORTUNITY_SCORE = Histogram(
    "ownex_opportunity_score",
    "Opportunity scores distribution",
    ["category"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=OWNEX_REGISTRY,
)

OPPORTUNITY_EVH = Histogram(
    "ownex_opportunity_evh",
    "Expected Value per Hour distribution",
    ["category"],
    buckets=(0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000),
    registry=OWNEX_REGISTRY,
)

OPPORTUNITY_PROVIDERS_ACTIVE = Gauge(
    "ownex_opportunity_providers_active",
    "Number of active opportunity providers",
    ["category"],
    registry=OWNEX_REGISTRY,
)

OPPORTUNITY_PROVIDER_HEALTH = Gauge(
    "ownex_opportunity_provider_health",
    "Provider health status (1=healthy, 0=degraded, -1=error)",
    ["provider", "category"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# EXECUTION / ACTION LAYER METRICS
# ──────────────────────────────────────────────────────────────────────────

EXECUTION_ACTIONS_TOTAL = Counter(
    "ownex_execution_actions_total",
    "Total execution actions performed",
    ["action_type", "capability", "status"],
    registry=OWNEX_REGISTRY,
)

EXECUTION_ACTION_DURATION = Histogram(
    "ownex_execution_action_duration_seconds",
    "Execution action duration",
    ["action_type", "capability"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
    registry=OWNEX_REGISTRY,
)

EXECUTION_CAPABILITY_AVAILABLE = Gauge(
    "ownex_execution_capability_available",
    "Whether a capability is available (1=yes, 0=no)",
    ["capability"],
    registry=OWNEX_REGISTRY,
)

EXECUTION_QUEUE_DEPTH = Gauge(
    "ownex_execution_queue_depth",
    "Current execution queue depth",
    ["capability"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# MEMORY / LEARNING METRICS
# ──────────────────────────────────────────────────────────────────────────

MEMORY_RECORDS_TOTAL = Gauge(
    "ownex_memory_records_total",
    "Total memory records stored",
    ["category", "state"],
    registry=OWNEX_REGISTRY,
)

MEMORY_PATTERNS_LEARNED = Counter(
    "ownex_memory_patterns_learned_total",
    "Total patterns learned",
    ["pattern_type", "vulnerability_type"],
    registry=OWNEX_REGISTRY,
)

MEMORY_CONFIDENCE_SCORE = Histogram(
    "ownex_memory_confidence_score",
    "Memory record confidence scores",
    ["category"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=OWNEX_REGISTRY,
)

LEARNING_FEEDBACK_EVENTS = Counter(
    "ownex_learning_feedback_events_total",
    "Total feedback events for learning",
    ["event_type", "outcome"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# SYSTEM HEALTH / INFRASTRUCTURE METRICS
# ──────────────────────────────────────────────────────────────────────────

SYSTEM_HEALTH_STATUS = Gauge(
    "ownex_system_health_status",
    "Overall system health (1=healthy, 0=degraded, -1=critical)",
    ["component"],
    registry=OWNEX_REGISTRY,
)

SYSTEM_UPTIME_SECONDS = Gauge(
    "ownex_system_uptime_seconds",
    "System uptime in seconds",
    registry=OWNEX_REGISTRY,
)

DATABASE_CONNECTIONS = Gauge(
    "ownex_database_connections",
    "Active database connections",
    ["pool"],
    registry=OWNEX_REGISTRY,
)

DATABASE_QUERY_DURATION = Histogram(
    "ownex_database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    registry=OWNEX_REGISTRY,
)

EVENT_BUS_EVENTS_PUBLISHED = Counter(
    "ownex_event_bus_events_published_total",
    "Total events published to EventBus",
    ["event_type"],
    registry=OWNEX_REGISTRY,
)

EVENT_BUS_SUBSCRIBERS = Gauge(
    "ownex_event_bus_subscribers",
    "Number of subscribers per event type",
    ["event_type"],
    registry=OWNEX_REGISTRY,
)

SCHEDULER_JOBS_TOTAL = Counter(
    "ownex_scheduler_jobs_total",
    "Total scheduler jobs executed",
    ["job_name", "status"],
    registry=OWNEX_REGISTRY,
)

SCHEDULER_JOB_DURATION = Histogram(
    "ownex_scheduler_job_duration_seconds",
    "Scheduler job execution duration",
    ["job_name"],
    buckets=(1, 5, 10, 30, 60, 300, 600, 1800, 3600),
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# 24/7 OPERATION METRICS
# ──────────────────────────────────────────────────────────────────────────

HEALTH_MONITOR_CHECKS_TOTAL = Counter(
    "ownex_health_monitor_checks_total",
    "Total health monitor checks",
    ["check_name", "status"],
    registry=OWNEX_REGISTRY,
)

HEALTH_MONITOR_CHECK_DURATION = Histogram(
    "ownex_health_monitor_check_duration_seconds",
    "Health monitor check duration",
    ["check_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
    registry=OWNEX_REGISTRY,
)

RECOVERY_ACTIONS_TOTAL = Counter(
    "ownex_recovery_actions_total",
    "Total recovery actions taken",
    ["action_type", "component", "status"],
    registry=OWNEX_REGISTRY,
)

STORAGE_CLEANUP_BYTES = Counter(
    "ownex_storage_cleanup_bytes_total",
    "Total bytes cleaned up by storage manager",
    ["cleanup_type"],
    registry=OWNEX_REGISTRY,
)

BACKUP_OPERATIONS_TOTAL = Counter(
    "ownex_backup_operations_total",
    "Total backup operations",
    ["backup_type", "status"],
    registry=OWNEX_REGISTRY,
)

BACKUP_SIZE_BYTES = Gauge(
    "ownex_backup_size_bytes",
    "Latest backup size in bytes",
    ["backup_type"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# STRATEGIC OVERSIGHT METRICS
# ──────────────────────────────────────────────────────────────────────────

APPROVAL_GATE_REQUESTS = Counter(
    "ownex_approval_gate_requests_total",
    "Total approval gate requests",
    ["gate_type", "decision"],
    registry=OWNEX_REGISTRY,
)

APPROVAL_GATE_DURATION = Histogram(
    "ownex_approval_gate_duration_seconds",
    "Approval gate decision duration",
    ["gate_type"],
    buckets=(1, 5, 10, 30, 60, 300, 600, 3600, 86400),
    registry=OWNEX_REGISTRY,
)

QUALITY_VALIDATION_RESULTS = Counter(
    "ownex_quality_validation_total",
    "Total quality validation results",
    ["validation_type", "result"],
    registry=OWNEX_REGISTRY,
)

LEARNING_LOOP_ITERATIONS = Counter(
    "ownex_learning_loop_iterations_total",
    "Total learning loop iterations",
    ["loop_type", "status"],
    registry=OWNEX_REGISTRY,
)

HUMAN_INTERVENTION_REQUIRED = Counter(
    "ownex_human_intervention_required_total",
    "Total human interventions required",
    ["reason", "component"],
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# THINKING SYSTEM METRICS
# ──────────────────────────────────────────────────────────────────────────

THINKING_CYCLES_COMPLETED = Counter(
    "ownex_thinking_cycles_completed_total",
    "Total thinking system cycles completed",
    ["cycle_type"],  # planning, research, improvement
    registry=OWNEX_REGISTRY,
)

THINKING_CYCLE_DURATION = Histogram(
    "ownex_thinking_cycle_duration_seconds",
    "Thinking system cycle duration",
    ["cycle_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0),
    registry=OWNEX_REGISTRY,
)

LEARNING_PATTERNS_EXTRACTED = Counter(
    "ownex_learning_patterns_extracted_total",
    "Total learning patterns extracted from task history",
    ["pattern_type"],  # success, failure, optimization, discovery
    registry=OWNEX_REGISTRY,
)

LEARNING_CONFIDENCE = Histogram(
    "ownex_learning_confidence",
    "Confidence scores of learned patterns",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=OWNEX_REGISTRY,
)

LEARNING_PATTERNS_APPLIED = Counter(
    "ownex_learning_patterns_applied_total",
    "Total times learned patterns were applied to new tasks",
    ["pattern_type"],
    registry=OWNEX_REGISTRY,
)

DAILY_PLANS_CREATED = Counter(
    "ownex_daily_plans_created_total",
    "Total daily plans created",
    ["risk_level"],  # low, medium, high
    registry=OWNEX_REGISTRY,
)

RESEARCH_TOPICS_COMPLETED = Counter(
    "ownex_research_topics_completed_total",
    "Total research topics completed",
    ["category"],  # platform, technique, tool, market
    registry=OWNEX_REGISTRY,
)


# ──────────────────────────────────────────────────────────────────────────
# METRICS HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

def get_registry() -> CollectorRegistry:
    """Get the OWNEX Prometheus registry."""
    return OWNEX_REGISTRY


def record_sensor_fetch(sensor_id: str, source_type: str, source_name: str, duration: float, success: bool, obs_count: int = 0) -> None:
    """Record sensor fetch metrics."""
    status = "success" if success else "error"
    SENSOR_FETCH_TOTAL.labels(sensor_id=sensor_id, source_type=source_type, source_name=source_name, status=status).inc()
    SENSOR_FETCH_DURATION_SECONDS.labels(sensor_id=sensor_id, source_type=source_type).observe(duration)
    if obs_count > 0:
        SENSOR_OBSERVATIONS_COLLECTED.labels(sensor_id=sensor_id, source_type=source_type, source_name=source_name).inc(obs_count)


def record_agent_processing(agent_id: str, event_type: str, duration: float, success: bool, error_type: str | None = None) -> None:
    """Record agent event processing metrics."""
    AGENT_EVENTS_RECEIVED.labels(agent_id=agent_id, event_type=event_type).inc()
    AGENT_PROCESSING_DURATION.labels(agent_id=agent_id, event_type=event_type).observe(duration)
    if success:
        AGENT_EVENTS_PROCESSED.labels(agent_id=agent_id, event_type=event_type).inc()
    else:
        AGENT_EVENTS_FAILED.labels(agent_id=agent_id, event_type=event_type, error_type=error_type or "unknown").inc()


def record_revenue_payout(amount: float, currency: str, platform: str, vuln_type: str, severity: str) -> None:
    """Record revenue payout."""
    REVENUE_PAYOUT_RECEIVED.labels(platform=platform, currency=currency, vulnerability_type=vuln_type).inc(amount)
    REVENUE_TOTAL.labels(currency=currency, platform=platform, vulnerability_type=vuln_type, severity=severity).inc(amount)


def record_opportunity_discovered(source: str, category: str, score: float, evh: float | None = None) -> None:
    """Record opportunity discovery."""
    OPPORTUNITIES_DISCOVERED.labels(source=source, category=category).inc()
    OPPORTUNITY_SCORE.labels(category=category).observe(score)
    if evh is not None:
        OPPORTUNITY_EVH.labels(category=category).observe(evh)


def record_execution_action(action_type: str, capability: str, duration: float, success: bool) -> None:
    """Record execution action."""
    status = "success" if success else "failed"
    EXECUTION_ACTIONS_TOTAL.labels(action_type=action_type, capability=capability, status=status).inc()
    EXECUTION_ACTION_DURATION.labels(action_type=action_type, capability=capability).observe(duration)


def record_approval_gate(gate_type: str, decision: str, duration: float) -> None:
    """Record approval gate decision."""
    APPROVAL_GATE_REQUESTS.labels(gate_type=gate_type, decision=decision).inc()
    APPROVAL_GATE_DURATION.labels(gate_type=gate_type).observe(duration)


def record_quality_validation(validation_type: str, passed: bool) -> None:
    """Record quality validation result."""
    result = "passed" if passed else "failed"
    QUALITY_VALIDATION_RESULTS.labels(validation_type=validation_type, result=result).inc()


def record_human_intervention(reason: str, component: str) -> None:
    """Record human intervention requirement."""
    HUMAN_INTERVENTION_REQUIRED.labels(reason=reason, component=component).inc()
