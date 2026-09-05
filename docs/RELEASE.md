# OWNEX Release Process

> **Generated from actual codebase** — This document reflects the real implementation.

## Release Philosophy

- **Revenue Rule**: No feature enters release without measurable impact on detection/evidence/acceptance/learning
- **Stability > Features**: Freeze on STABLE, only security/bugfixes after
- **Reproducible Builds**: Single lockfile, pinned versions, verified artifacts
- **Semantic Versioning**: MAJOR.MINOR.PATCH (7.0.0, 7.1.0, 7.0.1)

## Version Management

### Single Source of Truth
- **File**: `VERSION` (repo root)
- **Current**: `7.0.0`
- **Sync Script**: `scripts/sync_version.py`

```bash
# Sync version to all manifests
.venv/bin/python scripts/sync_version.py
# Updates: pyproject.toml, package.json, Cargo.toml, tauri.conf.json, src-tauri/Cargo.toml
```

### Version Format
| Type | Format | Example |
|------|--------|---------|
| Stable | `MAJOR.MINOR.PATCH` | `7.0.0` |
| RC | `MAJOR.MINOR.PATCH-rc.N` | `7.0.0-rc.1` |
| Alpha | `MAJOR.MINOR.PATCH-alpha.N` | `1.0.1-alpha` |
| Dev | `MAJOR.MINOR.PATCH-dev` | `7.1.0-dev` |

## Release Phases

### Phase 1: Feature Complete (RC-1)
- All planned features implemented
- Test matrix passing (434 tests)
- Security deep-scan clean
- Performance baseline measured
- Documentation complete

### Phase 2: Release Candidate (RC-2)
- Windows validation passed (physical hardware)
- 24h soak test passed
- Installer artifacts verified (MSI/NSIS)
- Checksums published
- Rollback tested

### Phase 3: Stable
- All RC gates passed
- Git tag created (`v7.0.0`)
- GitHub Release published
- Artifacts uploaded
- CHANGELOG updated

## Build Process

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 20+ |
| Rust | 1.75+ |
| Rust targets | `x86_64-pc-windows-msvc`, `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin` |
| WiX Toolset | 3.11+ (Windows MSI) |
| NSIS | 3.08+ (Windows installer) |

### Build Commands

```bash
# 1. Sync version
.venv/bin/python scripts/sync_version.py

# 2. Frontend build
cd frontend
npm ci
npm run build
# Output: frontend/dist/

# 3. Python sidecar (ONEFILE)
cd /home/adriel/projects/Rastro
.venv/bin/pyinstaller OWNEX-Backend.spec --clean --noconfirm
# Output: dist/ownex-backend/ownex-backend.exe (~50MB)

# 4. Tauri build (Windows)
cd src-tauri
cargo tauri build --target x86_64-pc-windows-msvc
# Output: src-tauri/target/x86_64-pc-windows-msvc/release/bundle/
#   - msi/OWNEX Alpha_7.0.0_x64_es-ES.msi
#   - nsis/OWNEX Alpha_7.0.0_x64-setup.exe
#   - appimage/OWNEX-Alpha-7.0.0.AppImage (Linux)

# 5. Verify artifacts
.venv/bin/python scripts/verify_artifacts.py
```

### Artifact Verification

```bash
# scripts/verify_artifacts.py checks:
# 1. Sidecar >= 50MB (not stub)
# 2. MSI/NSIS install silently
# 3. App launches, health endpoint responds
# 4. SHA256 matches SHA256SUMS.txt
# 5. Version in app matches VERSION file
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ownex-tauri-windows.yml
on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - uses: actions/setup-node@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: npm ci
      - run: npm run build
      - run: .venv/bin/pyinstaller OWNEX-Backend.spec
      - run: cargo tauri build
      - run: .venv/bin/python scripts/verify_artifacts.py
      - uses: actions/upload-artifact@v4
        with:
          name: OWNEX-Artifacts
          path: src-tauri/target/release/bundle/
```

## Artifacts

### Windows
| Artifact | Size | SHA256 Location |
|----------|------|-----------------|
| `OWNEX Alpha_7.0.0_x64_es-ES.msi` | ~340MB | `SHA256SUMS.txt` |
| `OWNEX Alpha_7.0.0_x64-setup.exe` | ~340MB | `SHA256SUMS.txt` |

### Linux
| Artifact | Size |
|----------|------|
| `OWNEX-Alpha-7.0.0.AppImage` | ~90MB |

### macOS (Future)
| Artifact | Size |
|----------|------|
| `OWNEX-Alpha-7.0.0.dmg` | ~100MB |
| `OWNEX-Alpha-7.0.0.aarch64.dmg` | ~100MB |

### Checksums
```bash
# SHA256SUMS.txt format:
7a7e215dae1813b84779788ee700a8616672159fb9b5aa519882dc2d2e4cda5f  msi/OWNEX Alpha_7.0.0_x64_es-ES.msi
9833315e4a6ab892066864bd4e49b13cb5a808622c311600b739368661646e86  nsis/OWNEX Alpha_7.0.0_x64-setup.exe
```

### Verification Script (Windows)
```powershell
# VERIFY-INSTALL.ps1 -Checksums
# 1. Download artifacts
# 2. Verify SHA256SUMS.txt
# 3. Install MSI/NSIS
# 4. Launch app, verify health endpoint
# 5. Test restart persistence
# 6. Optional: 24h soak test
```

## Release Checklist

### Pre-Release
- [ ] All tests passing (`make test-fast`, `make check`)
- [ ] Frontend build clean (`vue-tsc --noEmit`, `vite build`)
- [ ] Version synced (`scripts/sync_version.py`)
- [ ] CHANGELOG updated
- [ ] Security scan clean (`pip-audit`, `npm audit`)
- [ ] Dependencies audited

### Build Validation
- [ ] Python sidecar >= 50MB
- [ ] Tauri build succeeds (MSI + NSIS)
- [ ] Artifacts pass verification script
- [ ] SHA256SUMS.txt generated
- [ ] Version in app matches VERSION file

### Windows Validation (Physical Hardware)
- [ ] Clean install on Windows 11
- [ ] Backend starts (sidecar health OK)
- [ ] Frontend loads (Mission Control shows data)
- [ ] Database persists (restart test)
- [ ] Terminal works (WebSocket)
- [ ] System tray functions
- [ ] Auto-updater check works
- [ ] Uninstall cleans up

### Soak Test (Optional)
- [ ] 2h basic
- [ ] 8h extended
- [ ] 24h full (with `-RunSoakTest`)

### Release Publication
- [ ] Git tag created: `git tag -a v7.0.0 -m "OWNEX 7.0.0 STABLE"`
- [ ] Git push tags: `git push origin v7.0.0`
- [ ] GitHub Release created with artifacts
- [ ] SHA256SUMS.txt attached
- [ ] Release notes from CHANGELOG
- [ ] Announcement prepared

## Rollback Procedure

### If Critical Bug Found Post-Release

```bash
# 1. Revert tag
git tag -d v7.0.0
git push origin :refs/tags/v7.0.0

# 2. Create hotfix branch
git checkout -b hotfix/7.0.1 v7.0.0^

# 3. Fix bug, test, rebuild
# 4. Tag new version
git tag -a v7.0.1 -m "OWNEX 7.0.1 HOTFIX"
git push origin v7.0.1

# 5. Update GitHub Release
# 5. Communicate to users
```

### Emergency Rollback (User Side)
```powershell
# Windows: Uninstall via Settings > Apps
# Or run uninstaller
"%LOCALAPPDATA%\OWNEX Alpha\uninstall.exe"

# Data preserved in %LOCALAPPDATA%\OWNEX\
# Reinstall previous version from GitHub Releases
```

## Post-Release

### Monitoring (First 48h)
- [ ] GitHub Issues for regressions
- [ ] Discord/Telegram for user reports
- [ ] Error rate monitoring (`/api/metrics`)
- [ ] AI cost monitoring (`/api/oar/status`)

### First Patch Window (2 weeks)
- Only: security fixes, critical bugs, data loss prevention
- No: new features, refactors, visual changes

---

*Document generated from codebase. Last verified: 2026-08-27*