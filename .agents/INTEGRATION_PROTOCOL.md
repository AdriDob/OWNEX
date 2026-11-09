# OWNEX Integration Protocol — Multi-Agent Coordination (v1.0)

How changes get from an agent's work into `main` safely.

## 1. Pre-flight (mandatory before coding)

- Task, objective, commit base, branch/worktree.
- Modules involved; files authorized vs read-only; shared files.
- Related agents (check `.agents/AGENT_REGISTRY.md`).
- Existing implementations of the same responsibility (search first — `core/` AND `cores/`).
- Duplication risk; dependencies; planned tests; acceptance criteria.

## 2. During work

- Small atomic commits, clear messages.
- No contract changes (API schemas, DB models, event names, shared types) without listing consumers and updating them.
- Never delete code another agent may use without verifying consumers (`graft`/grep).
- Never mark MOCK as functional. States: IMPLEMENTED / VERIFIED / PARTIAL / BLOCKED / NOT_IMPLEMENTED / MOCK / UNKNOWN.

## 3. Completion report (mandatory)

Objective, files created/modified/deleted (+why), reused implementations, duplications found, decisions, contracts affected, migrations, tests run + results (PASS/FAIL/BLOCKED/NOT_TESTED/REGRESSION), risks, debt added, commit, pending items, integration recommendation.

## 4. Integration (coordinator)

- Review diffs of ALL commits, not just HEAD.
- Check for duplicate implementations of the same responsibility; if two agents built the same thing, compare technically and keep the superior one (migrate useful parts).
- Run global validation: ruff + scoped pytest + biome + vue-tsc on touched files.
- Update canonical docs (`.ai/CURRENT_STATE.md`, this board, registry).

## 5. Prohibitions

- `git reset --hard`, `git clean -fd`, force push, history rewrite, deleting others' branches.
- Committing unrelated/parallel-session changes.
- Secrets in code/logs/commits.
- Financial actions (trade/withdraw/transfer/sign/submit) without explicit human approval.
- Claiming "connected/synced" without a real provider response.
