# Self-Improvement Engine (Ornith-1.5 Loop)

## Overview

The Self-Improvement Engine implements an autonomous learning loop inspired by the Ornith-1.5 architecture. It continuously generates tasks, executes them in a policy-limited sandbox, evaluates outcomes objectively, and persists experiences to steer future task selection toward capability gaps.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SelfImprovementEngine                     │
├─────────────────────────────────────────────────────────────┤
│  TaskGenerator  →  ScaffoldGenerator  →  RolloutRunner      │
│       ↓                  ↓                   ↓              │
│  DifficultyFrontier                    Harness (sandbox)    │
│       ↓                  ↓                   ↓              │
│  Evaluator          →  RewardModel  →  NoveltyScorer        │
│       ↓                  ↓                   ↓              │
│  ExperienceStore  →  CapabilityTracker  →  Persistence      │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Purpose |
|-----------|---------|
| `TaskGenerator` | Curriculum-driven task generation with novelty filtering |
| `ScaffoldGenerator` | Produces step-by-step guidance per task category |
| `RolloutRunner` | Executes solver + harness + evaluator with retries |
| `Harness` | Policy-limited sandbox (no network, command whitelist) |
| `Evaluator` | Objective verification per category (exit code + stdout) |
| `RewardModel` | R = Validity × (0.5 + 0.5×Difficulty) × Novelty |
| `NoveltyScorer` | Jaccard similarity against experience history |
| `DifficultyFrontier` | Adaptive difficulty targeting p=0.20 success rate |
| `ExperienceStore` | JSON persistence with injectable paths |
| `CapabilityTracker` | Rolling success rate per skill |

## Task Categories (7)

| Category | Description | Deterministic Solver Output |
|----------|-------------|----------------------------|
| `CODE` | Write/fix/refactor code | `def call(*args): return answer` |
| `TEST` | Write passing tests | `def test_trivial(): assert True` |
| `DEBUG` | Find/fix bug | `print("PASS")` |
| `ANALYSIS` | Analyze input, produce verdict | `verdict = 'accepted'` |
| `GENERATION` | Structured output from spec | `RESULT = json.dumps(payload)` |
| `SECURITY` | Find vulnerability | `vuln_type = 'sqli'` |
| `REASONING` | Answer reasoning question | `answer = '0'` |

## Solvers

| Solver | Name | Use Case |
|--------|------|----------|
| `DeterministicSolver` | `deterministic` | Offline, reproducible, always passes harness |
| `OARSolver` | `oar` | Production (async, uses OAR runtime) |

**Default**: `DeterministicSolver` for API reliability. Configure `solver=OARSolver()` in `SelfImprovementEngine` for live model usage.

## Configuration

```python
from core.self_improvement.config import SelfImprovementConfig

config = SelfImprovementConfig(
    data_dir=Path("./data/self_improvement"),
    p_target=0.20,              # target success rate
    frontier_sigma=0.25,        # gaussian spread
    difficulty_step=0.05,       # difficulty delta per outcome
    rollout_timeout_seconds=60,
    max_retries_per_rollout=1,
    allow_network=False,        # sandbox isolation
)
```

Environment variable: `OWNEX_DATA_DIR` overrides default storage root.

## API Endpoints

All endpoints under `/api/self-improvement` with prefix. Require Bearer token + CSRF.

### Engine Endpoints (FASE 13)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/run` | Execute single loop iteration |
| POST | `/run/batch` | Execute N iterations (`count` in body) |
| GET | `/status` | Engine status + frontier + capabilities + recommendations |
| GET | `/experiences?limit=50` | Recent experiences |
| GET | `/frontier` | Difficulty frontier state |
| GET | `/capabilities` | Capability tracker stats |
| GET | `/recommendations?limit=5` | Skills needing improvement |
| POST | `/generate` | Generate tasks without running (`count`, `skill_gaps`) |
| GET | `/dashboard/engine` | Consolidated status + recents + recommendations |

### Reflection/Planning Endpoints (Pre-existing)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reflect` | Create reflection from failure |
| GET | `/reflections` | List reflections |
| GET | `/plan` | Current improvement plan |
| POST | `/plan/auto-generate` | Auto-generate plan from reflections |
| GET | `/actions` | List improvement actions |
| GET | `/dashboard` | Reflection/planning dashboard |

## Usage Example

```python
from core.self_improvement.engine import SelfImprovementEngine
from core.self_improvement.rollout import DeterministicSolver
from core.self_improvement.config import SelfImprovementConfig

engine = SelfImprovementEngine(
    config=SelfImprovementConfig(data_dir=Path("./my_data")),
    solver=DeterministicSolver()
)

# Single iteration
result = engine.run_once()
print(f"Task: {result['task_title']}, Valid: {result['valid']}, Reward: {result['reward']}")

# Batch
results = engine.run_batch(count=5)
for r in results:
    print(f"  {r['task_title']}: {r['status']}")

# Status
status = engine.status()
print(f"Experiences: {status['experiences']}, Success rate: {status['success_rate']:.2%}")
print(f"Frontier difficulty: {status['frontier']['difficulty']:.2f}")

# Persistence survives restart
engine2 = SelfImprovementEngine(config=config, solver=DeterministicSolver())
print(f"Reloaded experiences: {engine2.status()['experiences']}")
```

## API Usage

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"device_id": "my-device"}'

# Get CSRF token (response sets csrf-token cookie)
curl -X GET http://localhost:8000/api/version -b cookies.txt -c cookies.txt

# Run self-improvement loop
curl -X POST http://localhost:8000/api/self-improvement/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json"

# Check status
curl -X GET http://localhost:8000/api/self-improvement/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF"
```

## Harness Policy

- **Allowed commands**: `python`, `pytest`, `sh`, `bash`
- **Forbidden keywords**: `rm -rf`, `sudo`, `chmod`, `mkfs`, `dd`, `:(){`, `curl`, `wget`
- **Network**: Blocked by default (`allow_network=False`)
- **Payload limit**: 1MB solution size
- **Timeout**: 60s per rollout (configurable)

## Verification Strategy (Per Category)

| Category | Verification |
|----------|--------------|
| CODE | Import solution, call function with cases, check return values |
| TEST | Run pytest on `test_solution.py` |
| DEBUG | Execute solution, check for "PASS" in stdout |
| ANALYSIS | Check `verdict` variable against accepted list |
| GENERATION | Check `RESULT` or `payload` dict has all required keys |
| SECURITY | Check `vuln_type` variable against accepted list |
| REASONING | Check `answer` variable against expected |

## Persistence

All state persists as JSON with injectable paths:
- `experiences.json` — completed loop iterations
- `capabilities.json` — skill success rates
- `tasks.json` — generated tasks (optional)
- `policies.json` — harness policy snapshot

## Testing

```bash
# Unit + integration tests
pytest tests/test_self_improvement.py -v

# API endpoints
pytest tests/test_self_improvement.py::TestAPIEndpoints -v

# Fast suite (includes self-improvement)
python scripts/dev test-fast
```

## FASE 13 Deliverables

✅ 10 new engine endpoints mounted at `/api/self-improvement/*`  
✅ 34 tests passing (unit + harness + engine + API)  
✅ Deterministic end-to-end loop verified  
✅ Persistence between restarts verified  
✅ Ruff clean, type hints complete