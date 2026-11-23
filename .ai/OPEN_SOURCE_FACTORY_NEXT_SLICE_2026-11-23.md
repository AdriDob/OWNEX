# OWNEX — Open Source Earning Factory: audit and next implementation slice

**Audit date:** 2026-11-23  
**Base commit:** `965de37168dfda3e484422b872c68a6c8077c0bd`  
**Status:** READ-ONLY AUDIT COMPLETE · IMPLEMENTATION NOT STARTED

## 1. Product focus

Prioritize OWNEX as an AI-assisted engineering system for earning rewards by completing publicly available software and open-source projects.

The primary user journey is:

`DISCOVER → VERIFY → QUALIFY → PREPARE → IMPLEMENT → TEST → REVIEW → OWNER APPROVAL → SUBMIT → ACCEPT → GET PAID`

This is a product-priority decision, not a deletion of other OWNEX capabilities. Keep the existing source catalog, Work Bank, payment intelligence, security controls and finance ledger. Do not add another opportunity engine or another execution state machine.

OWNEX should do the reversible engineering work autonomously where safely supported. The owner retains approval over external commitments: claiming a bounty, publishing a pull request, submitting work, accepting terms and moving money.

## 2. Existing components to reuse

| Responsibility | Existing implementation | Audit finding |
|---|---|---|
| Public opportunity discovery | `cores/opportunity/live_pipeline.py` | Real fetcher registry and provenance-aware LiveStore exist. |
| Work prioritization | `cores/direct_work_engine/workbank.py` | Canonical WorkBank; prepared items are mirrored into ExecutionQueue. |
| Guided earning | `core/opportunity/guided_earning.py`, `api/routers/guided_earning.py` | The latest workspace joins journey, execution guide, resume point and account-verification blockers. |
| Repository preparation | `cores/opportunity/live_pipeline.py::prepare_execution` | Fetches GitHub issue/repository metadata, shallow-clones public repositories and writes an evidence pack. No claim or submission. |
| Repository analysis | `cores/opportunity/live_pipeline.py::analyze_workspace` | Reuses RepoAnalyzer; can inspect language, package manager, test/build commands and entry points. Optional tests currently execute through TestRunner. |
| AI code generation | `core/autonomy/code_generator.py` | Generates a structured GenerationPlan with proposed file changes. |
| Coding orchestration | `core/autonomy/coder_agent.py` | Has issue analysis, generation, test, retry and PR stages, but contains integration defects listed below. |
| Queue lifecycle | `core/execution_queue/models.py`, `core/execution_queue/mirror.py` | One persisted state machine; WorkBank preparation already advances items to `ready`. |
| Security boundary | `core/security/sandbox.py`, `core/security/credential_broker.py` | Docker policy and project-scoped credentials exist; runtime suitability for external code still needs verification. |
| Revenue truth | Revenue Ledger / payout evidence | A reported reward, accepted submission and received payment must remain separate states. |

## 3. Verified blockers

### B1 — CoderAutopilot resets the queue item and requests an illegal transition

File: `core/cycles/tasks_coder_autopilot.py::_solve_one`

- WorkBank calls `mirror_workbank_prepared`, which creates or advances the item through `discovered → qualified → ready`.
- `_solve_one` then calls `eq.add(item.id, ...)` unconditionally. This overwrites the existing mirrored record and resets it to `discovered`.
- It immediately requests `discovered → queued`, but `core/execution_queue/models.py::TRANSITIONS` allows only `discovered → qualified` or `rejected`.
- The exception handler then tries another transition to `failed`, which is also not allowed from `discovered`.

**Required repair:** never overwrite an existing queue item; validate its current state; use the canonical legal transition sequence; make duplicate scheduler runs idempotent.

### B2 — CoderAutopilot calls the CoderAgent with a nonexistent argument contract

File: `core/cycles/tasks_coder_autopilot.py::_solve_one`

The call uses `agent.solve_issue(issue_url=..., platform=...)`. The actual method in `core/autonomy/coder_agent.py` accepts `issue_data`, optional `repo_url` and `platform`. The scheduled path therefore cannot invoke the method successfully.

**Required repair:** build a validated issue payload and repository URL from the canonical opportunity data; return an explicit blocker when repository metadata cannot be extracted. Do not guess repository URLs from unrelated platform pages.

### B3 — CoderAgent analyzes a different path from the path it cloned

Files: `core/autonomy/coder_agent.py::solve_issue`, `core/autonomy/repo_analyzer.py::clone_repo`

- `RepoAnalyzer.clone_repo` returns the actual clone path in `clone_result.data["path"]` (under its configured work directory).
- `CoderAgent.solve_issue` ignores that returned path and instead analyzes `self.work_dir / "repo_<issue_id>"`.
- Those paths are not the same by default. The subsequent analysis/test flow can therefore fail or inspect a stale/nonexistent workspace.

**Required repair:** use the returned clone path as the sole source of truth; allocate a unique per-task workspace to prevent same-repository tasks from deleting or reusing each other's clones; preserve the workspace until delivery review is complete.

### B4 — The first test run does not validate the generated patch

File: `core/autonomy/coder_agent.py::solve_issue`

The initial `GenerationPlan` is generated, but `_apply_plan_changes` is not called before the first test run. The patch is applied only in the retry path after a failed test run. Thus a passing first test run can describe the original repository, not the proposed changes.

**Required repair:** apply the exact generated patch to the isolated workspace before tests; persist a before/after diff; run tests against that modified workspace; reject path traversal and changes outside the allowed repository root.

### B5 — External PR creation happens before a human approval boundary

File: `core/autonomy/coder_agent.py::solve_issue`

After the test stage, the method calls `create_pr_from_plan` directly. The autopilot's `WAITING_HUMAN` state is reached only after the CoderAgent returns, so that state does not gate PR creation.

**Required repair:** split local preparation from external publication. The autonomous stage may generate a patch, run allowed validation, create a review package and wait. A separate owner-authorized action must create/publish the PR or submit work. Queue states and UI labels must describe what actually happened.

### B6 — Sandbox readiness is not demonstrated for untrusted repositories

File: `core/security/sandbox.py`

- Docker execution mounts the host workspace read-only at `/work`, which is appropriate for inspection but not sufficient as-is for normal build/test tools that need writable caches and artifacts.
- When Docker is unavailable, the fallback starts a host subprocess and applies a CPU-time limit. It does not provide filesystem or network isolation.
- The current CoderAgent/RepoAnalyzer test and dependency-install calls do not route through the Sandbox abstraction.

**Required repair:** never run dependency installation or repository-supplied test/build commands on the host for an untrusted project. Add a writable ephemeral in-container copy/overlay, explicit CPU/memory/time limits and a controlled dependency/network policy. If a verified container runtime is unavailable, fail closed and preserve the task as `BLOCKED`/manual review instead of silently using the host fallback.

### B7 — Two CoderAgent implementations exist

Files: `core/autonomy/coder_agent.py` and `cores/autonomy/coder_agent.py`

The duplication audit identifies `core/autonomy` as the dominant import tree for the autonomy domain, while current callers also import the `cores` copy. The copies are not identical. Do not patch one copy and leave callers on the other.

**Required repair:** map every caller, choose `core/autonomy` as the domain SSOT in line with the duplication audit, and convert the `cores` path to a compatibility re-export only after verifying the imports and tests. No destructive deletion in this slice.

## 4. Safe implementation order

1. **Unify the call path:** make the scheduled/interactive entry point use one CoderAgent implementation; map WorkBank IDs to their LiveStore opportunity records and validate repository/issue URLs.
2. **Repair local workspace handling:** use the clone result path, isolate each task, preserve original metadata, and keep all writes inside that workspace.
3. **Apply and inspect changes:** apply GenerationPlan changes before validation; enforce repository-root boundaries; retain a patch, changed-file list and provenance.
4. **Close the sandbox gap:** route dependency installation and tests through a verified container environment with a writable ephemeral copy. Disable host execution fallback for external code.
5. **Add review gates:** run deterministic tests, lint/security checks and an independent code review. Produce a local delivery package first.
6. **Require explicit owner approval:** only then create a public PR, claim/submit a bounty or perform another external commitment.
7. **Record the actual result:** distinguish generated, tested, reviewed, PR-published, accepted and paid. Only evidence of payment may advance revenue to paid/verified.

## 5. Acceptance criteria for the first end-to-end slice

- A real public GitHub issue with a separately evidenced reward can be selected from WorkBank.
- Re-running the scheduler does not duplicate or reset the queue record.
- The task resolves to the exact repository and issue; a missing repository URL blocks safely.
- The repository is cloned to a unique per-task workspace and survives restart/review.
- The generated patch is applied locally and the diff contains only paths inside the workspace.
- Tests execute against the changed copy inside a verified sandbox; no host fallback is permitted.
- Test output, generated patch, changed files, model/provider used and timestamps are persisted as evidence.
- The result is displayed as `READY_FOR_OWNER` / `WAITING_HUMAN`, not `SUBMITTED`.
- No PR, bounty claim or platform submission occurs until an explicit owner approval is recorded.
- No advertised or reported reward is counted as revenue. Revenue becomes verified only after payment evidence is recorded.

## 6. Scope guard

Do not add another WorkBank, scheduler, agent framework, opportunity state machine or source registry for this work. Reuse the existing canonical components. Keep this first slice narrow: public software issues with a verifiable repository and an explicitly reported reward. Expand platform coverage only after one complete path works and can be demonstrated with evidence.

**Current conclusion:** discovery, guided earning, repository preparation and parts of code generation already exist. The missing product is not another dashboard or another list of sources. It is one safe, repeatable, reviewable engineering cycle from a selected open-source reward task to an owner-approved deliverable.
