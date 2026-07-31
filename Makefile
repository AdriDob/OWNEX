.PHONY: help install-windows build-android build-desktop clean lint typecheck test prebuild work version-info version-sync version-bump checkpoint status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install-windows: ## Build Windows portable folder + zip (one-command installer)
	python scripts/install_windows.py

install-windows-full: ## Build Windows portable + NSIS installer
	python scripts/install_windows.py --installer

build-android: ## Build Android debug APK
	python scripts/build_android.py

build-android-release: ## Build Android release APK
	python scripts/build_android.py --release

build-android-clean: ## Clean and rebuild Android debug APK
	python scripts/build_android.py --clean

build-desktop: ## Build desktop bundle via PyInstaller (current OS)
	python desktop/build/build_desktop.py --onedir

build-desktop-onefile: ## Build desktop single-file binary
	python desktop/build/build_desktop.py --onefile

clean: ## Remove build artifacts
	rm -rf dist/
	rm -rf desktop/build/build/
	rm -rf desktop/build/dist/
	rm -rf desktop/build/*.spec

lint: ## Run ruff linter
	python -m ruff check .

typecheck: ## Run mypy type checker
	python -m mypy cores/ api/ database/ desktop/

test: ## Run test suite with coverage
	python -m pytest tests/ -v --tb=short --cov=cores --cov-report=term-missing:skip-covered

prebuild: ## Run pre-build validation
	python scripts/prebuild.py

work: ## Run agent startup protocol
	python scripts/agent-startup.py

version-info: ## Show version sync status
	python -m core.system.version_engine info

version-sync: ## Sync VERSION.txt to all project files
	python -m core.system.version_engine sync

version-bump: ## Bump patch version, sync all files, add changelog entry
	python -m core.system.version_engine bump patch --auto-sync --changelog -m "Auto-bump from agent work session"

checkpoint: ## Generate summary of changes since last commit
	@git diff --stat HEAD
	@echo "---"
	@echo "Untracked files:"
	@git status --short | grep "^??" || echo "(none)"

status: ## Full system health check
	python scripts/agent-startup.py --no-tests
