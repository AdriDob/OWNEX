# Security Baseline — July 2026

## Credential Storage

| Item | Path | Perms | Status |
|------|------|-------|--------|
| Hermes .env | `~/.hermes/.env` | 600 ✅ | Fixed (was 644) |
| Hermes auth.json | `~/.hermes/auth.json` | 600 ✅ | Correct |
| Hermes config.yaml | `~/.hermes/config.yaml` | 600 ✅ | Fixed (was 644) |
| Identity Vault | `~/.orion/identity_vault.*` | 600 ✅ | Correct |
| Audit Log | `~/.orion/audit.jsonl` | 600 ✅ | Correct |

## Hardcoded Secrets in Source

Scanned: Python files for patterns `api_key=`, `secret=`, `token=`, long alphanumeric strings.

**Result**: No hardcoded keys found in source code. ✅

## Orphaned Test Databases

- **Count**: 1183 files
- **Size**: ~79 MB
- **Location**: `~/.orion/database/knowledge_graph_kg_test_*.db`
- **Risk**: Low (no credentials, just test data)
- **Recommendation**: Clean up with `rm ~/.orion/database/knowledge_graph_kg_test_*.db`

## Audit Logging

- **File**: `~/.orion/audit.jsonl`
- **Size**: 216 KB, 1488 events
- **Permissions**: 600 ✅
- **Rotation**: 10MB limit (3 backups)

## Recommendations

1. ✅ `.env` and `config.yaml` permissions fixed to 600
2. ⚠️ Clean up 1183 orphaned test databases (79MB)
3. ✅ No hardcoded credentials detected
4. ✅ All vault/audit files have correct permissions
