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
# The PyInstaller spec (OWNEX-Backend.spec) is ONEFILE by design: Tauri v2
# resolves externalBin to exactly one file per target triple, and a ONEDIR
# copy without its _internal/ directory cannot import api.main (the
# failure that shipped in the 2026-08-24 MSI). Both targets below therefore
# emit the same self-contained binary; `build-desktop` keeps its name for
# compatibility with existing muscle memory.
install-windows: ## Build Windows portable folder + zip (one-command installer)
	$(PY) scripts/install_windows.py

install-windows-full: ## Build Windows portable + MSI installer
	$(PY) scripts/install_windows.py --installer

build-android: ## Build Android debug APK
	$(PY) scripts/build_android.py

build-android-release: ## Build Android release APK
	$(PY) scripts/build_android.py --release

build-android-clean: ## Clean and rebuild Android debug APK
	$(PY) scripts/build_android.py --clean

build-desktop: ## Build desktop bundle via PyInstaller (current OS) -> dist/ownex-backend
	$(PY) desktop/build/build_desktop.py --onefile

build-desktop-onefile: ## Build desktop single-file binary (same as build-desktop)
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
	$(MYPY) cores/ api/ database/ desktop/

typecheck-fast: ## Run mypy over the OWNEX v7.0.0 AUD scope (scoring + scheduler runtime)
	$(MYPY) cores/opportunity/scoring.py cores/scheduler/scheduler.py cores/scheduler/jobs.py

check: typecheck-fast test-fast ## Pre-flight: scoped typecheck + fast tests

# ── Testing ───────────────────────────────────────────────────────
# `make test` mirrors the pre-commit/CI contract.
# Excludes test_security.py (live external calls). test_vision_gateway and
# test_scheduler are network/rate-limit flaky in local dev/CI and are ignored
# by default.
#
# Re-enabled 2026-10-01 (la condición era "cuando ese flujo aterrice"):
#   · test_financial_hub — importaba `api.routers.financial_hub`, movido a
#     `_archived/` en el polish del 2026-09-28. Ahora apunta a su ruta real.
#   · test_self_improvement — 4 stubs ("for backward compatibility") que el
#     engine llamaba igual: ExecutionPolicy, ScaffoldGenerator, NoveltyScorer
#     y RewardModel. Implementados con la fórmula ya documentada en
#     models.py:242 (R = Validity × Difficulty × Novelty).
# Para correr los flaky de red explícitamente:
#
#   make test TEST_ARGS="--timeout=60 -q tests/test_vision_gateway.py"
#   make test TEST_ARGS="--timeout=60 -q tests/test_scheduler.py::TestScanSchedulerUnit::test_loop_resilient_to_stage_failure"
#
# NOTE (2026-09-09): commits gate on `make test-fast` (10s deterministic smoke),
# NOT on this full run. `make test` is available explicitly.
TEST_ARGS ?= --timeout=60 -q \
	--ignore=tests/test_security.py \
	--ignore=tests/test_vision_gateway.py \
	--ignore=tests/test_scheduler.py

test: ## Run the pytest suite (excludes security + network-flaky + foreign WIP suites)
	$(PYTEST) $(TEST_ARGS) tests/

coverage: ## Run tests with coverage report for backend modules
	$(PYTEST) --cov=cores --cov-report=term-missing:skip-covered $(TEST_ARGS) tests/

# test_full_scoring_workflow was excluded from the fast smoke while its mock
# side_effect was undersized (KNOWN_DEBT #10). The side_effect now provisions
# all 8 DB lookups (commit eade07f87) and the test passes deterministically
# (SELF-6, 2026-08-11) — no longer deselected.
FLAKY_DESELECT :=

test-fast: ## Run a smoke subset (scoring + opportunity + scheduler-jobs; no network tests)
	$(PYTEST) --timeout=30 -q $(FLAKY_DESELECT) \
		tests/test_scoring.py \
		tests/test_opportunity_engine.py \
		tests/test_opportunity_engine_comprehensive.py \
		tests/test_scheduler_jobs.py \
		tests/test_e2e_security_pipeline.py \
		tests/test_security_cycle.py

test-full-scoring: ## Run the full-scoring workflow test (formerly flaky, now deterministic)
	$(PYTEST) --timeout=30 -q tests/test_opportunity_engine_comprehensive.py::TestIntegrationScenarios::test_full_scoring_workflow

check: typecheck-fast test-fast ## Pre-flight: scoped typecheck + fast tests
	@echo "✓ dev check passed: scoped typecheck + fast tests"

release-check: ## FINAL RELEASE GATE — backend+frontend+lint+build (Parte 4 megaprompt)
	@echo "════ OWNEX release-check ════"
	$(PY) -m ruff check cores/execution_queue/ cores/device_identity/ cores/sync/ cores/license/validator.py cores/direct_work_engine/workbank.py api/routers/device.py api/routers/direct_work.py
	@echo "[1/5] lint touched: OK"
	$(PYTEST) --timeout=60 -q tests/test_income_chain_e2e.py tests/test_execution_mirror.py tests/test_workbank.py tests/test_daily_mode.py tests/test_revenue_engine.py tests/test_revenue_pipeline.py tests/test_direct_work_api.py tests/test_execution_queue.py tests/test_execution_queue_store.py tests/test_state_convergence.py tests/test_availability_engine.py tests/test_scheduler_jobs.py
	@echo "[2/5] backend core: OK"
	cd frontend && npx vue-tsc --noEmit && npx vitest run
	@echo "[3/5] frontend tsc+tests: OK"
	cd frontend && npx vite build
	@echo "[4/5] frontend build: OK"
	$(PYTEST) --timeout=60 -q tests/test_tauri_packaging.py tests/test_cors_tauri.py tests/test_data_dir_resolution.py tests/test_desktop_release.py tests/test_desktop_native.py
	@echo "[5/5] packaging+desktop guards: OK"
	@echo "════ release-check PASS ════"

# ── Operations ────────────────────────────────────────────────────
prebuild: ## Run pre-build validation
	$(PY) scripts/prebuild.py

work: ## Run agent startup protocol ("Ponte a trabajar")
	$(PY) scripts/agent-startup.py

version-info: ## Show version sync status
	$(PY) -m cores.system.version_engine info

version-sync: ## Sync VERSION.txt to all project files
	$(PY) -m cores.system.version_engine sync

version-bump: ## Bump patch version, sync all files, add changelog entry
	$(PY) -m cores.system.version_engine bump patch --auto-sync --changelog -m "Auto-bump from agent work session"

checkpoint: ## Generate summary of changes since last commit
	@git diff --stat HEAD
	@echo "---"
	@echo "Untracked files:"
	@git status --short | grep "^??" || echo "(none)"

status: ## Full system health check
	$(PY) scripts/agent-startup.py --no-tests

daily: ## Daily briefing (full)
	$(PY) scripts/daily.py

daily-quick: ## Daily briefing (essentials only)
	$(PY) scripts/daily.py --quick

daily-json: ## Daily briefing as JSON
	$(PY) scripts/daily.py --json

scheduler-start: ## Start scheduler in background
	$(PY) -m api.scheduler &

scheduler-stop: ## Stop scheduler
	pkill -f "api.scheduler" || true

scheduler-logs: ## Show scheduler logs
	tail -f /home/adriel/.ownex/logs/scheduler.log 2>/dev/null || echo "No scheduler logs found"

missing-creds: ## Show missing credentials with setup links
	$(PY) -c "from cores.credentials.sync import prompt_missing_credentials; prompt_missing_credentials()"

sync-creds: ## Sync credentials from DB to .env
	$(PY) -c "from cores.credentials.sync import sync_settings_to_env; print(sync_settings_to_env())"



security-run: ## Run full security cycle once (usage: make security-run DOMAIN=example.com)
	$(PY) scripts/security_run.py $(DOMAIN)

target-add: ## Add a new target (usage: make target-add NAME=foo DOMAIN=foo.com)
	$(PY) scripts/target_add.py $(NAME) $(DOMAIN)

first-run: ## Interactive first-time setup wizard
	$(PY) scripts/first_run.py


	$(PY) scripts/first_run.py

watch: ## Watch daily briefing every 5 min (Ctrl+C to stop)
	watch -n 300 'make daily-quick'

backup: ## Backup database and config
	$(PY) scripts/backup.py

logs: ## Tail all service logs
	tail -f /home/adriel/.ownex/logs/*.log 2>/dev/null || echo "No logs found"
