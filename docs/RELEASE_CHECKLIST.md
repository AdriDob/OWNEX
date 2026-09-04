# OWNEX Release Checklist v7.1.0

## Pre-Release

### Code Quality
- [x] All fast tests pass (100 passed, 1 skipped)
- [x] Ruff lint clean (0 critical errors)
- [x] Frontend build successful
- [x] TypeScript type check clean
- [x] No hardcoded secrets
- [x] Email system enhanced with priority headers

### Features Complete
- [x] Mode System (LITE/FULL/CAPITAL)
- [x] LITE mode: OneActionCard, IncomeHome
- [x] CAPITAL mode: Capital.vue (12 tabs)
- [x] FULL mode: OperationsDashboard
- [x] Agent Orchestrator: CommanderAgent
- [x] Provider system: 7 fallback chains
- [x] Automation: 49 scheduler jobs
- [x] Desktop/Mobile/Watch support

### Security
- [x] Removed hardcoded API key from fcc_provider.py
- [x] All secrets from environment variables
- [x] Email priority headers implemented
- [x] SPF/DKIM/DMARC documentation

### Performance
- [x] App startup: 2.57s
- [x] Database queries: 6ms
- [x] API health: 33ms
- [x] Frontend build: 12.14s
- [x] Optimized quick_wins.py queries

### Documentation
- [x] PERFORMANCE.md created
- [x] EMAIL_DELIVERY.md created
- [x] RELEASE_CHECKLIST.md created

## Release Steps

### 1. Version Update
```bash
# Update VERSION.txt
echo "7.1.0" > VERSION.txt

# Update pyproject.toml
# Update package.json
```

### 2. Git Operations
```bash
# Stage all changes
git add .

# Commit changes
git commit -m "Release v7.1.0: Performance optimization + security hardening"

# Tag release
git tag -a v7.1.0 -m "Release v7.1.0"

# Push to remote
git push origin main --tags
```

### 3. Build Artifacts
```bash
# Frontend build
cd frontend && npm run build

# Desktop build (PyInstaller)
make build-desktop

# Android build
make build-android
```

### 4. Verification
```bash
# Run full test suite
python scripts/dev test

# Verify frontend
cd frontend && npm run build

# Verify backend
python -c "from api.main import app; print('App OK')"
```

### 5. Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Monitor health endpoints
- [ ] Verify email notifications

## Post-Release

### Monitoring
- [ ] Check API response times
- [ ] Monitor error rates
- [ ] Verify scheduler jobs running
- [ ] Check email delivery

### Documentation
- [ ] Update CHANGELOG.md
- [ ] Update README.md
- [ ] Announce release

## Rollback Plan

If issues detected:
1. Revert to previous tag
2. Redeploy previous version
3. Notify users
4. Investigate and fix

## Release Notes

### v7.1.0 (2026-08-28)

#### Added
- Email priority headers (Importance, X-Priority, X-MSMail-Priority)
- Configurable email recipient via OWNEX_NOTIFICATION_EMAIL
- Email retry logic with exponential backoff
- Email delivery tracking and statistics
- SPF/DKIM/DMARC documentation
- Performance documentation

#### Fixed
- Removed hardcoded API key from fcc_provider.py
- Fixed 3 failing tests (availability, desktop native)
- Optimized database queries with limits
- Fixed missing __init__.py files (25 files)
- Fixed import errors (cores.autonomy, cores.scheduler)

#### Security
- All secrets now read from environment variables
- Email system hardened with priority headers
- No hardcoded credentials in production code

#### Performance
- App startup: 2.57s
- Database queries: 6ms
- API health: 33ms
- Frontend build: 12.14s
