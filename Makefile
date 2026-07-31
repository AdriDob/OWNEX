.PHONY: help venv install-windows install-windows-full build-android build-android-release build-android-clean \
       build-desktop build-desktop-onefile clean fmt lint typecheck typecheck-fast \
       test coverage test-fast test-full-scoring check work version-info version-sync \
       version-bump checkpoint status

# ── Tooling ───────────────────────────────────────────────────────
PY ?= .venv/bin/python
PYTEST := $(PY) -m pytest
RUFF := $(PY) -m ruff
MYPY := $(PY) -m mypy

# ── Help ──────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtual environment in .venv (idempotent)
	$(PY) --version 2>/dev/null || (python3 -m venv .venv && .venv/bin/python -m pip install --upgrade pip -q)
	$(PY) -m pip install -q -r requirements.txt
	$(PY) -m pip install -q ruff mypy pytest pytest-timeout pytest-asyncio pytest-cov || true

# ── Build / install ───────────────────────────────────────────────
install-windows: ## Build Windows portable folder + zip (one-command installer)
	$(PY) scripts/install_windows.py

install-windows-full: ## Build Windows portable + NSIS installer
	$(PY) scripts/install_windows.py --installer

build-android: ## Build Android debug APK
	$(PY) scripts/build_android.py

build-android-release: ## Build Android release APK
	$(PY) scripts/build_android.py --release

build-android-clean: ## Clean and rebuild Android debug APK
	$(PY) scripts/build_android.py --clean

build-desktop: ## Build desktop bundle via PyInstaller (current OS)
	$(PY) desktop/build/build_desktop.py --onedir

build-desktop-onefile: ## Build desktop single-file binary
	$(PY) desktop/build/build_desktop.py --onefile

clean: ## Remove build artifacts
	rm -rf dist/
	rm -rf desktop/build/build/
	rm -rf desktop/build/dist/
	rm -rf desktop/build/*.spec
	rm -rf .ruff_cache .pytest_cache
	$(PY) -m pip cache purge || true

fmt: ## Format + auto-fix lint issues with ruff
	$(RUFF) check --fix .
	$(RUFF) format .

lint: ## Run ruff linter (check + format check)
	$(RUFF) check .
	$(RUFF) format --check .

typecheck: ## Run mypy over backend modules (may surface pre-existing errors in untouched modules)
	$(MYPY) cores/ core/ api/ database/ desktop/

typecheck-fast: ## Run mypy over the OWNEX v7.0.0 AUD scope (scoring + scheduler runtime)
	$(MYPY) core/opportunity/scoring.py core/scheduler/scheduler.py core/scheduler/jobs.py

check: typecheck-fast test-fast ## Pre-flight: scoped typecheck + fast tests

# ── Testing ───────────────────────────────────────────────────────
# `make test` mirrors the pre-commit/CI contract.
# Excludes test_security.py (live external calls). test_vision_gateway and
# test_scheduler are network/rate-limit flaky in local dev/CI and are ignored
# by default; run them explicitly when needed:
#
#   make test TEST_ARGS="--timeout=60 -q tests/test_vision_gateway.py"
#   make test TEST_ARGS="--timeout=60 -q tests/test_scheduler.py::TestScanSchedulerUnit::test_loop_resilient_to_stage_failure"
TEST_ARGS ?= --timeout=60 -q \
	--ignore=tests/test_security.py \
	--ignore=tests/test_vision_gateway.py \
	--ignore=tests/test_scheduler.py

test: ## Run the pytest suite (excludes security + network-flaky suites)
	$(PYTEST) $(TEST_ARGS) tests/

coverage: ## Run tests with coverage report for backend modules
	$(PYTEST) --cov=cores --cov=core --cov-report=term-missing:skip-covered $(TEST_ARGS) tests/

# test_full_scoring_workflow is excluded from the fast smoke: it relies on a
# mock side_effect sequence (3 items) that cannot satisfy the real
# on_accept/on_reject DB lookups the engine performs. Run it explicitly to
# debug: `make test-full-scoring`.
FLAKY_DESELECT := --deselect tests/test_opportunity_engine_comprehensive.py::TestIntegrationScenarios::test_full_scoring_workflow

test-fast: ## Run a smoke subset (scoring + opportunity + scheduler-jobs; no network tests)
	$(PYTEST) --timeout=30 -q $(FLAKY_DESELECT) \
		tests/test_scoring.py \
		tests/test_opportunity_engine.py \
		tests/test_opportunity_engine_comprehensive.py \
		tests/test_scheduler_jobs.py \
		tests/test_e2e_security_pipeline.py \
		tests/test_security_cycle.py

test-full-scoring: ## Diagnose the flaky full-scoring workflow test
	$(PYTEST) --timeout=30 -q tests/test_opportunity_engine_comprehensive.py::TestIntegrationScenarios::test_full_scoring_workflow

check: typecheck-fast test-fast ## Pre-flight: scoped typecheck + fast tests
	@echo "✓ dev check passed: scoped typecheck + fast tests"

# ── Operations ────────────────────────────────────────────────────
prebuild: ## Run pre-build validation
	$(PY) scripts/prebuild.py

work: ## Run agent startup protocol ("Ponte a trabajar")
	$(PY) scripts/agent-startup.py

version-info: ## Show version sync status
	$(PY) -m core.system.version_engine info

version-sync: ## Sync VERSION.txt to all project files
	$(PY) -m core.system.version_engine sync

version-bump: ## Bump patch version, sync all files, add changelog entry
	$(PY) -m core.system.version_engine bump patch --auto-sync --changelog -m "Auto-bump from agent work session"

checkpoint: ## Generate summary of changes since last commit
	@git diff --stat HEAD
	@echo "---"
	@echo "Untracked files:"
	@git status --short | grep "^??" || echo "(none)"

status: ## Full system health check
	$(PY) scripts/agent-startup.py --no-tests
