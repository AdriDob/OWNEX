# VS Code Freeze Diagnostic Report — OWNEX/Rastro Project

**Date:** 2026-11-23
**Environment:** WSL2 (Linux), code-server, 32 GB RAM, 49 GB project
**Symptom:** VS Code freezes completely during AI agent (Devin) work sessions

---

## 1. ENVIRONMENT EVIDENCE

### 1.1 OS and Execution Context
- **OS:** Linux (WSL2) — `Linux ADRI 6.6.114.1-microsoft-standard-WSL2`
- **VS Code:** Running as `code-server` (PID 1066-1182 range)
- **Python backend:** `uvicorn api.main:app` (PID 547) — FastAPI
- **Node.js:** Multiple processes for extensions and server

### 1.2 Project Size and File Count
- **Total size:** 49 GB
- **Total files:** 137,910 files
- **Total directories:** 16,391 directories
- **Major directories:**
  - `database/`: 25 GB (SQLite files, WAL, SHM)
  - `src-tauri/`: 15 GB (Tauri desktop app assets)
  - `work/`: 1.3 GB
  - `dist/`: 1.2 GB
  - `node_modules/`: 306 MB

### 1.3 CPU/Memory Hot Processes (from `ps aux`)
| Process | CPU | Memory | Description |
|---------|-----|--------|-------------|
| **Extension Host** (PID 1182) | **86.9%** | 11.3% | VS Code extension host — primary freeze cause |
| **Pylance** (PID 2589) | **83.1%** | 2.5 GB | Python language server — massive indexing load |
| Node (various) | 2-22% | varying | Extension language servers (Java, JavaScript, etc.) |
| python (uvicorn) | 55.6% | 410 MB | FastAPI backend serving API requests |
| code-server bootstrap | 17.1% | 423 MB | VS Code server main process |

### 1.4 Installed Extensions (50+ total)
Key extensions (from `.vscode/extensions.json` and installed list):
- `ms-python.python` — core Python support
- `ms-python.vscode-pylance` — language server (83% CPU!)
- `charliermarsh.ruff` — linter/formatter
- `ms-python.mypy-type-checker` — type checking
- `georgewfraser.vscode-javac` — Java language server
- `bradlc.vscode-tailwindcss` — Tailwind support
- `eamodio.gitlens` — Git enhancements
- `Evan.vscode-codeglot` — AI code translation
- `anthropic.claude-code` — Claude agent integration
- `vizards.deepseek-v4-for-copilot` — DeepSeek integration
- `EunomiaDevelopersInc.cfpynb` — Jupyter notebooks
- `ms-vscode.charliecalcs` — Calculator extension
- And many more (PHP, C++, Docker, Kubernetes, etc.)

### 1.5 Key Configuration (`.vscode/settings.json`)
- `files.exclude`: Already excludes caches, dist, build, node_modules, venv
- `search.exclude`: Similar exclusions
- `files.watcherExclude`: Watcher exclusions configured
- `python.analysis.indexing`: `true` (full indexing — problem!)
- `python.analysis.diagnosticMode`: `"workspace"`
- `python.analysis.typeCheckingMode`: `"basic"` (not strict)
- `ruff.enable`: `true`
- `ruff.importStrategy`: `"fromEnvironment"`
- `git.autofetch`: `false` (good — avoids git scanning overhead)
- `git.enableStatusSync`: `false` (good)

---

## 2. ROOT CAUSE ANALYSIS

### 2.1 Primary Cause: Pylance Over-indexing
The **Microsoft Pylance language server** is consuming 83.1% CPU because it is attempting to index the entire 49 GB project, including:

- **25 GB of SQLite database files** (`database/*.db`, `*.sqlite`, `*.sqlite3`)
- **15 GB of Tauri build artifacts** (`src-tauri/`)
- **306 MB of node_modules** dependencies
- **Multiple cache directories** (.mypy_cache, .ruff_cache, .pytest_cache)
- **All 137,910 source files** across core/, cores/, api/, frontend/, etc.

Pylance's analysis mode is set to `"workspace"`, which means it indexes every file in the workspace root. The `python.analysis.indexing` is `true` with no `include` paths configured, so it scans everything.

### 2.2 Secondary Cause: Extension Host CPU Spin
The **Extension Host** process is at 86.9% CPU, likely because:
- Multiple language servers are running simultaneously (Pylance, Java LS, TypeScript LS, ESLint, Biome)
- The host is constantly watching for file changes across the massive project
- AI-agent (Devin) modifications trigger continuous re-indexing

### 2.3 Tertiary Cause: Git Autofetch Disabled But Status Sync Active
While `git.autofetch` is `false` (good), `git.enableStatusSync` is also `false` (good), but there are still many Git-related extensions (GitLens, githistory, github.actions) that may be scanning the repo metadata.

### 2.4 Agent Workflow Interaction
When Devin/other agents work on OWNEX:
1. They modify source files, generate caches, create worktrees
2. VS Code's file watchers detect every change
3. Pylance re-indexes modified files
4. The extension host processes notifications
5. **Result:** CPU spikes to 100%, UI freezes, terminal becomes unresponsive

---

## 3. OPTIMIZATION PLAN — PHASE BY PHASE

### ⚠️ PRE-OPTIMIZATION: PRESERVATION CHECKLIST
Before making any changes:
- [x] Git commit or stash all modifications
- [x] Document current `.vscode/settings.json`
- [x] Note installed extensions and their configurations
- [x] Preserve the `.venv` and virtual environment
- [x] Backup any agent-specific configurations

### PHASE A: IMMEDIATE PYLANCE OPTIMIZATION (Highest Impact)

**Current Problem:** Pylance indexing entire 49GB project including databases and node_modules.

**Fixes (all reversible):**

1. **Configure Pylance to analyze only relevant directories:**

   Update `.vscode/settings.json` — add `python.analysis.extraPaths` and `python.analysis.include`:

   ```json
   "python.analysis.extraPaths": [
     "core",
     "api",
     "frontend/src",
     "database"
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
     "desktop-installer",
     "archive_cleanup",
     "logs",
     "coverage",
     "**/__pycache__",
     "desktop/**"
   ]
   ```

   **Rationale:** 
   - `extraPaths` points Pylance to the actual source directories
   - `include` restricts analysis to Python/TypeScript source only
   - `exclude` blocks databases, caches, build outputs, and agent artifacts
   - **Reversible:** Just remove these sections to restore full indexing

2. **Reduce Pylance diagnostic mode:**

   ```json
   "python.analysis.diagnosticMode": "off"
   ```

   **Note:** This disables real-time diagnostics but reduces CPU dramatically. You can still run `ruff` manually for linting.

3. **Set type checking to "basic" or "off"**:

   Already set to `"basic"` — good. Can be changed to `"off"` if needed.

### PHASE B: FILE WATCHER EXCLUSIONS (High Impact)

**Current:** `files.watcherExclude` already has many exclusions but may need refinement.

**Additional exclusions for `.vscode/settings.json`:**

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
  "core/cores/**": true,  /* Accidental duplicate - see Phase C */
  "**/.pytest_cache/**": true,
  "**/.mypy_cache/**": true,
  "**/.ruff_cache/**": true,
  "archive_cleanup/": true,
  "htmlcov/**": true,
  ".nyc_output/**": true
}
```

**Rationale:** These paths are either generated files, third-party dependencies, or agent artifacts that don't need watching. The watcher will stop polling them, reducing CPU load.

**Verification after implementation:**
- Run `code .` and observe if the "indexing" badge disappears or slows
- Check `Developer: Show Running Extensions` → verify Pylance status
- Monitor CPU with `top` or `htop` during agent work

### PHASE C: GIT OPTIMIZATION (Medium Impact)

**Current:** `git.autofetch: false` (good), but many Git extensions are active.

**Changes:**

1. **Ensure `git.enableStatusSync` remains `false`** — already the case.

2. **Consider limiting GitLens scope:** GitLens is powerful but can be heavy on large repos. If freezing persists, consider:
   - Disabling "GitLens.annotations.enabled" temporarily
   - Or using `gitlens.advanced.trace` to monitor its impact

3. **Worktree management:** The project has worktrees (mentioned in `.ai/TASK_QUEUE.md`). Ensure:
   - Obsolete worktrees are removed (not destructively, but via `git worktree remove <path>`)
   - Active worktrees are kept separate from the main VS Code workspace

### PHASE D: EXTENSION AUDIT AND REDUCTION (Medium Impact)

**Current:** 50+ extensions installed, many may be redundant.

**Analysis of high-impact extensions:**

| Extension | Purpose | Potential Optimization |
|-----------|---------|----------------------|
| `ms-python.vscode-pylance` | Python language server | **Primary target** — configure exclusions (Phase A) |
| `charliermarsh.ruff` | Lint/formatter | Keep — lightweight, replaces flake8/black |
| `ms-python.python` | Python core | Keep — but configure analysis scope |
| `georgewfraser.vscode-javac` | Java language server | **Consider disabling** if not actively used — heavy |
| `bradlc.vscode-tailwindcss` | Tailwind CSS | Keep — lightweight |
| `eamodio.gitlens` | Git enhancements | Keep, but monitor CPU |
| `anthropl.claude-code` | Claude integration | May trigger agent interactions — monitor |
| `vizards.deepseek-v4-for-copilot` | DeepSeek/Copilot | Monitor — AI extensions can spawn background processes |
| `ms-python.mypy-type-checker` | MyPy type checker | Already `typeCheckingMode: basic` — okay |

**Recommendation:** 
- Keep: `ruff`, `python`, `tailwindcss`, `gitlens`, `even-better-toml`
- Temporarily disable: `javac`, ` Claude-code`, `deepseek-v4-for-copilot` to test if freezing stops
- Re-enable one-by-one to identify the specific culprit

### PHASE E: COORDINATION WITH DEVIN/AGENTS (Critical)

Based on the megaprompt's Phase F, design a collaboration protocol:

1. **Agent file ownership:** When Devin modifies a file, it should work in a dedicated worktree, not directly in the VS Code workspace root.

2. **Controlled builds/tests:** Instead of VS Code auto-triggering on every save, agents should:
   - Run `make test` or `pytest` explicitly from terminal
   - Not rely on VS Code's auto-save + lint cycle

3. **Indexing pause during agent work:** Consider adding a VS Code setting or script that:
   - Disables file watching when an agent task starts
   - Re-enables after the task completes

4. **Change integration protocol:**
   - Agent modifies files in a `work/` subdirectory or dedicated worktree
   - After task completion, changes are merged via `git` from the terminal
   - VS Code then reloads (not watches continuously)

5. **Preserve Progress Ledger:** Ensure that agent work sessions update `.ai/PROGRESS.md` and create snapshots via `python3 scripts/progress.py`, so no advances are lost.

### PHASE F: MEASUREMENT — BEFORE AND AFTER

**Before optimization indicators:**
- Extension Host CPU: **86.9%**
- Pylance CPU: **83.1%**
- VS Code responsiveness: Freezes during agent work
- Indexing time: Continuous, never completes fully

**After optimization indicators (target):**
- Extension Host CPU: **< 30%** (target 50% reduction)
- Pylance CPU: **< 30%** (target 60% reduction)
- VS Code responsiveness: Smooth during agent work
- Indexing: Completes or stabilizes at low level

**Measurement methodology:**
1. Record `top` output before changes
2. Run a representative Devin task (e.g., "add a new source adapter")
3. Record `top` output after changes
4. Compare CPU, memory, and responsiveness
5. Document in `.vscode/DEVELOPER_WORKSTATION.md`

---

## 4. IMPLEMENTATION — REVERSIBLE CHANGES

### 4.1 Edit `.vscode/settings.json`

Apply the optimizations from Phases A-E. Here's the **complete optimized settings.json**:

```json
{
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true,
    "**/*.pyc": true,
    "archive_cleanup/": true,
    "dist/": true,
    "build/": true,
    "android/": true,
    "desktop/installer/": true,
    "**/*.egg-info": true
  },
  "search.exclude": {
    "archive_cleanup/": true,
    "dist/": true,
    "build/": true,
    "node_modules/": true,
    ".venv/": true,
    "android/": true,
    "**/__pycache__": true,
    "**/*.min.js": true,
    "**/*.map": true,
    "logs/": true,
    "**/node_modules/": true,
    "coverage/": true
  },
  "files.watcherExclude": {
    "archive_cleanup/**": true,
    "dist/**": true,
    "build/**": true,
    "node_modules/**": true,
    ".venv/**": true,
    "android/**": true,
    "**/__pycache__/**": true,
    "**/.git/objects/**": true,
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
    ".nyc_output/**": true
  },
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
  ],
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": false,
  "ruff.enable": true,
  "ruff.importStrategy": "fromEnvironment",
  "ruff.lint.run": "onType",
  "ruff.format.args": [],
  "git.enabled": true,
  "git.autofetch": false,
  "git.enableStatusSync": false,
  "git.decorations.enabled": false,
  "git.countContributors": false,
  "git.openRepositoryCount": 1,
  "git.enableStatusSync": false,
  "editor.minimap.enabled": false,
  "editor.lightbulb.enabled": "off",
  "editor.hover.enabled": "off",
  "editor.parameterHints.enabled": false,
  "editor.suggest.showStatusBar": false,
  "editor.semanticHighlighting.enabled": false,
  "extensions.ignoreRecommendations": true,
  "workbench.startupEditor": "none",
  "workbench.tips.enabled": false,
  "workbench.colorTheme": "Abyss",
  "window.titleBarStyle": "custom",
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 2000,
  "problems.autoReveal": false,
  "breadcrumbs.enabled": false,
  "update.showReleaseNotes": false,
  "telemetry.telemetryLevel": "off",
  "terminal.integrated.gpuAcceleration": "on",
  "terminal.integrated.shellIntegration.enabled": false,

  "task.allowAutomaticTasks": "on",
  "python.terminal.useEnvFile": true
}
```

### 4.2 Optional: Disable Pylance Entirely (If Freezing Persists)

If the above doesn't suffice, you can disable Pylance and use `ruff` + `mypy` from the command line instead:

1. In `.vscode/settings.json`, add:
   ```json
   "python.languageServer": "None"
   ```

2. Install `ruff` for linting (already enabled) and use `mypy` from terminal:
   ```bash
   cd /home/adriel/projects/Rastro
   .venv/bin/mypy core/ api/ frontend/src/
   ```

3. **Note:** This removes the integrated Python language server intelligence (type hints, go-to-definition, etc.) within VS Code, but the language server still runs externally. Reversible by removing `"python.languageServer": "None"`.

### 4.3 Create Diagnostic Script

Create `/home/adriel/projects/Rastra/scripts/debug_vscode.py` (or similar) for ongoing monitoring:

```python
#!/usr/bin/env python3
"""VS Code freeze diagnostic — monitor CPU/memory during agent work."""

import subprocess
import json
import time
from datetime import datetime

def get_vscode_processes():
    """Get VS Code-related process resource usage."""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True, text=True
    )
    processes = []
    for line in result.stdout.split("\n"):
        if any(keyword in line.lower() for keyword in ["code-server", "pylance", "extension", "node"]):
            parts = line.split()
            if len(parts) > 10:
                processes.append({
                    "command": parts[10:],
                    "cpu": parts[2],
                    "mem": parts[3],
                    "rss": parts[5],
                    "pid": parts[1]
                })
    return processes

def main():
    print(f"=== VS Code Freeze Diagnostic ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    processes = get_vscode_processes()
    if processes:
        print("VS Code related processes:")
        for p in processes:
            print(f"  PID {p['pid']}: {p['command']} — CPU: {p['cpu']}%, MEM: {p['mem']}%, RSS: {p['rss']} MB")
    else:
        print("No VS Code-related processes found with current filters.")
    
    # Check VS Code version and extensions
    try:
        result = subprocess.run(
            ["code-server", "--versions"],
            capture_output=True, text=True
        )
        print(f"\ncode-server versions output: {result.stdout[:500]}")
    except:
        pass
    
    # Check project size
    import os
    total_size = 0
    for dirpath, dirnames, filenames in os.walk("/home/adriel/projects/Rastro"):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    
    print(f"\nProject approximated size: {total_size / (1024**3):.1f} GB")
    print(f"Files: ~137,910 (known count)")
    
    # Target thresholds
    print("\n--- Thresholds ---")
    print("Target: Extension Host CPU < 30%")
    print("Target: Pylance CPU < 30%")
    print("Target: VS Code responsive during agent tasks")

if __name__ == "__main__":
    main()
```

Make it executable and run periodically during agent work sessions.

---

## 5. VALIDATION PROCEDURE

After applying optimizations:

### 5.1 Immediate Checks
- [ ] VS Code window responsive (no "not responding")
- [ ] `top` shows Extension Host < 30% CPU (was 86.9%)
- [ ] `top` shows Pylance < 30% CPU (was 83.1%)
- [ ] File indexing badge (bottom-right) stabilizes or disappears

### 5.2 Functional Checks
- [ ] Python auto-completion still works in `core/` and `api/`
- [ ] `ruff` linting runs from command line: `cd /home/adriel/projects/Rastro && .venv/bin/ruff check .`
- [ ] Navigation (go-to-definition, find references) works for source files
- [ ] Tests can be run: `cd /home/adriel/projects/Rastro && .venv/bin/pytest tests/ -x -q` (should pass)

### 5.3 Agent Work Session Test
- [ ] Run a minimal Devin/task agent task
- [ ] Observe CPU during and after the task
- [ ] Verify no freeze or, if freeze occurs, it's brief (< 5 seconds vs. minutes)
- [ ] Confirm findings/reports are saved to `.ai/PROGRESS.md`
- [ ] Update progress snapshot: `python3 scripts/progress.py`

### 5.4 Rollback Plan
If optimizations cause issues:
1. Remove the `python.analysis.extraPaths`, `include`, and `exclude` sections from settings.json
2. Restore `files.watcherExclude` to original
3. Re-enable any disabled extensions
4. Reload VS Code (`Ctrl+Shift+P` → "Developer: Reload Window")
5. Verify everything returns to previous state

---

## 6. DOCUMENTATION TO CREATE/UPDATE

- [ ] `.vscode/settings.json` — optimized version (above)
- [ ] `docs/DEVELOPER_WORKSTATION.md` — documented workspace configuration
- [ ] `docs/VSCODE_PERFORMANCE.md` — performance diagnosis and fixes
- [ ] `scripts/debug_vscode.py` — diagnostic script (created above)
- [ ] `.ai/progress_snapshot.json` — update after agent sessions
- [ ] `.ai/TASK_QUEUE.md` — note any worktree/agent coordination changes

---

## 7. SUMMARY OF CHANGES

| Change | Impact | Reversible | Effort |
|--------|--------|------------|--------|
| `python.analysis.extraPaths` + `include` + `exclude` | **HIGH** — directs Pylance to scan only source files | Yes (remove sections) | Low |
| `files.watcherExclude` additions | **HIGH** — stops polling generated/cache dirs | Yes (remove entries) | Low |
| `python.analysis.diagnosticMode: "off"` | **MEDIUM** — disables real-time errors | Yes (set back to "workspace") | Low |
| Disable Pylance entirely (`python.languageServer: "None"`) | **MEDIUM-LOW** — removes LS intelligence | Yes (remove setting) | Low |
| Disable Java LS (`georgewfraser.vscode-javac`) | **LOW-MEDIUM** if not using Java | Yes (disable extension) | Low |
| GitLens annotations reduction | **LOW** if many annotations | Yes (toggle settings) | Low |

**Expected result:** 60-70% reduction in CPU usage by VS Code extensions, eliminating the freezes during Devin/agent work sessions while maintaining enough language intelligence for productive development.

---
*Diagnostic complete. Evidence based on process monitoring, project structure analysis, and VS Code configuration review.*