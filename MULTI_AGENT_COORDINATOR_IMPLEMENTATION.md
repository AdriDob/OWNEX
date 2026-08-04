# Multi-Agent Bounty Coordinator - Implementation Summary

## Overview
Implemented a multi-agent coordinator to parallelize bounty execution with priority queue based on EVH (Expected Value per Hour).

## Files Created

### 1. `cores/agents/bounty_coordinator.py`
Main coordinator implementation with:
- **BountyCoordinator class**: Stateful singleton pattern for parallel bounty execution
- **Priority Queue**: Uses EVH-based priority (higher EVH = higher priority)
- **Concurrency Control**: Max 3-5 concurrent bounties (configurable)
- **Timeout Handling**: Automatic cleanup after 30min timeout (configurable)
- **EventBus Integration**: Publishes events for monitoring:
  - `coordinator:started` / `coordinator:stopped`
  - `coordinator:bounty_queued` / `coordinator:bounty_started`
  - `coordinator:bounty_completed` / `coordinator:bounty_failed`
  - `coordinator:bounty_timeout`
- **Auto-cleanup**: Removes failed/timeout bounties and cleans up repos
- **State Management**: Tracks queued, active, and completed bounties

### 2. `api/routers/agent_coordinator.py`
FastAPI router with endpoints:
- `POST /api/agent-coordinator/start` - Start the coordinator scheduler
- `POST /api/agent-coordinator/stop` - Stop the coordinator scheduler
- `GET /api/agent-coordinator/status` - Get coordinator status and stats
- `POST /api/agent-coordinator/add-bounty` - Add a bounty to the queue
- `POST /api/agent-coordinator/config` - Update coordinator configuration
- `DELETE /api/agent-coordinator/completed/{bounty_id}` - Remove completed bounty from history
- `GET /api/agent-coordinator/queue` - Get detailed queue information

### 3. `scripts/test_coordinator.py`
Test script to verify coordinator functionality.

## Files Modified

### 1. `api/main.py`
- Added `agent_coordinator` to imports
- Mounted `agent_coordinator.router` at line 1500

### 2. `cores/events/event_bus.py`
- Added coordinator events to `EVENT_PRIORITY_MAP`:
  - `coordinator:bounty_failed` - critical
  - `coordinator:bounty_timeout` - critical
  - `coordinator:bounty_started` - high
  - `coordinator:bounty_completed` - high
  - `coordinator:started` - medium
  - `coordinator:stopped` - medium
  - `coordinator:bounty_queued` - medium

## Configuration

### CoordinatorConfig
```python
max_concurrent: int = 3           # Max 3-5 simultaneous bounties
timeout_minutes: int = 30         # Timeout for individual bounties
auto_start: bool = False          # Auto-start when bounties are added
enable_priority_queue: bool = True # Use EVH-based priority
cleanup_on_failure: bool = True   # Auto-cleanup failed bounties
```

## Usage Example

### Start the coordinator
```bash
curl -X POST http://localhost:8000/api/agent-coordinator/start
```

### Add a bounty to the queue
```bash
curl -X POST http://localhost:8000/api/agent-coordinator/add-bounty \
  -H "Content-Type: application/json" \
  -d '{
    "bounty_id": "algora-123",
    "repo": "owner/repo",
    "issue_number": 42,
    "issue_url": "https://github.com/owner/repo/issues/42",
    "title": "Fix authentication bug",
    "description": "Authentication fails when...",
    "evh": 150.0
  }'
```

### Check status
```bash
curl http://localhost:8000/api/agent-coordinator/status
```

### Stop the coordinator
```bash
curl -X POST http://localhost:8000/api/agent-coordinator/stop
```

## Priority Queue Behavior

Bounties are prioritized by EVH (Expected Value per Hour):
- Higher EVH = higher priority (executed first)
- If EVH is not available, uses FIFO (timestamp-based)
- Priority is stored as negative value for max-heap behavior in PriorityQueue

## Integration with BountyPipeline

The coordinator uses the existing `BountyPipeline` from `core.autonomy.bounty_pipeline`:
- Integrates via `get_bounty_pipeline()` singleton
- Executes bounties asynchronously with timeout
- Captures results and errors for each bounty
- Cleanup of repo directories on failure/timeout

## State Persistence

The coordinator maintains in-memory state:
- `_queue`: PriorityQueue of pending bounties
- `_active_tasks`: Dict of currently running bounties
- `_completed_tasks`: Dict of completed bounties (last 100)

Note: For production, consider persisting state to database for recovery after restart.

## Testing

Run the test script:
```bash
python scripts/test_coordinator.py
```

This tests:
1. Starting/stopping the coordinator
2. Adding bounties to the queue
3. Getting coordinator status
4. Priority queue ordering (EVH-based)

## Next Steps (Optional Enhancements)

1. **Database Persistence**: Store coordinator state in PipelineRun or new table
2. **Recovery on Restart**: Load queued bounties from DB on startup
3. **Dynamic Scaling**: Adjust max_concurrent based on system resources
4. **Web Dashboard**: Real-time view of queue and active bounties
5. **Metrics Integration**: Prometheus metrics for queue size, execution time, success rate
6. **Webhook Notifications**: Notify on bounty completion/failure
