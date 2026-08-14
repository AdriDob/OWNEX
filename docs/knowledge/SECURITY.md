# Knowledge Bridge — Security

> Security model of the OWNEX Knowledge Bridge: authorization for writes,
> secret scanning, and the local-first guarantees.

## Authorization model

Every **mutation** endpoint of `/api/knowledge` requires an explicit
`authorized=true` flag. Without it, the API returns HTTP 403:

```json
{ "authorization_required": true }
```

| Endpoint | Requires authorization |
|---|---|
| `GET /api/knowledge/*` (status, search, note, context, health, history, git status, security scan, snapshots list) | No — read-only |
| `POST /api/knowledge/git/commit` | Yes — shows pending diff on 403 |
| `POST /api/knowledge/snapshots` (create) | Yes |
| `POST /api/knowledge/connect`, `scan`, `initialize`, `sync`, `disconnect` | No (the user is already authenticated via session; these operate on the user's own vault) |

Writes through `SafeWriter` (note overwrite) also require `authorized=True`
and return 403 otherwise — the system never modifies vault content
unprompted.

## Secret scanning

`GET /api/knowledge/security/scan` scans every file in the vault for leaked
credentials (API keys, tokens, private keys). The scan result lists each
finding with file, line and kind:

```json
{
  "clean": false,
  "findings": [{ "file": "notes/config.md", "kind": "api_key", "line": 3, "snippet": "sk-..." }],
  "scanned": 12
}
```

If the vault is a git repository, a scan with findings should block pushing:
fix or remove the secrets before `git commit`/`push` (the GitOps layer
reports dirty state; the human decides).

## Local-first guarantees

- All data lives on the host: index SQLite, embeddings, snapshots and the
  vault itself. No telemetry, no cloud sync.
- The vault is the user's own folder — OWNEX only reads it for indexing and
  only writes with explicit authorization.
- The health log (`knowledge_health.jsonl`) records scan results over time
  so secret leakage or index degradation is visible retroactively.

## Threat model notes

- **Local attacker with host access**: can read the vault and the index
  (same trust level as the rest of OWNEX data). IdentityVault/OS permissions
  apply as for the rest of the system.
- **CSRF / forged requests**: mutations require the authorized flag (a
  user-decision, not a CSRF token), which prevents any automated cross-site
  request from committing or overwriting vault content. The standard CSRF
  middleware also applies to the whole API.
- **Malicious vault content**: notes are parsed and stored textually; the
  index only stores strings. No code execution is performed on vault content.

## Related

- General security model: `docs/SECURITY_MODEL.md`
- Root `SECURITY.md` (vulnerability reporting)
