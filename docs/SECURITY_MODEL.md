# Security Model

> Version 4.1.0 — July 2026

This document describes the security architecture of the ORION Platform / CATEYE system. All cryptography, authentication, authorization, and data protection mechanisms are documented here with references to the actual source code.

## 1. Encryption

### 1.1 AES-256-GCM — Vault Crypto

The foundation of all data-at-rest encryption is `cores/vault_crypto.py`. It provides:

- **Algorithm**: AES-256-GCM (Authenticated Encryption with Associated Data)
- **Nonce**: 12 random bytes per encryption operation
- **Key**: 32 random bytes generated via `secrets.token_bytes(32)`
- **Key storage**: `~/.orion/identity_vault.key` with permissions `chmod 600`
- **Encoding**: nonce + ciphertext, base64-encoded as ASCII

```python
# cores/vault_crypto.py:54-61
def encrypt(plaintext: str) -> str:
    key = get_vault_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(_AES_NONCE_BYTES)  # 12 bytes
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")
```

This is used by:
- `IdentityVault` — encrypts provider credentials (tokens, passwords)
- `TokenService` — encrypts auth tokens on disk
- `SessionStore` — encrypts session data on disk

### 1.2 Ed25519 — License Signing

License validation uses Ed25519 asymmetric signatures via `cores/license/validator.py`:

- **Algorithm**: Ed25519 (Curve25519, 32-byte public key, 64-byte signatures)
- **Public key**: Embedded in the binary (safe to distribute)
- **Private key**: Held by the license server only
- **License format**: 25-character alphanumeric + signature stored in `license.json`
- **Migration**: Replaced HMAC-SHA256 (CVE-1) — old HMAC licenses are not compatible

## 2. Authentication

### 2.1 TokenService (`cores/auth/token_service.py`)

- **Storage**: Tokens encrypted on disk using AES-256-GCM via `vault_crypto`
- **Path**: `~/.local/share/CATEYE/tokens/secure_tokens.json`
- **Device binding**: Each token is bound to a `device_id`
- **Expiry**: TTL configurable per token (default 86400s / 24h)
- **Revocation**: Individual token revocation with automatic cleanup of expired tokens

### 2.2 SessionStore (`cores/auth/session.py`)

- **Storage**: Sessions encrypted on disk using AES-256-GCM via `vault_crypto`
- **Path**: `~/.local/share/CATEYE/sessions/sessions.json`
- **Device binding**: Sessions are bound to a `device_id`
- **Refresh tokens**: Each session has a refresh token for seamless re-authentication
- **Device registration**: Each device registers metadata (name, type) on first use

### 2.3 TokenAuth (`cores/auth/auth.py`)

- **Token secret**: Persisted to `.auth_secret` file (CVE-12 fix)
- **Survival**: Tokens survive server restarts (previously tokens were invalidated on restart)

## 3. CSRF Protection

The `api/middleware/csrf_middleware.py` implements the **double-submit cookie** pattern:

1. **GET requests**: A cryptographically random 32-byte token (`secrets.token_hex(32)`) is set as an `httponly` cookie named `csrf-token`
2. **State-changing requests** (POST, PUT, DELETE, PATCH): The client must send the same token in the `X-CSRF-Token` header
3. **Verification**: Server compares cookie token vs header token using `hmac.compare_digest()` to prevent timing attacks
4. **Exempt paths**: `/api/health`, `/api/license/activate`, `/api/auth/login`, `/api/auth/register`, `/api/auth/desktop-session`

```python
# api/middleware/csrf_middleware.py:70-79
cookie_token = request.cookies.get(COOKIE_NAME, "")
header_token = request.headers.get(HEADER_NAME, "")
if not hmac.compare_digest(cookie_token, header_token):
    return Response("CSRF validation failed", status_code=403)
```

CSRF is **always active** unless explicitly disabled via `CATEYE_CSRF_DISABLED=1` environment variable (CVE-4 fix improved in v3.0.0).

## 4. OAuth2 Security

### 4.1 Gmail OAuth (`cores/authhub/gmail.py`)

- **State token**: Cryptographically random state token (`secrets.token_urlsafe(32)`) generated in `authorize_url()`, stored in memory during the OAuth flow
- **Verification**: State token compared in `exchange_code()` using constant-time comparison to prevent CSRF on the OAuth callback
- **Scope**: Restricted to `https://www.googleapis.com/auth/gmail.readonly` — read-only email access
- **Token storage**: Access and refresh tokens encrypted via IdentityVault (AES-256-GCM) after exchange
- **Fix for CVE-5**: OAuth2 flow was missing `state` parameter — now mandatory and verified

### 4.2 API Key Header Security

All API keys (Google Gemini, OpenRouter) are transmitted via HTTP headers, never in URL query parameters:

- `X-Goog-Api-Key` header for Google Gemini API (`cores/ai/orion_agent.py`, `cores/ai/provider.py`)
- Fixed CVEs 9 and 10 where keys were previously sent as URL query parameters (exposed in server logs, referrer headers, and browser history)

### 4.3 Auth Middleware

`api/middleware/auth_middleware.py` provides Bearer JWT authentication:

- **Token format**: JWT with `sub` (user ID), `type` (session/refresh), `exp` (expiry)
- **Secret**: Persisted to `.auth_secret` file for restart survival (CVE-12)
- **Optional auth**: Some routers (health, public endpoints) bypass auth
- **Desktop mode**: In desktop mode (`CATEYE_DESKTOP=1`), auth can be relaxed for local-only operation

## 5. Secrets Management

### 5.1 IdentityVault (`cores/identity_vault.py`)

- **Encryption**: AES-256-GCM via `vault_crypto`
- **Key**: Random 32-byte key (`secrets.token_bytes(32)`), NOT derived from machine-id
- **File permissions**: `chmod 600` on both the key file and the vault JSON
- **Migration**: Automatic migration from old machine-id-derived key on first access. The migration reads old credentials using the machine-id key, re-encrypts them with the new file key, and sets `_key_version` to `"file"` in the vault JSON.
- **Supported providers**: HackerOne, Bugcrowd, Huntr, Immunefi, Intigriti, YesWeHack, GitHub, Synack
- **Session health**: Each stored credential tracks session state (`connected`, `disconnected`), last check timestamp, and health status (`healthy`, `unknown`, `error`)
- **Auto-detection**: `check_session_health()` determines if a session is still valid based on state, time since last check (max 24h), and credential presence

The migration code in `_maybe_migrate_vault()`:

```python
# cores/identity_vault.py:82-108
old_key = _get_old_machine_id_key()  # SHA-256 of /etc/machine-id
get_vault_key()  # ensures new file key exists
for provider, entry in data.items():
    encrypted = entry.get("encrypted_token", "")
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    plain = AESGCM(old_key).decrypt(nonce, ciphertext, None)
    entry["encrypted_token"] = _encrypt(plain)  # re-encrypt with file key
data["_key_version"] = "file"
json.dump(data, vault_path, indent=2)
os.chmod(vault_path, 0o600)
```

### 5.2 SecretsManager (`core/secrets/manager.py`)

- **Priority**: IdentityVault → Environment variable → Default value
- **Caching**: In-memory cache with per-key access (cleared on restart)
- **Scope**: API keys for exchanges, AI providers, scanners, wallets
- **API endpoints**: REST API at `/api/core/secrets` provides GET (list keys), GET `/{key}` (get value), PUT `/{key}` (store), DELETE `/{key}` (remove)
- **Vault provider format**: Secrets are stored as `_secret:{key}` providers in IdentityVault, distinguished from regular bug bounty provider credentials

### 5.3 Frontend Secrets Handling (`frontend/src/stores/settings.ts`)

- **Storage**: sessionStorage (cleared when tab closes)
- **Encryption**: AES-GCM via Web Crypto API
- **Mitigation**: Mitigates XSS exfiltration compared to localStorage (CVE-style fix, documented as temporary)
- **Scope**: openai, gemini, wallet, bank API keys
- **Planned improvement**: Move all secrets to backend IdentityVault with dedicated API endpoints

## 5.4 Exchange API Authentication (ATLAS)

Exchange connectors use HMAC-based authentication for API access:

- **Coinbase** (`apps/atlas/connectors/coinbase/connector.py`): `CB-ACCESS-SIGN` header using HMAC-SHA256 with the API secret. Timestamp + method + path + body are signed.
- **Kraken** (`apps/atlas/connectors/kraken/connector.py`): API signature using HMAC-SHA512 with the private key. Nonce-based replay protection.
- **No key storage**: API keys are retrieved from SecretsManager (IdentityVault-backed) at runtime, never stored in code or config files.

## 5.5 Test Security

- **Dev keys**: Ed25519 test keys are generated at runtime in `tests/conftest.py` using `cryptography.hazmat`, not hardcoded (fixed in v3.0.0 hardening)
- **Isolation**: Tests use an in-memory SQLite database, never touching production data
- **Rate limiting bypass**: Rate limit middleware is disabled during tests

## 6. Audit Log

`cores/audit_log.py` provides a persistent, append-only audit trail:

- **Format**: JSONL (JSON Lines) — one JSON object per line
- **Path**: `~/.orion/audit.jsonl`
- **Permissions**: `chmod 600` — owner read/write only
- **Events logged**: `login`, `logout`, `token_revoke`, `license_activate`
- **Rotation**: Automatic at 10MB — 3 backup files are kept (`audit.jsonl.1`, `.2`, `.3`)
- **Content safety**: No secrets or tokens are ever written to the log
- **Query**: `get_recent(limit)` returns the most recent events in reverse chronological order

```python
# cores/audit_log.py:31-64
def log_event(event: str, actor: str = "", detail: str = "", metadata=None):
    # Rotate if oversized (>10MB)
    if os.path.exists(path) and os.path.getsize(path) > _MAX_BYTES:
        # shift backups .1 -> .2, .2 -> .3, then current -> .1
    entry = {"timestamp": ..., "event": event, "actor": actor, "detail": detail, "metadata": metadata}
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    os.chmod(path, 0o600)
```

## 7. Rate Limiting

The `api/middleware/rate_limit_middleware.py` implements per-identity rate limiting:

- **Identity resolution**: By JWT token `sub` claim first, fallback to client IP
- **Bucket**: Token bucket algorithm via `cores/gateway/rate_limit.py`
- **Key format**: `{path}:{identity}` — per-endpoint per-user quotas
- **Response**: HTTP 429 with `X-RateLimit-Remaining` header
- **Exempt paths**: `/api/health`, `/api/version`, `/api/docs`, `/api/openapi.json`, `/api/redoc`

## 8. Security Headers

The `api/middleware/error_handling.py` applies security headers to all responses via `SecurityHeadersMiddleware`:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws:; frame-ancestors 'none'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

## 9. CORS Configuration

`api/main.py` configures CORS separately for production and development:

- **Production** (`CATEYE_DESKTOP=1`): Restricted to `http://127.0.0.1:8000`, `http://localhost:8000`, `app://` (pywebview). Credentials allowed.
- **Development**: Wildcard `*` origin, credentials disabled (fix for CVE-7).

## 10. Error Handling

The `ErrorHandlingMiddleware` (`api/middleware/error_handling.py`) ensures no internal details leak:

- **Client response**: Generic `{"message": "An unexpected error occurred"}` with HTTP 500
- **Server log**: Full exception with traceback via `logger.exception()`
- **Fix for CVE-6**: Previously exception messages were included in HTTP responses

## 11. Known Resolved CVEs

| ID | Vulnerability | Fix | File |
|---|---|---|---|
| CVE-1 | HMAC-SHA256 hardcoded in license validator | Ed25519 asymmetric signatures | `cores/license/validator.py` |
| CVE-2 | AES key derived from world-readable `/etc/machine-id` | Random 32-byte key file, chmod 600 | `cores/identity_vault.py` |
| CVE-3 | Tokens and sessions stored in plaintext JSON | AES-256-GCM encryption on disk | `cores/auth/token_service.py`, `cores/auth/session.py` |
| CVE-4 | No CSRF protection | Double-submit cookie middleware | `api/middleware/csrf_middleware.py` |
| CVE-5 | OAuth2 Gmail missing `state` parameter | Cryptographically random state token | `cores/authhub/gmail.py` |
| CVE-6 | Exception messages leaked in HTTP responses | Generic error message, full log server-side | `api/middleware/error_handling.py` |
| CVE-7 | CORS `allow_credentials` with wildcard origin | Specific origins in production | `api/main.py` |
| CVE-8 | No audit logging | JSONL audit log, chmod 600, rotation | `cores/audit_log.py` |
| CVE-9 | API key in URL query param (orion_agent.py) | Moved to `X-Goog-Api-Key` header | `cores/ai/orion_agent.py` |
| CVE-10 | API key in URL query param (provider.py) | Moved to `X-Goog-Api-Key` header | `cores/ai/provider.py` |
| CVE-11 | SQL injection in `mobile.py _count()` | Table name whitelist (frozenset) | `api/routers/mobile.py` |
| CVE-12 | Token secret lost on restart | Persisted to `.auth_secret` file | `cores/auth/auth.py` |

## 11. Desktop Security

### 11.1 Boot Guard (`desktop/boot_guard.py`)

The desktop launcher validates the environment before starting:
- Checks runtime mode (dev, frozen, service)
- Validates file permissions on sensitive paths
- Falls back to safe mode if environment validation fails
- Logs a boot summary for diagnostics

### 11.2 Watchdog (`desktop/watchdog.py`)

A background monitoring thread that checks:
- Backend API health (`/api/health`)
- Process responsiveness
- Circuit breaker states via RecoveryEngine

If the watchdog detects a stuck process, it reports to the RecoveryEngine for automated healing.

### 11.3 Safe Mode

When the system detects an unsafe environment:
- Disables desktop tray and webview
- Falls back to browser-only mode
- Logs the reason for safe mode activation
- Allows manual override via `--safe-mode` flag

## 12. Known Resolved CVEs

1. **No hardcoded secrets**: All API keys and credentials are stored in IdentityVault (AES-256-GCM) or environment variables. Source code contains zero secrets.
2. **Encrypted disk storage**: All sensitive files (tokens, sessions, vault, licenses) are encrypted at rest using AES-256-GCM.
3. **OAuth2 state**: Every OAuth2 flow includes a cryptographically random state parameter to prevent CSRF attacks.
4. **Generic error messages**: Internal exceptions never leak to HTTP responses. All errors are logged server-side with full context.
5. **CSRF on all mutations**: Double-submit cookie pattern protects all state-changing endpoints. Only 5 paths are exempt.
6. **Rate limiting by identity**: Token-based rate limiting with IP fallback. Each user gets their own rate limit bucket per endpoint.
7. **Audit logging**: All authentication events (login, logout, token operations) are logged to a secure, append-only JSONL file with automatic rotation.
8. **Security headers**: CSP, HSTS, XFO, XCTO, and Referrer-Policy headers applied to every response.
9. **CORS restriction**: Production builds restrict origins to localhost and pywebview's `app://` protocol. Credentials only sent to known origins.
10. **SQL injection prevention**: Dynamic table names validated against a frozenset whitelist. All queries use SQLAlchemy parameterized queries or `text()` with no string concatenation.
11. **Dependency security**: Python dependencies managed via `requirements.txt`, frontend via `package-lock.json`. Not yet audited with automated tools (known debt item).
