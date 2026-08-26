# Desktop Legacy — PySide6 Qt Implementation

**Status:** ARCHIVED — Replaced by Tauri v2

**Archived Date:** 2026-08-26  
**Reason:** P0-1 Desktop Decision — Keep Tauri, Remove PySide6

---

## Why This Was Archived

This directory contains the PySide6 Qt desktop implementation that was **archived** in favor of the Tauri v2 implementation.

### Decision Rationale

1. **Production Evidence:** Tauri is the current production build, verified and deployed to OneDrive
2. **Architecture Consistency:** Tauri uses the same Vue 3 frontend as web/mobile
3. **Revenue Rule:** Zero regression risk, faster to release
4. **Effort:** Low effort (1-2 days) vs high effort (2-3 weeks) to migrate
5. **Technical Debt:** Tauri is modern, PySide6 is legacy

### Current Production Desktop

**Location:** `src-tauri/`

**Stack:**
- Tauri v2 (Rust + WebView2)
- Vue 3 SPA (same as web/mobile)
- Backend sidecar (PyInstaller ONEFILE)
- Windows installer (MSI/NSIS)

### This Legacy Stack

**Archived Stack:**
- PySide6 Qt (Python)
- Qt-based UI (different from web/mobile)
- Backend sidecar (same)
- No Windows installer (requires manual setup)

---

## If You Need to Restore

**Warning:** This is archived code. It may not work with the current backend.

To restore:

1. Move `desktop-legacy/` back to `desktop/`
2. Move `run-desktop` back to root
3. Update all documentation to reference PySide6
4. Test end-to-end
5. Consider updating CI/CD to build PySide6

---

## Migration Notes

This implementation had these features that may need attention in Tauri:

- ✅ Add Target functionality (ported to Tauri)
- ✅ Empty states handling (ported to Tauri)
- ✅ Tray icon (ported to Tauri)
- ✅ Backend sidecar (ported to Tauri)
- ✅ Auto-start (may need attention in Tauri)
- ✅ Notifications (may need attention in Tauri)

---

**Archived by:** Principal Software Architect  
**Reviewed by:** None  
**Next Review:** Never (unless critical issue with Tauri)
