# Security Policy

## Reporting a Vulnerability

OWNEX is a private system. If you discover a security issue in the repository or
the software it describes, report it privately instead of opening a public issue:

**security@ownex.ai**

Include, when possible:

- Affected version and component
- Steps to reproduce
- Impact assessment
- Suggested fix (optional)

Acknowledgement within 48h; no public disclosure until resolved.

## Security Model

OWNEX is **100% local by default** — nothing leaves the machine, no telemetry.

| Layer | Control |
|---|---|
| Credentials | IdentityVault — AES-256-GCM, random key, `chmod 600` |
| Licensing | Ed25519 asymmetric signatures, 25-char format |
| Sessions | Token service with device binding, 30 min expiry, revocation |
| CSRF | Double-submit cookie on all state-changing routes |
| Rate limiting | Identity-based with IP fallback |
| Audit | Append-only JSONL log, 10 MB rotation |
| Secrets | Never in the repository — IdentityVault or env vars only |

## Supported Versions

| Version | Supported |
|---|---|
| 7.0.0 (current) | ✅ |
| < 7.0.0 | ❌ |

## Security Principles

- **Secure by default**: everything locked down unless explicitly opened
- **No hardcoded secrets**: keys come from vault/env, never source
- **Error handling**: no stack traces leaked to clients, server-side logging only
- **Minimal surface**: no cloud, no telemetry, no third-party runtime calls

## Dependencies

Dependency updates are tracked via Dependabot on the default branch; security
advisories are applied on a best-effort schedule aligned with the release cycle.
