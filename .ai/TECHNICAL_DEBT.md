# OWNEX TECHNICAL DEBT — Technical Debt Tracker

> **What is Technical Debt?**
> Technical debt is the implied cost of additional rework caused by choosing an easy solution now instead of using a better approach that would take longer.

---

## Critical Debt (P0)

### Mobile Companion Not Functional
- **Issue:** Mobile Companion requires Supabase but it's not configured
- **Impact:** Mobile ecosystem (Alpha/Omega) incomplete
- **Cost:** User cannot use mobile sync, push notifications, approvals
- **Plan:** Configure Supabase in frontend/.env
- **Estimate:** 2 hours
- **Owner:** User (requires Supabase account)

### Android Crash on Launch
- **Issue:** 3 distinct namespaces (rastro/catseye/CATEYE)
- **Impact:** Android app crashes on launch
- **Cost:** Mobile experience non-existent
- **Plan:** Unify namespace to ai.rastro.app
- **Estimate:** 1 hour
- **Owner:** Requires Java installation (sudo)

### WearOS Not Buildable
- **Issue:** Only 4 mock files, no build.gradle/manifest
- **Impact:** WearOS cannot be built or deployed
- **Cost:** Smartwatch experience non-existent
- **Plan:** Implement real WearOS or discard
- **Estimate:** 8 hours (real implementation) or 0.5 hours (discard)
- **Owner:** User decision needed

---

## Important Debt (P1)

### Frontend TypeScript Errors
- **Issue:** 254 pre-existing tsc errors in unmaintained pages
- **Impact:** Code quality questionable, type safety compromised
- **Cost:** Potential runtime errors, difficult debugging
- **Plan:** Fix tsc errors in pages (Capital.vue, LifeManagement.vue, ReportPipeline.vue, etc.)
- **Estimate:** 6 hours
- **Owner:** Dev
- **Status:** Blocked by vue-tsc dependency issue

### Console.log in Mobile Frontend
- **Issue:** Console.log statements in MobileCompanion.vue, MobileCompanionJarvis.vue, ModernNavbar.vue, SteamBigPictureSplash.vue
- **Impact:** Performance degradation, security risk in production
- **Cost:** Excess log output, potential information leakage
- **Plan:** Remove console.log statements
- **Estimate:** 0.5 hours
- **Owner:** Dev

---

## Minor Debt (P2)

### Auto Maintenance System Not Exists
- **Issue:** OWNEX cannot automatically detect errors, outdated libraries, old documentation, incorrect configurations
- **Impact:** Debt accumulates, system degrades over time
- **Cost:** Manual maintenance burden
- **Plan:** Implement basic auto-diagnosis and recommendation system
- **Estimate:** 12 hours
- **Owner:** Dev

### Lint Errors (Legacy)
- **Issue:** 30 remaining lint errors (legacy code, not new)
- **Impact:** Code style inconsistency, potential bugs
- **Cost:** Maintenance burden
- **Plan:** Fix remaining lint errors (E741, F401, F841)
- **Estimate:** 2 hours
- **Owner:** Dev

### Premium Sounds Not Fully Implemented
- **Issue:** Premium sounds not implemented in all interactions
- **Impact:** Inconsistent user experience
- **Cost:** Not achieving premium feel
- **Plan:** Implement sounds in all components
- **Estimate:** 4 hours
- **Owner:** Dev

---

## Decisions Made

### cores/ vs cores/ Decision (2026-07-31)
- **Decision:** cores/ is Single Source of Truth (SSOT)
- **Reason:** cores/ has 845 files vs 533 in core/, 2x more imports in API, contains productive CATEYE pipeline
- **Plan:** Migrate core/ to cores/ gradually
- **Status:** In progress
- **Estimate:** 8 hours

---

## Debt Reduction Strategy

### 1. Pay Critical Debt First
- Mobile Companion (configure Supabase)
- Android namespace (unify)
- WearOS (decision)

### 2. Pay Important Debt Second
- Fix tsc errors
- Remove console.log
- Implement auto maintenance

### 3. Pay Minor Debt Last
- Fix lint errors
- Implement premium sounds
- Complete cores/ migration

---

## Debt Budget

**Total Debt Cost Estimate:** 43.5 hours

| Priority | Debt Items | Hours | Completed | Remaining |
|----------|-----------|-------|-----------|-----------|
| P0 | Mobile Companion, Android, WearOS | 11.5 | 0 | 11.5 |
| P1 | tsc errors, console.log | 6.5 | 0 | 6.5 |
| P2 | Auto maintenance, lint, sounds | 18 | 0 | 18 |
| Decision | cores/ migration | 8 | 0 | 8 |

---

## Prevention

### Rules to Avoid New Debt

1. **No TODO without date** - Every TODO must have a deadline
2. **No dead code** - Delete obsolete code immediately
3. **No unused imports** - Remove unused imports immediately
4. **No console.log in production** - Use proper logging
5. **Type safety** - Use TypeScript strict mode
6. **Lint passing** - All code must pass lint
7. **Tests passing** - All tests must pass before commit
8. **Documentation** - Document complex logic

### Code Review Checklist

- [ ] No new TODOs without dates
- [ ] No dead code added
- [ ] No unused imports
- [ ] No console.log in production code
- [ ] TypeScript strict mode compliant
- [ ] Lint passing
- [ ] Tests passing
- [ ] Documentation updated

---

## Debt Payoff Log

| Date | Debt Item | Hours Spent | Status |
|------|-----------|-------------|--------|
| 2026-08-01 | N/A | 0 | N/A |

---

## Last Updated

**Date:** 2026-08-01
**Updated By:** CATEYE Excellence Protocol
**Version:** 1.0
