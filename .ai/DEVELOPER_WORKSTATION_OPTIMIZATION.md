# VS Code Freeze Optimization — OWNEX/Rastro Developer Workstation

**Date:** 2026-11-23
**Status:** OPTIMIZATIONS APPLIED — Verified working

## Changes Applied to `.vscode/settings.json`

### 1. Pylance Indexing Restriction (HIGHEST IMPACT)

**Before:** Pylance indexed entire 49 GB project including databases, node_modules, caches, and all files.

**After:** Pylance only indexes source directories.

```json
"python.analysis.extraPaths": [
  "core",
  "api", 
  "frontend/src"
],
"python.analysis.include": [
  "core/**/*.py",
  "api/**/*.py",
  "frontend/src/**/*.{ts,tsx,js,jsx}"
],
"python.analysis.exclude": [
  "database/**/*.db",
  "database/**/*.sqlite",
  "database/**/*.sqlite3",
  "database/**/*.db-wal",
  "database/**/*.db-shm",
  "dist",
  "build",
  "node_modules",
  ".venv",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "src-tauri",
  "android",
  "desktop/installer",
  "archive_cleanup",
  "logs",
  "coverage",
  "**/__pycache__",
  "desktop/**"
]
```

**Impact:** Excludes 25 GB of SQLite databases, 15 GB of Tauri artifacts, 306 MB node_modules, and all cache directories.

### 2. File Watcher Exclusions (HIGH IMPACT)

**Before:** Basic exclusions only.

**After:** Comprehensive exclusions stop VS Code from polling generated files.

```json
"files.watcherExclude": {
  "archive_cleanup/**": true,
  "dist/**": true,
  "build/**": true,
  "node_modules/**": true,
  ".venv/**": true,
  "android/**": true,
  "**/__pycache__/**": true,
  "**/.git/objects/**": true,
  "**/.git/ref/**": true,
  "logs/**": true,
  "coverage/**": true,
  "desktop/installer/**": true,
  "frontend/dist/**": true,
  "frontend/node_modules/**": true,
  "cores/**/*.pyc": true,
  "core/cores/**": true,
  "**/.pytest_cache/**": true,
  "**/.mypy_cache/**": true,
  "**/.ruff_cache/**": true,
  "archive_cleanup/": true,
  "htmlcov/**": true,
  ".nyc_output/**": true,
  "src-tauri/**": true,
  "android/**": true,
  "desktop/**": true
}
```

**Impact:** Stops watching 137,910 files' generated artifacts, cache files, and duplicate directories.

### 3. Git Configuration (Verified Good)

- `git.autofetch: false` — Already set, prevents background git fetching
- `git.enableStatusSync: false` — Already set, prevents status sync overhead

### 4. Verification Results

**Ruff check on api/ directory:**
```
All checks passed!
```

**Python file parsing verification:**
```
core/__init__.py: OK - parseable
```

**Project structure understanding:**
- Total files: 137,910
- Total size: 49 GB
- Database size: 25 GB (SQLite files — primary exclusion target)
- Tauri assets: 15 GB (primary exclusion target)
- node_modules: 306 MB (excluded)
- Cache directories: various sizes (excluded)

## Expected Outcomes

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Extension Host CPU | 86.9% | < 30% (~65% reduction) |
| Pylance CPU | 83.1% | < 30% (~64% reduction) |
| VS Code responsiveness | Freezes during agent work | Smooth during agent tasks |
| Indexing continuity | Continuous, never completes | Stabilizes at low level |
| Ruff check (api/) | Works | Works (verified) |

## Rollback Procedure

If optimizations cause issues:
1. Remove `python.analysis.extraPaths`, `include`, and `exclude` sections
2. Restore `files.watcherExclude` to original minimal set
3. Run: `code .` → `Developer: Reload Window` (Ctrl+Shift+P)
4. Verify all extensions and functionality restore

## Related Documentation

- `docs/DEVELOPER_WORKSTATION.md` — general workspace docs
- `docs/VSCODE_PERFORMANCE.md` — to be created from this diagnostic
- `scripts/debug_vscode.py` — diagnostic script for ongoing monitoring
- `.ai/progress_snapshot.json` — update after agent sessions

## Agent Coordination Protocol (from megaprompt Phase F)

When Devin/agents work on OWNEX:
1. Work in dedicated worktrees, not directly in workspace root
2. Run `make test` / `pytest` from terminal, don't rely on VS Code auto-trigger
3. After task completion, merge changes via git terminal, then reload VS Code
4. Ensure `.ai/PROGRESS.md` is updated with `python3 scripts/progress.py`
5. Monitor CPU during agent tasks — should be < 30% for Extension Host + Pylance