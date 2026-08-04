# EventBus System

> Version 4.6.0 — Julio 2026

## 1. Architecture Overview

The ORION Platform has three event bus systems serving different communication needs:

| Bus | Class | File | Purpose | Persistence |
|---|---|---|---|---|
| CATEYE EventBus | `EventBus` | `cores/events/event_bus.py` | System-wide events (findings, opportunities, reports, system state) | SQLite via `EventBusEntry` model + in-memory cache (500 events) |
| ORION CoreEventBus | `CoreEventBus` | `core/events/event_bus.py` | App-level namespaced events (`atlas:*`, `odyssey:*`) | SQLite via `EventRecord` in `orion_core.db` + in-memory (1000 events) |
| AgentBus | `LocalEventBus` | `cores/agents/bus.py` | Agent-to-agent communication (pipeline events, task dispatch) | In-memory only (1000 events) |

### Event Flow Diagram

```
+------------------+       +------------------+       +------------------+
|   Publisher      | ----> |   EventBus       | ----> |   Subscribers    |
| (scheduler,      |       |                  |       | (notification    |
|  routers,        |       |  1. Classify     |       |  bridges,        |
|  agents)         |       |  2. Persist      |       |  auto-report,    |
+------------------+       |  3. Route        |       |  WS bridge)      |
                           |  4. Dispatch     |       +------------------+
                           +------------------+
                                   |
                                   v
                           +------------------+
                           |   SQLite DB      |
                           | (EventBusEntry)  |
                           +------------------+
```

On every `publish()` call, the CATEYE EventBus:

1. Classifies the event via `EVENT_PRIORITY_MAP` (critical, high, medium, low, ignore)
2. Records the event in the in-memory history ring buffer (max 500)
3. Persists the event to SQLite via the `EventBusEntry` model
4. Routes the event through the PriorityEngine for ranking (opportunity/quick_win/system_alert events)
5. Dispatches to all registered sync handlers (same thread)
6. Dispatches to all registered async handlers (via `asyncio.run_coroutine_threadsafe`)

## 2. Event Types

The CATEYE EventBus defines 20+ event types in `EVENT_PRIORITY_MAP`:

### Critical Events

| Event Type | Description | Publisher |
|---|---|---|
| `system:error` | System error occurred | `cores/system_health.py`, `cores/recovery/engine.py` |
| `system:degraded` | System entered degraded state | `cores/system_state.py` |
| `system:alert` | System alert | Various |
| `recovery:started` | Recovery action initiated | `cores/recovery/engine.py` |
| `recovery:failed` | Recovery action failed | `cores/recovery/engine.py` |
| `anomaly_detected` | Anomaly detected | `cores/intelligence/` |
| `failure_predicted` | Failure predicted | `cores/predictor/` |

### High Priority Events

| Event Type | Description | Publisher |
|---|---|---|
| `opportunity:found` | New opportunity detected | `cores/opportunity/engine.py`, `api/scheduler.py` |
| `quick_win:detected` | Quick win found | `cores/opportunity/` |
| `contract:warning` | Contract warning | `cores/contracts/` |

### Medium Priority Events

| Event Type | Description | Publisher |
|---|---|---|
| `system:ready` | Service is ready | `cores/events/event_bus.py` (self-publish after init) |
| `recovery:success` | Recovery succeeded | `cores/recovery/engine.py` |
| `health_score_updated` | Health score recalculated | `cores/system_health.py` |
| `auto_optimization_applied` | Auto-optimization ran | `cores/optimization/` |
| `report:generated` | Report generated | `api/scheduler.py` |
| `opportunity:updated` | Existing opportunity updated | `cores/opportunity/engine.py` |
| `assistant:recommendation` | AI assistant recommendation | `cores/assistant/` |

### Low Priority Events

| Event Type | Description | Publisher |
|---|---|---|
| `sync:completed` | Sync cycle completed | `cores/financial/scheduler.py` |
| `discovery:completed` | Discovery scan completed | `api/scheduler.py` |
| `system:boot:complete` | System boot completed | `api/main.py` |
| `system:boot:starting` | System boot starting | `api/main.py` |

### Agent Bus Events (forwarded as `agent:*`)

Bridged from the AgentBus to the CATEYE EventBus via `cores/agents/bus.py:bridge_agent_bus_to_eventbus()`:

- `agent:PIPELINE_START`
- `agent:TASK_COMPLETE`
- `agent:AGENT_ERROR`
- `agent:DISCOVERY_COMPLETE`
- `agent:ANALYSIS_COMPLETE`
- `agent:REPORT_GENERATED`

### Finding Events

| Event Type | Description | Publisher |
|---|---|---|
| `finding:created` | New finding created | `api/routers/findings.py` |
| `finding:status_changed` | Finding status changed | `api/routers/findings.py` |

### Financial Events

| Event Type | Description | Publisher |
|---|---|---|
| `financial:sync_completed` | Financial sync cycle completed | `cores/financial/events.py` |
| `financial:withdrawal_completed` | Withdrawal completed | `api/routers/financial_truth.py` |
| `financial:withdrawal_failed` | Withdrawal failed | `api/routers/financial_truth.py` |
| `financial:dispute_resolved` | Financial discrepancy resolved | `api/routers/financial_truth.py` |

## 3. Event Flow Examples

### Finding Confirmed → Auto-Report

Registered in `api/main.py` as an EventBus subscriber:

```
finding:status_changed (new_status="confirmed")
  -> _auto_report() subscriber
    -> create_report_from_findings()
    -> report:generated event published
```

```python
# api/main.py:266-287
def _auto_report(event_type, payload):
    if payload.get("new_status") != "confirmed":
        return
    report = create_report_from_findings(
        session=session,
        finding_ids=[payload["id"]],
        ...
    )
```

### Finding Rejected → FP Feedback

```
finding:status_changed (new_status="rejected")
  -> _fp_feedback() subscriber
    -> FeedbackLearner.analyze_verdict_patterns()
```

### Discovery Pipeline → EventBus

```
DISCOVER stage (api/scheduler.py)
  -> bus.publish("opportunity:found", {count, names, source})
  -> bus.publish("discovery:completed", {stage, scanned, total})

RECON stage
  -> bus.publish("discovery:completed", {stage="recon", ...})

REPORT stage
  -> bus.publish("report:generated", {finding_id, report_id, status})
```

### AgentBus → EventBus Bridge

```
AgentBus publish(event)
  -> bridge_agent_bus_to_eventbus() _forward handler
    -> CATEYE EventBus publish("agent:{event_type}", {source, target, ...})
```

## 4. Usage Examples

### Publishing an Event

```python
from cores.events.event_bus import get_event_bus

bus = get_event_bus()
bus.publish(
    "finding:status_changed",
    id=finding.id,
    new_status="confirmed",
    target_id=finding.target_id,
    title=finding.title,
    severity=finding.severity,
)
```

### Subscribing to Events (Sync)

```python
from cores.events.event_bus import get_event_bus


def my_handler(event_type, priority, **payload):
    logger.info("Received %s: %s", event_type, payload)


bus = get_event_bus()
bus.subscribe("finding:created", my_handler)
```

### Subscribing to All Events

Use the wildcard `*` pattern:

```python
def catch_all(event_type, priority, **payload):
    logger.debug("Event: %s", event_type)


bus.subscribe("*", catch_all)
```

### Subscribing to Events (Async)

```python
async def async_handler(event_type, priority, **payload):
    await some_async_operation(payload)


bus.subscribe_async("report:generated", async_handler)
```

### Getting Event History

```python
bus = get_event_bus()

# Last 50 events of any type
history = bus.get_history()

# Last 20 finding events
finding_events = bus.get_history(event_type="finding:status_changed", limit=20)
```

## 5. Event Priority Classification

The `EVENT_PRIORITY_MAP` in `cores/events/event_bus.py` classifies events by type:

- **Ignore**: Events with `priority=ignore` are logged at DEBUG level and not dispatched
- **All others**: Routed through the PriorityEngine for ranking (opportunity/quick_win/system_alert events get special handling)

```python
EVENT_PRIORITY_MAP = {
    "system:error": "critical",
    "opportunity:found": "high",
    "report:generated": "medium",
    "discovery:completed": "low",
    # ... 20+ event types mapped
}
```

## 6. Persistence

All events published to the CATEYE EventBus are persisted to the main SQLite database via the `EventBusEntry` model:

```python
# database/models.py
class EventBusEntry(Base):
    __tablename__ = "event_bus_entries"
    id = Column(Integer, primary_key=True)
    event_type = Column(String, index=True)
    priority = Column(String)
    payload_json = Column(Text)
    timestamp = Column(String)
```

The `get_history()` method combines in-memory cache with DB query, de-duplicating by `{type}:{timestamp}` key to avoid overlap.

## 7. App Namespacing (CoreEventBus)

The ORION CoreEventBus (`core/events/event_bus.py`) adds namespace support for multi-app events:

```python
bus = get_core_event_bus()
# Apps auto-namespace events
bus.app_event("atlas", "price_updated")  # -> "atlas:price_updated"
# Subscribe to all events from an app
bus.subscribe_app("atlas", handler)  # -> "atlas:*"
```

The CoreEventBus also bridges to the legacy CATEYE EventBus, so app events reach all legacy subscribers.

## 8. Integration Points

| Component | Events Published | Events Subscribed |
|---|---|---|
| `api/scheduler.py` | `opportunity:found`, `discovery:completed`, `report:generated` | — |
| `api/routers/findings.py` | `finding:created`, `finding:status_changed` | — |
| `api/main.py` | `system:boot:complete` | `finding:status_changed` (auto-report, FP feedback) |
| `cores/opportunity/engine.py` | `opportunity:found`, `opportunity:updated` | — |
| `cores/recovery/engine.py` | `recovery:started`, `recovery:success`, `recovery:failed` | — |
| `cores/system_state.py` | `system:state:ready`, `system:state:degraded` | — |
| `cores/financial/events.py` | `financial:sync_completed` | — |
| `cores/agents/bus.py` | `agent:*` (via bridge) | — |
| `cores/ws/bridge.py` | — | `*` (all events → WebSocket) |
| `cores/notifications/hub.py` | — | Various (via notification bridge) |
| `desktop/watchdog.py` | — | `system:*`, `recovery:*` |
