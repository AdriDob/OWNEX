# OWNEX Testing Guide

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

OWNEX uses a multi-layered testing strategy covering unit, integration, E2E, security, and desktop tests.

## Test Commands

### Quick Commands

```bash
# Fast smoke test (scoring + opportunity + scheduler + security cycle)
make test-fast
# or
.venv/bin/python scripts/dev test-fast
# 100 passed, 1 skipped in ~1s

# Full test suite (excludes known-flaky)
make test
# or
.venv/bin/python scripts/dev test
# ~3000 tests, ~60s

# Lint + typecheck + fast tests
make check
# or
.venv/bin/python scripts/dev check

# Lint with auto-fixes
make fmt
# or
.venv/bin/python scripts/dev fmt

# Type check (scoped)
make typecheck-fast
# or
.venv/bin/python scripts/dev typecheck-fast
```

### Specific Test Modules

```bash
# Core scoring/opportunity
.venv/bin/python -m pytest tests/test_scoring.py tests/test_opportunity_engine.py tests/test_opportunity_engine_comprehensive.py -v

# Scheduler & security
.venv/bin/python -m pytest tests/test_scheduler_jobs.py tests/test_e2e_security_pipeline.py tests/test_security_cycle.py -v

# Direct Work Engine
.venv/bin/python -m pytest tests/test_direct_work_engine.py tests/test_direct_work_api.py tests/test_workbank.py -v

# Execution & Income
.venv/bin/python -m pytest tests/test_execution_queue.py tests/test_income_chain_e2e.py -v

# Financial
.venv/bin/python -m pytest tests/test_financial_scheduler_persist.py tests/test_atlas_composition.py -v

# Market & QA
.venv/bin/python -m pytest tests/test_market_evolution.py tests/test_qa_cycle_api.py -v

# Security middleware
.venv/bin/python -m pytest tests/test_csrf_middleware.py tests/test_rate_limit_middleware.py tests/test_cors_tauri.py tests/test_auth_cookie.py -v

# Failure injection / Chaos
.venv/bin/python -m pytest tests/test_failure_injection.py tests/test_chaos_workflows.py -v

# AI & Voice
.venv/bin/python -m pytest tests/test_ai_security.py tests/test_hermes_security.py tests/test_voice_engine.py -v

# Desktop native
.venv/bin/python -m pytest tests/test_desktop_native.py -v

# Tauri packaging
.venv/bin/python -m pytest tests/test_tauri_packaging.py tests/test_data_dir_resolution.py -v
```

### Frontend Tests

```bash
cd frontend

# Unit tests (Vitest)
npm run test
# or
npx vitest run --coverage

# Type check
npx vue-tsc --noEmit

# Lint
npx biome check --write

# Build
npm run build
```

## Test Architecture

### Backend (pytest)

```
tests/
├── conftest.py              # DB isolation, fixtures
├── test_scoring.py          # ZeroBarrierScorer, EV calculations
├── test_opportunity_engine.py
├── test_opportunity_engine_comprehensive.py
├── test_scheduler_jobs.py   # 51 tests, 47 jobs, 12 cycles
├── test_e2e_security_pipeline.py
├── test_security_cycle.py
├── test_direct_work_engine.py    # 39 tests
├── test_direct_work_api.py       # 44 tests
├── test_workbank.py              # 18 tests
├── test_execution_queue.py       # 6 tests (state machine)
├── test_income_chain_e2e.py      # 3 tests (full chain)
├── test_financial_scheduler_persist.py  # 6 tests
├── test_atlas_composition.py       # 9 tests
├── test_market_evolution.py        # 25 tests
├── test_qa_cycle_api.py            # 7 tests
├── test_csrf_middleware.py         # 17 tests
├── test_rate_limit_middleware.py   # 12 tests
├── test_cors_tauri.py              # 9 tests
├── test_auth_cookie.py             # 10 tests
├── test_failure_injection.py       # 19 tests
├── test_chaos_workflows.py         # 14 tests
├── test_ai_security.py             # 6 tests (5 skipped)
├── test_hermes_security.py         # 27 tests
├── test_voice_engine.py            # 21 tests
├── test_desktop_native.py          # 54 tests (offscreen Qt)
├── test_tauri_packaging.py         # 9 tests
├── test_data_dir_resolution.py     # 4 tests
├── test_cors_tauri.py              # 9 tests
├── test_auth_cookie.py             # 10 tests
├── test_profile_kit.py             # 12 tests
├── test_contradiction_runner.py    # 22 tests
├── test_duplicate_detector.py      # 9 tests
├── test_oar.py                     # 12 tests
└── test_version_backup.py          # 24 tests
```

### Fixtures (conftest.py)

```python
# DB Isolation - CRITICAL
@pytest.fixture(autouse=True, scope="session")
def _isolated_db():
    # Forces DATABASE_URL=sqlite:////tmp/cateye_test_<pid>.db
    # Guard: raises RuntimeError if "catseye.db" appears in URL
    # Cleanup: removes temp DB after session
```

### Test Categories

| Marker | Description | Command |
|--------|-------------|---------|
| (none) | Standard tests | `pytest` |
| `@pytest.mark.asyncio` | Async tests | `pytest` |
| `@pytest.mark.slow` | Slow tests | `pytest -m slow` |
| `@pytest.mark.integration` | Integration | `pytest -m integration` |
| `@pytest.mark.security` | Security | `pytest -m security` |
| `@pytest.mark.desktop` | Desktop (Qt) | `pytest -m desktop` |

## Test Data

### Fixtures

```python
# conftest.py provides:
- tmp_path: temporary directory
- db_session: isolated SQLAlchemy session
- test_client: FastAPI TestClient
- mock_httpx: mocked httpx client
- sample_target, sample_finding, sample_opportunity: factory objects
```

### Factories

```python
# tests/factories.py (if exists)
def make_target(name="test", domain="example.com"):
    return Target(name=name, domain=domain, active=True)


def make_opportunity(platform="hackerone", reward=1000):
    return Opportunity(...)
```

## Test Patterns

### Unit Test
```python
def test_zero_barrier_scorer_normalizes_weights():
    scorer = ZeroBarrierScorer()
    assert abs(sum(scorer.weights.__dict__.values()) - 1.0) < 0.001
```

### Integration Test
```python
@pytest.mark.asyncio
async def test_direct_work_full_cycle(test_client):
    # Discover → Score → Recommend → WorkBank
    resp = await test_client.post("/direct-work/discover", json={"limit": 5})
    assert resp.status_code == 200
    opportunities = resp.json()["opportunities"]
    
    resp = await test_client.post("/direct-work/recommend", json={"opportunities": opportunities})
    assert resp.status_code == 200
    ranked = resp.json()["ranked"]
    assert len(ranked) > 0
```

### API Contract Test
```python
def test_recommend_endpoint_contract(test_client):
    resp = test_client.post("/direct-work/recommend", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "ranked" in data
    assert "total_analyzed" in data
    for item in data["ranked"]:
        assert "rank" in item
        assert "overall_score" in item
        assert "zero_barrier_score" in item
```

### Desktop Test (Qt Offscreen)
```python
@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_mission_control_loads(qapp):
    from desktop.native.views.mission_control import MissionControlView

    view = MissionControlView()
    view.refresh()
    assert view.table.rowCount() >= 0
```

### Failure Injection Test
```python
@pytest.mark.asyncio
async def test_timeout_fallback():
    async def failing_op():
        await asyncio.sleep(0.1)
        raise TimeoutError
    
    async def fallback():
        return "fallback_value"
    
    try:
        await asyncio.wait_for(failing_op(), timeout=0.05)
    except TimeoutError:
        result = await fallback()
    
    assert result == "fallback_value"
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: make test-fast
      - run: make check
```

### Test Exclusions

```python
# pytest.ini / pyproject.toml
[tool.pytest.ini_options]
addopts = "
    --timeout=60
    --ignore=tests/test_security.py
    --ignore=tests/test_vision_gateway.py
    --ignore=tests/test_scheduler.py
    --deselect=tests/test_desktop_release.py::TestDesktopRelease::test_hwid_*"
```

**Excluded Tests:**
- `test_security.py` — External network calls, flaky
- `test_vision_gateway.py` — Gemini rate limits
- `test_scheduler.py` — HTTP to external sources
- `test_desktop_release.py::test_hwid_*` — HWID flaky (passes in isolation)

## Coverage

```bash
# Backend coverage
.venv/bin/python -m pytest --cov=cores --cov=api --cov-report=term-missing

# Frontend coverage
cd frontend && npx vitest run --coverage
```

### Target Coverage
| Module | Target | Current |
|--------|--------|---------|
| `cores/direct_work_engine` | >90% | ~95% |
| `cores/revenue_tracker` | >85% | ~90% |
| `cores/trading` | >80% | ~85% |
| `api/routers/direct_work` | >85% | ~90% |
| `cores/ai/runtime` | >80% | ~85% |

## Debugging Tests

### Verbose Output
```bash
pytest tests/test_direct_work_engine.py::TestZeroBarrierScorer::test_best_case_scores_very_low_barrier -vvs
```

### Debug on Failure
```bash
pytest tests/test_direct_work_engine.py --pdb
```

### Parallel Execution
```bash
pytest -n auto  # Uses pytest-xdist
```

### Test Selection
```bash
# By name pattern
pytest -k "zero_barrier"

# By marker
pytest -m "not slow"

# Specific file
pytest tests/test_direct_work_engine.py
```

## Writing New Tests

### Checklist
- [ ] Use `conftest.py` DB isolation (no manual cleanup)
- [ ] Use factories for test data
- [ ] Test both success and error paths
- [ ] Include edge cases (empty, None, boundary values)
- [ ] Mock external dependencies (httpx, external APIs)
- [ ] No hardcoded IDs — use factory objects
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] Desktop tests use `QT_QPA_PLATFORM=offscreen`

### Template
```python
"""Test <module> — <description>."""

import pytest
from <module> import <ClassUnderTest>


class Test<ClassUnderTest>:
    """Tests for <ClassUnderTest>."""
    
    def test_<behavior>_<expected_outcome>(self):
        # Arrange
        sut = <ClassUnderTest>()
        
        # Act
        result = sut.<method>(<input>)
        
        # Assert
        assert result == <expected>
    
    @pytest.mark.asyncio
    async def test_async_<behavior>(self):
        # ...
```

## Test Quality Gates

### Pre-commit
```bash
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pytest-fast
      name: pytest (fast)
      entry: make test-fast
      language: system
      pass_filenames: false
      always_run: true
```

### CI Gate
```yaml
# Required to pass:
- make test-fast (100 passed, 1 skipped)
- make check (lint + typecheck + fast tests)
- npx vue-tsc --noEmit (0 errors)
- npx vite build (success)
```

---

*Document generated from codebase. Last verified: 2026-08-27*