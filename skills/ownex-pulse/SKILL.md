# OWNEX Pulse Cycle — System Pulse

**Goal**: Monitor system health continuously — detect anomalies, check subsystem status, and route alerts when thresholds are breached.

**App**: pulse · **Cadence**: 5m · **Risk**: medium

## Default Phases

discover → triage → classify → notify

## Human Gates

- Critical system alerts (service down, data loss)
- Infrastructure failures (disk full, DB connection lost)
- Security anomalies

## Required Skills

- `health-check` — Run health probes on all subsystems
- `anomaly-detect` — Detect anomalous patterns in metrics
- `alert-routing` — Route alerts to appropriate channels (Telegram, email, desktop)

## Monitored Services

- Backend API (FastAPI health endpoint)
- Database connectivity + query latency
- Scheduler heartbeats
- Event bus activity
- Background worker status
- WebSocket bridge
- Notification bridges

## State File

```markdown
# Pulse Cycle State
Last run: <timestamp>
Services:
  api: 🟢 healthy
  db: 🟢 connected
  scheduler: 🟢 running (last heartbeat: 2m ago)
  event_bus: 🟢 142 events/min
Active Alerts:
  - None
Recent Resolved:
  - [2026-07-28 10:15] DB latency spike — resolved (index rebuild completed)
```

## Success Metrics

- MTTR (mean time to detect) for subsystem failures
- % of uptime across all services
- Alert false positive rate
- Time from anomaly → notification

## Budget

- Daily cap: 25k tokens (very low overhead)
- Unlimited runs (5m cadence)
- L1: dashboard + notification only
- L2: auto-remediation (restart service, clear cache)
