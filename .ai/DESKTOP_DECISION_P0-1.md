# P0-1 DESKTOP DECISION — Tauri vs PySide6

**Fecha:** 2026-08-26  
**Estado:** DECISION REQUIRED  
**Prioridad:** P0 - BLOCKING

---

## 1. CURRENT STATE ANALYSIS

### 1.1 Tauri Implementation (Production)

**Location:** `src-tauri/`

**Evidence:**
- ✅ Tauri v2 configuration (`tauri.conf.json`)
- ✅ Cargo.toml with full dependencies
- ✅ Sidecar configured: `binaries/ownex-backend`
- ✅ Build target directory exists
- ✅ Product name: "OWNEX Alpha"
- ✅ Version: 1.0.1
- ✅ Windows installer (MSI/NSIS) generated
- ✅ Deployed to OneDrive (SHA256 verified)

**From ARCHITECTURE_CURRENT.md:**
```
OWNEX Alpha.exe (Tauri 2 · WebView2 · tray)
├── Vue 3 SPA — frontend/dist embebido
├── Sidecar ownex-backend.exe (PyInstaller ONEFILE)
└── Lifecycle: backend-ready event · kill-on-exit + watchdog
```

**From CURRENT_STATE.md:**
```
v1.0.1-alpha cortada + desplegada en OneDrive
Hashes MSI `85256fbc…` / NSIS `d171cab6…` verificados ×2
```

### 1.2 PySide6 Implementation (Legacy)

**Location:** `desktop/`

**Evidence:**
- ✅ Full modules implemented (`main_desktop.py`, `native/`, `tray.py`, etc.)
- ✅ Services layer (`desktop/native/services/`)
- ✅ UI structure (`desktop/native/ui/`)
- ✅ More Python code than Tauri
- ❌ Not mentioned in ARCHITECTURE_CURRENT.md
- ❌ Not referenced in CURRENT_STATE.md as production
- ❌ No evidence of recent builds or deployment

**From RELEASE_AUDIT.md:**
```
### 1.2 Desktop (PySide6 Qt)
**Estado:** ✅ Functional, pero con Tauri duplicado
**Problema P0:** Duplicación de implementación desktop
```

---

## 2. EVIDENCE-BASED ASSESSMENT

### 2.1 Production Evidence

| Evidence | Tauri | PySide6 |
|----------|-------|---------|
| **In ARCHITECTURE_CURRENT.md?** | ✅ Yes | ❌ No |
| **In CURRENT_STATE.md?** | ✅ Yes | ❌ No |
| **Build artifacts exist?** | ✅ Yes | ❌ No |
| **Deployed to OneDrive?** | ✅ Yes | ❌ No |
| **SHA256 verified?** | ✅ Yes | ❌ No |
| **Installer generated?** | ✅ Yes | ❌ No |
| **Recently built?** | ✅ Yes (2026-08-25) | ❌ No |

### 2.2 Functionality Comparison

| Feature | Tauri | PySide6 |
|---------|-------|---------|
| **Vue 3 SPA embedding** | ✅ Yes | ❌ No (Qt-based UI) |
| **Backend sidecar** | ✅ Yes | ✅ Yes |
| **Tray icon** | ✅ Yes | ✅ Yes |
| **Windows installer** | ✅ Yes | ❌ No |
| **Cross-platform** | ✅ Yes | ✅ Yes |
| **Modern web stack** | ✅ Yes | ❌ No |
| **Native Qt UI** | ❌ No | ✅ Yes |
| **Add Target functionality** | ✅ Yes | ✅ Yes |
| **Empty states** | ✅ Yes | ✅ Yes |

### 2.3 Architecture Consistency

The system uses:
- **Backend:** FastAPI (Python)
- **Frontend:** Vue 3 + TypeScript
- **Mobile:** Capacitor (Vue-based)
- **Watch:** WearOS (Java native)

**Tauri is consistent:**
- Uses the same Vue 3 frontend as web/mobile
- Single frontend codebase for all surfaces
- Modern web stack

**PySide6 is inconsistent:**
- Requires Qt-based UI (duplicate frontend)
- Different from web/mobile
- Legacy approach

---

## 3. DECISION CRITERIA

### 3.1 Revenue Rule Impact

**Tauri:**
- ✅ Maintains current production build
- ✅ Zero regression risk
- ✅ Consistent with mobile/web frontend
- ✅ Faster to release (already built)

**PySide6:**
- ❌ Requires migration from Tauri
- ❌ High regression risk
- ❌ Inconsistent frontend stack
- ❌ Slower to release (new build required)

### 3.2 Effort Estimation

**Option A: Keep Tauri, Remove PySide6**
- Effort: **L** (Low)
- Risk: **L** (Low)
- Time: **1-2 days**
- Tasks:
  1. Archive `desktop/` to `desktop-legacy/`
  2. Update documentation
  3. Verify Tauri build works
  4. Update README

**Option B: Migrate to PySide6, Remove Tauri**
- Effort: **XL** (Extra Large)
- Risk: **H** (High)
- Time: **2-3 weeks**
- Tasks:
  1. Migrate PySide6 to use same backend
  2. Implement Windows installer for PySide6
  3. Migrate all Tauri-specific functionality
  4. Test on Windows
  5. Generate new installer
  6. Deploy to OneDrive
  7. Update all documentation
  8. Regression testing

### 3.3 Technical Debt

**Tauri:**
- ✅ Modern stack (Tauri v2)
- ✅ Consistent with frontend
- ✅ Smaller codebase
- ✅ Better performance (WebView2)

**PySide6:**
- ❌ Legacy stack (Qt6)
- ❌ Inconsistent with frontend
- ❌ Larger codebase
- ❌ More dependencies

---

## 4. RECOMMENDATION

### **OPTION A: KEEP TAURI, REMOVE PYSIDE6**

**Rationale:**

1. **Production Evidence:** Tauri is the current production build, verified and deployed
2. **Architecture Consistency:** Tauri uses the same Vue 3 frontend as web/mobile
3. **Revenue Rule:** Zero regression risk, faster to release
4. **Effort:** Low effort (1-2 days) vs high effort (2-3 weeks)
5. **Technical Debt:** Tauri is modern, PySide6 is legacy
6. **User Impact:** No user impact (current build continues)

**Decision:**
- ✅ **Keep Tauri** as the desktop implementation
- ❌ **Remove PySide6** as legacy code
- 📦 Archive `desktop/` to `desktop-legacy/`
- 📝 Update all documentation

---

## 5. EXECUTION PLAN

### Phase 1: Archive PySide6 (Day 1)

1. Create `desktop-legacy/` directory
2. Move `desktop/` to `desktop-legacy/`
3. Add README in `desktop-legacy/` explaining archival
4. Update `.gitignore` if needed

### Phase 2: Update Documentation (Day 1)

1. Update `README.md` to remove PySide6 references
2. Update `.ai/ARCHITECTURE_CURRENT.md` to reflect Tauri-only
3. Update `.ai/RELEASE_AUDIT.md` to mark P0-1 as resolved
4. Update `.ai/DECISIONS.md` with this decision

### Phase 3: Verify Tauri Build (Day 1-2)

1. Run Tauri build locally
2. Verify installer generation
3. Test installer on Windows (if available)
4. Verify backend sidecar works
5. Verify Vue 3 SPA loads correctly

### Phase 4: Update CI/CD (Day 2)

1. Update GitHub workflows to only build Tauri
2. Remove PySide6 build steps
3. Update build scripts
4. Test CI/CD pipeline

### Phase 5: Final Verification (Day 2)

1. Run full test suite
2. Verify no PySide6 imports remain
3. Verify no PySide6 references in code
4. Verify Tauri bundle works end-to-end

---

## 6. ROLLBACK PLAN

If issues arise:

1. Restore `desktop-legacy/` to `desktop/`
2. Revert documentation changes
3. Revert CI/CD changes
4. Fall back to PySide6 if Tauri has critical issues

**Probability of rollback:** **LOW** (Tauri is already production-proven)

---

## 7. SUCCESS CRITERIA

- [ ] `desktop/` moved to `desktop-legacy/`
- [ ] No PySide6 imports in codebase
- [ ] Documentation updated to Tauri-only
- [ ] Tauri build succeeds locally
- [ ] Tauri installer generates correctly
- [ ] CI/CD pipeline updated
- [ ] All tests pass
- [ ] No regression in functionality

---

## 8. NEXT STEPS

**Immediate:**
1. Execute Phase 1 (Archive PySide6)
2. Execute Phase 2 (Update Documentation)
3. Execute Phase 3 (Verify Tauri Build)

**Following P0-1 completion:**
- P0-2: Implement cross-device sync manager
- P0-3: Add mobile/watch tests

---

**Decision:** OPTION A - KEEP TAURI, REMOVE PYSIDE6  
**Confidence:** HIGH (production evidence + architecture consistency)  
**Risk:** LOW (minimal changes, rollback available)  
**Effort:** LOW (1-2 days)
