# OWNEX Security Policy

> **Generated from actual codebase** — This document reflects the real implementation.

## Security Model

### Principles

1. **100% Local** — Nothing leaves your machine without explicit consent. No telemetry, no cloud dependencies for core functionality.
2. **Defense in Depth** — Multiple layers: network, application, data, device.
3. **Minimal Attack Surface** — No external ports in production, local-only by default.
4. **Audit Everything** — Structured JSONL logs for all security events.
5. **Fail Secure** — Errors never expose secrets, stack traces, or internal state.

### Threat Model

| Asset | Threats | Mitigations |
|-------|---------|-------------|
| **Credentials** (API keys, tokens) | Theft via XSS, malware, backup leak | IdentityVault (AES-256-GCM), httpOnly cookies, no localStorage |
| **Financial Data** | Tampering, disclosure | Signed license (Ed25519), SQLite WAL, audit log |
| **User Identity** | Impersonation, session hijack | Device binding, short JWT (30m), refresh rotation |
| **AI Providers** | Key leakage, cost abuse | OAR budget ($0 default), circuit breakers, no keys in frontend |
| **Sync Data** | MITM, replay | TLS (mobile), Data Layer (watch), idempotency keys |

---

## Authentication

### Device Identity
- **Auto-generated UUID** on first run (`CATEYE-device-id` in localStorage / `%LOCALAPPDATA%/OWNEX/desktop_device.json`)
- **No email/password** — device-based auth
- **Registration**: `POST /api/auth/device-login {device_id, platform}`
- **Returns**: JWT (30m) + httpOnly cookie `ownex-session` (24h refresh)

### Session Management
| Token | Lifetime | Storage | Rotation |
|-------|----------|---------|----------|
| Access JWT | 30 min | Memory (JS) + httpOnly cookie | Auto-refresh via `/api/auth/refresh` |
| Refresh Token | 24 h | httpOnly cookie + DB | New refresh on each use |
| Device ID | Permanent | localStorage / file | Never rotates |

### CSRF Protection
- **Double-submit cookie**: `csrf-token` cookie + `X-CSRF-Token` header
- **Exempt**: `GET`, `HEAD`, `OPTIONS`, `/api/health`, `/api/auth/*`, WebSocket
- **Dev override**: `CATEYE_CSRF_DISABLED=1`

### Rate Limiting
- **Algorithm**: Token bucket (burst 50, sustained 30 req/s)
- **Identity**: Bearer token `sub` claim → fallback to IP
- **No-limit paths**: `/health`, `/version`, `/docs`, `/api/auth/*`
- **Headers**: `X-RateLimit-Remaining`, `Retry-After` on 429

---

## Authorization

### Device Binding
- JWT contains `device_id` claim
- Backend validates `device_id` matches registered device
- Mismatch → 401 + device re-registration required

### Scopes (Future)
- Current: Single privilege level (full access)
- Planned: `read`, `write`, `admin`, `financial`

---

## Data Protection

### IdentityVault (`cores/identity_vault.py`)

```python
# Encryption: AES-256-GCM
# Key: 32 random bytes (secrets.token_bytes), chmod 600
# Storage: ~/.ownex/identity_vault.key (key) + identity_vault.json (encrypted data)
# Migration: Automatic from legacy machine-id derived key
```

**Protected Data**:
- API keys (OpenRouter, Anthropic, exchange APIs)
- Wallet private keys
- OAuth tokens
- Bank credentials

### License System (`cores/license/`)

```python
# Asymmetric: Ed25519
# Public key: Embedded in binary
# Private key: License server only
# Format: 25-char string (backward compatible)
# Verification: Cryptographic, not obfuscation
```

### Database
- **Engine**: SQLite (dev) / PostgreSQL (prod)
- **WAL Mode**: Enabled for concurrency + durability
- **Encryption**: Not encrypted at rest (local-only threat model)
- **Backup**: `run.py --backup` → timestamped `.db` + WAL checkpoint

### Audit Log (`cores/audit_log.py`)

```json
{
  "timestamp": "2026-08-27T10:30:00.123Z",
  "event": "login",
  "status": "success",
  "user_id": "dev_abc123",
  "device_id": "uuid",
  "ip": "127.0.0.1",
  "details": {}
}
```
- **Format**: JSONL, append-only
- **Rotation**: 10MB daily
- **Permissions**: chmod 600
- **Events**: `login`, `logout`, `token_stored`, `financial_transaction`, `credential_access`, `config_change`

---

## Network Security

### Production (Desktop Bundle)
- **Backend**: `127.0.0.1:8000` (loopback only)
- **Frontend**: `tauri://localhost` (WebView2)
- **WebSocket**: `ws://127.0.0.1:8000/api/ws/terminal`
- **No external connections** from bundle

### Development
- **Frontend**: `http://localhost:5173` (Vite)
- **Backend**: `http://127.0.0.1:8000`
- **CORS**: `*` (dev), restricted origins (prod)

### Mobile
- **API**: `https://<desktop-ip>:8000` (TLS, self-signed cert pinned)
- **WebSocket**: `wss://<desktop-ip>:8000/api/ws/terminal`
- **FCM**: Google push infrastructure

### Watch
- **Sync**: Google Play Services Data Layer (encrypted)
- **No direct network** — all via phone

### CORS Policy (`api/main.py:403`)

```python
# Production (OWNEX_DESKTOP=1):
allow_origins = [
    "http://127.0.0.1",
    "http://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "app://",
]
allow_credentials = True

# Development (OWNEX_DESKTOP not set):
allow_origins = ["*"]
allow_credentials = False  # Per Fetch spec
```

### Security Headers (`api/middleware/error_handling.py`)

```python
# Applied to all responses:
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
# CSP (Tauri):
# default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; 
# style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:* ws://localhost:*
```

---

## AI Security

### OAR Runtime (`cores/ai/runtime/`)

```python
# Budget: $0/day default (explicit opt-in for paid)
# Circuit Breaker: 3 failures → 60s open
# Cost Tracking: Per provider/model, daily aggregation
# Cache: Semantic (prompt hash), TTL 1h
# Learning: Routing preferences by TaskType
# Fallback Chain: OmniRoute → FCC → Ollama → OpenCode
```

### Provider Keys
- **Never in frontend** — only in backend config/env
- **FCC Proxy**: `ANTHROPIC_API_KEY=orion-dev-local` (local proxy)
- **OmniRoute**: `OPENROUTER_API_KEY` in `~/.config/omniroute/config.yaml`
- **Ollama**: No key (local)

### MERLIN
- **No autonomous actions** — only suggestions
- **Human gate** required for all executions
- **Context**: Reads canonical state via API (never direct DB)
- **Memory**: UnifiedMemoryStore (namespace `merlin`)

---

## Financial Security

### Payment Compatibility Engine
- **Honest verdicts**: Never invent workarounds for KYC/entity requirements
- **Incompatible = 0 score** with explicit reason (e.g., "Requires US LLC")
- **Verified accounts only** — user-configured, persisted in `~/.config/ownex/payment_network.json`

### Revenue Tracking
- **Expected ≠ Realized** — strict separation
- **Money only in PAID** — `ACCEPTED`/`PENDING` not counted as cash
- **RevenueTracker** recomputes from current state (no incremental accumulation bugs)

### Investment Execution
- **DRY_RUN default** — never moves real money without explicit config
- **Human gate** required for every execution
- **Idempotency keys** on all financial mutations
- **Emergency stop** kills all copy trading instantly

---

## Cryptography

| Purpose | Algorithm | Implementation |
|---------|-----------|----------------|
| Symmetric encryption | AES-256-GCM | `cryptography.hazmat` |
| Asymmetric signatures | Ed25519 | `cryptography.hazmat` |
| Key derivation | HKDF-SHA256 | `cryptography.hazmat` |
| Random generation | `secrets.token_bytes` | Stdlib `secrets` |
| Password hashing | Argon2id | `passlib` (if used) |
| TLS | TLS 1.3 | `rustls` (Tauri), `ssl` (Python) |

### Key Management
| Key | Storage | Rotation |
|-----|---------|----------|
| IdentityVault master | `~/.ownex/identity_vault.key` (chmod 600) | Manual (emergency) |
| License signing | Embedded public / Server private | Annual (server) |
| JWT signing | HS256 (env `JWT_SECRET`) | 90 days |
| TLS certs | Self-signed (mobile) / Let's Encrypt (prod) | 90 days |

---

## Secure Development

### Code Practices
- **No secrets in code** — all via env/vault
- **Parameterized queries** — SQLAlchemy ORM (no raw SQL)
- **Input validation** — Pydantic models on all endpoints
- **Output encoding** — Jinja2 autoescape, Vue auto-escape
- **Dependency scanning** — `pip-audit`, `npm audit` in CI

### CI/CD Security
```yaml
# .github/workflows/test.yml
- run: pip-audit
- run: npm audit
- run: cargo audit
- run: bandit -r .
- run: .venv/bin/python -m pytest --ignore=tests/test_security.py
```

### Secrets Management
- **Never commit** `.env`, `*.key`, `*.jks`, `*.pem`
- **GitHub Secrets** for CI/CD
- **Local**: `~/.orion/config.sh` (sourced in shell)
- **Pre-commit**: `gitleaks` (if configured)

---

## Incident Response

### Detection
- **Automated**: Health checks, audit log anomalies, error rate spikes
- **Manual**: User reports, security@ email

### Response Levels

| Level | Trigger | Response Time | Actions |
|-------|---------|---------------|---------|
| **Critical** | Active breach, data exfiltration | 15 min | Isolate, preserve evidence, notify |
| **High** | Vulnerability exploited | 1 hour | Patch, deploy, verify |
| **Medium** | Suspicious activity | 4 hours | Investigate, mitigate |
| **Low** | Policy violation | 24 hours | Educate, remediate |

### Playbooks
| Scenario | Playbook |
|----------|----------|
| Credential leak | Rotate key, invalidate sessions, audit access |
| SQL injection attempt | WAF rule, parameterize query, scan |
| XSS attempt | CSP report, sanitize input, scan |
| AI budget abuse | Circuit breaker, budget alert, cap |
| Mobile MITM | Cert pinning, HSTS, mTLS (future) |

---

## Compliance

### Standards Alignment
| Standard | Status | Notes |
|----------|--------|-------|
| **OWASP Top 10** | Addressed | CSP, CSRF, rate limit, validation |
| **NIST 800-53** | Partial | Auth, audit, encryption, IR |
| **GDPR** | Local-only | No personal data collection |
| **SOC 2 Type II** | Not certified | Controls documented |

### Data Retention
| Data Type | Retention | Deletion |
|-----------|-----------|----------|
| Audit logs | 1 year | Auto-purge |
| Financial records | 7 years | Manual |
| AI conversations | 90 days | Auto-purge |
| Device sessions | 30 days | Auto-purge |
| Backups | 30 days | Auto-purge |

---

## Security Contacts

- **Email**: security@ownex.local (configure in deployment)
- **PGP**: Not configured (local-only)
- **Bug Bounty**: Not applicable (private tool)

---

## Security Checklist (Pre-Release)

- [ ] `pip-audit` clean
- [ ] `npm audit` clean
- [ ] `cargo audit` clean
- [ ] `bandit -r .` clean
- [ ] No secrets in repo (`gitleaks` or `trufflehog`)
- [ ] All endpoints have auth (except health/version)
- [ ] CSRF on all mutating endpoints
- [ ] Rate limiting on all API endpoints
- [ ] CSP headers present
- [ ] Security headers present
- [ ] Audit log captures login/financial/credential events
- [ ] IdentityVault encrypts all credentials
- [ ] License uses Ed25519
- [ ] AI budget default $0
- [ ] DRY_RUN default for trading
- [ ] Emergency stop tested
- [ ] Backup/restore tested
- [ ] Mobile TLS cert pinned
- [ ] Watch Data Layer encrypted

---

*Document generated from codebase. Last verified: 2026-08-27*