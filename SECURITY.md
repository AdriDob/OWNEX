# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 7.x.x   | ✅ Yes             |
| 6.x.x   | ❌ No              |
| < 6.0   | ❌ No              |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in OWNEX, please report it responsibly:

### Responsible Disclosure Process

1. **Do NOT** create a public GitHub issue for the vulnerability
2. Email us at: **security@ownex.ai**
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: < 30 days, High: < 60 days, Medium: < 90 days)

## Security Measures

### OWNEX Core
- All API endpoints require authentication
- Role-based access control (RBAC) on all operations
- Input validation and sanitization on all endpoints
- Secure defaults (fail-closed on authentication)
- Audit logging for all sensitive operations

### Data Protection
- Encrypted secrets storage
- No hardcoded credentials in codebase
- Environment-based configuration
- Secure key rotation procedures

### Dependencies
- Automated dependency scanning (GitHub Dependabot)
- Regular security audits
- Pinned dependency versions in production
- License compliance verification

## Bug Bounty

We run a private bug bounty program. Contact security@ownex.ai for details.

## Security Contacts

- **Primary**: security@ownex.ai
- **PGP Key**: Available on request

---

*This security policy follows industry best practices for open source projects.*