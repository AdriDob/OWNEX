# RISK MAP — OWNEX (2026-09-30)

## CRITICAL

### C-1 · Auth Bypass: 149 Mutating Endpoints Without Credentials
**Location**: `api/middleware/auth_middleware.py:49-50`
```python
if not path.startswith("/api/"):
    return await call_next(request)
```
**Impact**: 29 root-mounted routers (282 endpoints, 148 mutating) bypass auth entirely.
- Worst: `/direct-work` (40 mutating), `/finance` (14), `/life-management` (10), `/devin` (8)
- `POST /version-backup/rollback` → `shutil.rmtree()` on user data-dir
- `POST /direct-work/workbank/purge-fixtures` — unauthenticated deletion
- `POST /remote/session`, `/remote/chat`, `/remote/approve` — unauthenticated

**Mitigation today**: Binds `127.0.0.1` only. **If rebuilt with `--host 0.0.0.0`, fully exposed.**

---

### C-2 · Economic History Not Persisted — `RevenueTracker` Memory-Only
**Location**: `cores/revenue_tracker/revenue_tracker.py:355-365`
```python
class RevenueTracker:
    def __init__(self):
        self.opportunities = {}
        self.transactions = []
        self.metrics = {}
```
No file write, no DB table. `database/models.py` has **zero** financial tables (21 tables, none financial).

**Recovery sources**: Only `workbank.json` + `submission_queue.json` at boot. All direct tracker calls (`record_bounty_paid()`, `add_payment_method()`, `PaymentTransaction`) **lost on restart**.

**Migration requirement**: Must copy these JSON files:
```
$OWNEX_DATA_DIR/workbank.json
$OWNEX_DATA_DIR/submissions/submission_queue.json
$OWNEX_DATA_DIR/bounty_tracker.json
$OWNEX_DATA_DIR/payment_pipeline.json
$OWNEX_DATA_DIR/fiverr_assets.json · fiverr_funnel.json
$OWNEX_DATA_DIR/payout_tax_records.json · state.json
$OWNEX_DATA_DIR/economic_feedback/snapshot.json
$OWNEX_DATA_DIR/dev_bounty_autopilot/{config,proposals}.json
$OWNEX_DATA_DIR/revenue/availability.json
$OWNEX_DATA_DIR/financial_intelligence/state.json
```

---

### C-3 · Ungated External Bounty Claims (No Human Gate)
**Live claim paths** (only token required, no approval):
| File:Line | Effect |
|-----------|--------|
| `cores/opportunity/executors/opire_executor.py:47-56` | `POST /bounties/{id}/claim` on Opire |
| `cores/opportunity/executors/issuehunt_executor.py:39-66` | `POST .../claim` on IssueHunt |
| `cores/autonomy/workflow_engine.py:284` | Generic dispatch; `_plan_oss_bounty` emits `claim_issue` |

**By contrast, gated correctly**: `algora_executor.py:151-166`, `pr_builder.py:41-53` — `require_approval=True`, `consume_approval()`.

---

### C-4 · Vault Key Silent Regeneration → Permanent Credential Loss
**Location**: `cores/vault_crypto.py:35-50`
```python
def get_vault_key():
    if os.path.exists(key_path):
        try:
            _VAULT_KEY = f.read().strip()
            if len(_VAULT_KEY) == 32:
                return _VAULT_KEY
        except Exception:
            logger.warning("Failed to read vault key, generating new one")  # line 45
    _VAULT_KEY = secrets.token_bytes(32)
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(_VAULT_KEY)  # OVERWRITES
```

If key file missing/truncated/unreadable → **new random key overwrites it**. All credentials in `~/.orion/identity_vault.json` permanently undecryptable. Only signal: `logger.warning` — but `ownex.*` loggers **not wired to file handler** (only `CATEYE` logger configured).

**Migration requirement**: `~/.orion/identity_vault.key` (32 bytes, chmod 600) **MUST** travel with `identity_vault.json`, or all credentials destroyed.

---

## HIGH

### H-1 · Test Suite Contaminates Real Data Dir
`tests/conftest.py:14` isolates only SQL (`DATABASE_URL`). **No `OWNEX_DATA_DIR` or `HOME` override**. Vault uses `HOME` → `~/.orion`. **22/356** tests set `OWNEX_DATA_DIR`; **3** monkeypatch `HOME`.

**Historical**: `.ai/DECISIONS.md` (2026-08-16) records `test_migrate.py` overwrote real `~/.orion/config.sh`, `license.json`, `identity_vault.json`, `identity_vault.key`, `database/orion.db`, `~/.config/ownex/trading.json`.

---

### H-2 · `content_factory` Hardcoded Output Path
`cores/content_factory/service.py:55,63`
```python
output_dir: str = "/home/adriel/projects/Rastro/data/mpt/output"
self.output_dir = Path(output_dir)
self.output_dir.mkdir(parents=True, exist_ok=True)
```
Runs in `__init__`. Instantiating on another machine creates `/home/adriel/projects/Rastro/data/mpt/output` or fails.

Also: `api/routers/merlin.py:267` (`cwd="/home/adriel/projects/Rastro"`), `scripts/brand/puppeteer-config.json:2` (machine-specific Chrome path).

---

### H-3 · License HWID-Bound — Rebuild on New Hardware Invalidates It
`cores/license/hardware.py:40-73` derives from `/etc/machine-id`, `dbus machine-id`, Windows `MachineGuid`. New machine ⇒ new HWID ⇒ invalid license. Escape: `CATEYE_PORTABLE=1` (`.ai/DECISIONS.md` 2026-08-16). **Must plan into migration**.

---

### H-4 · Machine Fingerprints Logged at INFO
`cores/license/hardware.py:43,64,71` — raw hardware IDs at INFO level, persist to logs/bug reports.

---

### H-5 · `FreeDiskSpaceAction` — Early Return Inside `os.walk` + CWD-Relative
`cores/self_repair/engine.py:479-497`
```python
for root, dirs, _ in os.walk("."):
    ...
    return True, f"Freed {freed_mb:.1f} MB"  # INSIDE loop!
```
Cleans **one** directory, reports success. CWD-relative (`os.walk(".")`, `Path("logs")`).

---

## HIGH (Continued)

### H-6 · Sidecar Binary Stale (26 Commits Behind)
- Built: 2026-09-05
- Backend commits since: 26
- `auth.py` unchanged since 2026-08-14 → auth works, but other fixes missing
- **Must rebuild** before release

---

### H-7 · License HWID-Bound — New Machine = Invalid License
`cores/license/hardware.py:40-73`. Escape: `CATEYE_PORTABLE=1`. **Must plan into migration**.

---

### H-7 (cont) · Machine Fingerprints at INFO Level
`cores/license/hardware.py:43,64,71` log raw hardware IDs.

---

## MEDIUM

### M-1 · Unauthenticated `clear_all()` on Identity Vault
`cores/identity_vault.py:276-279` — wipes all credentials, no backup, no dry-run. Reachable via `/devin` root-mounted.

### M-2 · `full_reindex` Destroys Knowledge Index Before Rebuild
`cores/knowledge/index.py:249-253` — `DELETE FROM` then `scan_incremental()`. If scan fails, index gone.

### M-3 · `rollback_to_version` Overwrites Data-Dir Non-Atomically
`cores/version_backup/backup_system.py:483-497` — `rmtree` + `copytree` per file, no staging. Crash mid-restore = corrupted state.

### M-4 · `GitHubCommenter.post_issue_comment` — No Gate (Currently Dead)
`cores/autonomy/github_commenter.py:53-80` — posts to GitHub Issues API, only `GITHUB_TOKEN` guard. No callers now, but one import away from live.

### M-5 · `assisted_mode.auto_submit` Returns Success Doing Nothing
`cores/opportunity/executors/assisted_mode.py:284-298`
```python
return {"success": True, "status": "auto_submitted", ...}
```
Returns success for work never submitted. Sets `requires_manual_action: True` but status is a lie.

### M-6 · QA "Screenshot" Is Fabricated Stub
`cores/cycles/qa.py:707-734`
```python
def _take_screenshot(self, url, output_path, timeout=15) -> str:
    stub = {"url": url, "timestamp": ..., "simulated": True}
    with open(output_path + ".json", "w") as f:
        json.dump(stub, f)
    return output_path  # Returns path to non-existent file
```

### M-7 · `RebuildIndexAction` Reports Success for No-Op
`cores/self_repair/engine.py:525` — `return True, "Index rebuild triggered (placeholder)"`.

### M-8 · `osint_api` Logs API Key on "Not Configured"
`cores/recon/osint_api.py:57` — logs `self.api_key` when not configured. Latent leak.

### M-9 · `.env` World-Readable (644)
Mode `-rw-r--r--`. Gitignored, but readable by all local users. Vault key is 600.

### M-10 · Partial Push Token in Logs
`cores/notifications/fcm.py:74` — `logger.debug("FCM send failed: %s", token[:16], ...)`

---

## LOW

### L-1 · CORS `allow_origins=["*"]` When Desktop Flag Absent
`api/main.py:459-463` — `_allow_all = not get_config().desktop`. Paired with `allow_credentials=not _allow_all`, so degrades not opens.

### L-2 · FCM / `IdentityVault.clear_all` Reachable from `/devin` (8 Mutating, Unauth)
`api/routers/devin.py:36,60,81,102,123,144,165,186`

### L-3 · Hardcoded Localhost Ports (Not Configurable in 3 Places)
`:8082`×13, `:8000`×9, `:8081`×4, `:8080`×4, `:20128`×8, `:11434`×8.

### L-4 · TODO/FIXME/HACK/XXX: 27 in `cores/` + `api/`
Significant: `assisted_mode` auto-submit, CVE matchers incomplete, EV scoring unused, credential auto-refresh placeholder, Polymarket resolution timing unknown, `time_to_payment_days=None`, test generation not implemented.

---

## CLEAN / VERIFIED (No Risk)

### Version Drift: NONE
All 10 surfaces agree on `7.7.7`:
`.VERSION.txt` · `VERSION.txt` · `VERSION` · `pyproject.toml` · `package.json` · `frontend/package.json` · `src-tauri/Cargo.toml` · `src-tauri/tauri.conf.json` · `cores/__init__.py` · `cores/version.py` · `apps/hermes/__init__.py` · `android/app/build.gradle` (`versionCode 777`, `versionName "7.7.7"`).

### Secrets Hygiene
- `.env` gitignored (`.gitignore:10`), only `.env.example` tracked
- No `*.pem`/`*.key`/keystore in `git ls-files`
- `tests/test_no_secrets_committed.py` guards JWTs + asserts `backups/` ignored
- Vault: AES-256-GCM, random 32-byte key, `chmod 600` enforced
- Legacy `/etc/machine-id` keys auto-migrated

### Economic Modules: Zero Destructive Code
Grep across `cores/revenue*/`, `cores/economic*/`, `cores/first_money/`, `cores/direct_work_engine/workbank.py` → **1 hit**: `cores/revenue_multiplier/bugbounty_hunter.py:28` `self._findings.clear()` (in-memory cache). **Nothing deletes persisted money history.**

### Database Safety
`database/db.py`: `chmod`-adjacent dir creation, WAL checkpoint on exit. `tests/conftest.py:18` raises hard `RuntimeError` if `catseye.db` used in tests.

---

## DOC CLAIMS FALSE / UNVERIFIABLE

| Claim | Location | Verdict |
|-------|----------|---------|
| Badge `tests-4534+-passed` vs table `3,228+` | `README.md:17`, `:232` | **FALSE** — self-contradictory. Actual: **5,843** `def test_` |
| `Scheduler - 72 jobs` | `README.md:188` | **UNVERIFIED** — measured 66 unique `job_id=` |
| `1641 routes` | `.ai/CURRENT_STATE.md:1466` | **STALE** — `.ai/` says 1846, `api/main.py` has 208 `include_router` |
| `138 curated sources` | `README.md:325` | **UNVERIFIED** — `.ai/` has 121, 124, 135, 138, 139 |
| `9.5/10 health` badge | `README.md:22` | **UNVERIFIABLE** — self-assessed score as badge |
| `Vitest 191 tests` | `README.md:561,581` | Plausible (matches `.ai/CURRENT_STATE.md`) |
| `719 targets` / `9806 endpoints` / `0 findings` | `.ai/DECISIONS.md:552,615` | Point-in-time, DB-dependent |

---

## BOTTOM LINE FOR REBUILD

**Safe to migrate with THREE hard conditions:**

1. **`~/.orion/identity_vault.key` is the single most important file** — lose it, all credentials gone (C-4). Only a `logger.warning` (not even wired to file handler).

2. **No SQL table for money** — all economic history is JSON in data-dir, `RevenueTracker` memory-only (C-2). Migration = **file copy of `OWNEX_DATA_DIR`**, not DB dump.

3. **Do not bind `0.0.0.0` until C-1 fixed** — 149 mutating endpoints unauthenticated. Only `127.0.0.1` bind protects today.

**Additionally**: Plan HWID rebind (H-3), fix `content_factory` hardcoded path (H-2) before first run on new hardware.