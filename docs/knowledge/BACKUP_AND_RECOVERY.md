# Knowledge Bridge — Backup and Recovery

> Backup and recovery for the OWNEX Knowledge Bridge: local zip snapshots of
> the Obsidian vault, the index health log, and restore procedures.

## What is backed up

| What | How | Where |
|---|---|---|
| Vault content (markdown + attachments) | Zip snapshot | `data/knowledge/backups/vault_YYYY-mm-dd_HHMMSS.zip` |
| Index / config | Rebuildable from the vault (derived cache) | `data/knowledge/` (SQLite) |
| Health history | JSONL appended on each daily sync | `data/knowledge/knowledge_health.jsonl` |

The index is a **derived cache**: if it is lost or corrupted, re-running a
full reindex (`POST /api/knowledge/scan?full=true`) rebuilds it from the
vault. Backing up the vault itself is the critical part.

## Creating a snapshot

Authorized API call (the UI does this via Knowledge Vault → "Crear
snapshot"):

```bash
curl -X POST "http://localhost:8000/api/knowledge/snapshots?authorized=true"
```

Without `authorized=true` the endpoint returns 403
`{"authorization_required": true}` — snapshots never happen without explicit
user action.

## Retention

Snapshots are rotated: the `SnapshotManager` keeps the **10 most recent**
zips and deletes older ones automatically. Snapshots older than that must be
copied elsewhere to be preserved.

## Restore

1. Locate the desired zip in `data/knowledge/backups/`.
2. Extract it over the vault folder (replacing files):

   ```bash
   unzip -o data/knowledge/backups/vault_2026-08-13_063000.zip -d /home/usuario/Obsidian/Vault
   ```

3. Reindex the vault so the index reflects the restored content:
   `POST /api/knowledge/scan?full=true`.

> There is no automated restore endpoint: restoring is a human decision and
> must happen outside the system (the vault is the user's own repository).

## Health history

Every daily sync appends a snapshot with scan results, health metrics, git
state and security status to `knowledge_health.jsonl`:

```bash
curl "http://localhost:8000/api/knowledge/history?limit=7"
```

Use it to answer "what changed in the vault since last week" and to detect
degradation (broken links growing, secrets appearing).

## Related

- General OWNEX data backup: `docs/BACKUP_AND_RECOVERY.md`
  (`python run.py --backup`)
- Git in the vault is an additional layer: `POST /api/knowledge/git/commit`
  (authorized) commits vault changes to the vault's own git history.
