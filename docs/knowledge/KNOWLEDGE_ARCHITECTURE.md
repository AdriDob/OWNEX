# Knowledge Bridge — Architecture

> OWNEX Knowledge Bridge: the user's Obsidian vault as the single source of truth
> for personal knowledge. OWNEX reads, indexes and searches the vault locally —
> it never duplicates reality.

## Principles

1. **Markdown is the source of truth.** The vault files are the reality. The
   index is a derived cache that can always be rebuilt from the vault.
2. **100% local.** Index (SQLite + FTS5), embeddings (local hashing), backups
   (zip snapshots) and git operations all run on the host. No cloud.
3. **Writes require explicit authorization.** Every mutation endpoint
   (git commit, snapshot create, note overwrite) rejects with HTTP 403
   `{"authorization_required": True}` unless the caller passes
   `authorized=true`.

## Components (`cores/knowledge/`)

| Module | Responsibility |
|---|---|
| `parser.py` / `parsers.py` | Markdown parsing: frontmatter, wikilinks, embeds, tags, headings, checkboxes |
| `index.py` | `VaultManager` (connect/verify/set/clear) + `KnowledgeIndex` (SQLite FTS5, incremental scan, backlinks, broken links, duplicates, stats) + config persistence |
| `search.py` | `KnowledgeSearcher`: unified hybrid search (exact / title / path / alias / tag / link / FTS / semantic) + `build_context()` for AI prompts + embeddings (`ensure_embeddings`) |
| `gitops.py` | `GitOps` (status/diff/commit/push/pull), `SecretScanner` (API keys/tokens → blocks unsafe pushes), `SnapshotManager` (zip backups, keep 10), `SafeWriter` (writes require authorization, pre-write snapshot) |
| `tasks.py` | `run_knowledge_sync()` (daily job: scan + embeddings + health snapshot) + `get_knowledge_snapshot_history()` |
| `graph.py`, `store.py`, `deduplicators.py`, `enrichers.py`, `normalizers.py`, `trust.py`, `pipeline.py`, `abstracts.py`, `models.py` | Supporting layers (note model, enrichment, dedup, trust scoring, pipeline orchestration) |
| `__init__.py` | Public API: `VaultManager`, `ensure_initialized()`, `vault_health()`, `load_config()` |

## Data flow

```
Obsidian vault (markdown)
        │  connect (POST /api/knowledge/connect)
        ▼
KnowledgeIndex (SQLite + FTS5)  ── incremental scan / full reindex
        │
        ├──► hybrid search (GET /api/knowledge/search)
        ├──► AI context    (GET /api/knowledge/context)
        ├──► health        (GET /api/knowledge/health)
        ├──► git/security  (GitOps / SecretScanner)
        └──► snapshots     (SnapshotManager, keep 10)
```

## Storage

| Path | Purpose |
|---|---|
| `data/knowledge/` | Global index DB + config for the knowledge layer (DATA_DIR) |
| `data/knowledge/knowledge_health.jsonl` | Health snapshots appended by each daily sync |
| `data/knowledge/backups/` | Zip snapshots `vault_YYYY-mm-dd_HHMMSS.zip` (rotated, keep 10) |

## Scheduler

- `knowledge_sync_daily` — cron `30 6 * * *` — handler
  `cores.knowledge.tasks:run_knowledge_sync`: incremental scan, embeddings
  (≤150 per run), health snapshot. Registered in `get_all_jobs()` (10 cycles,
  44 jobs total).

## API surface

Router `api/routers/knowledge_bridge.py` — prefix `/api/knowledge` (17
endpoints). GETs are read-only and always allowed; mutations require
authorization (see `SECURITY.md`). See `.ai/COMPLETED_FEATURES.json` →
`FASE_34` for the verification record.
