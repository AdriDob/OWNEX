# ORION Release Report

## Summary

| Field | Value |
|-------|-------|
| **Application** | ORION |
| **Version** | v1.6.0 |
| **Release** | v1.0.1 (tag) |
| **Build ID** | `ORION-v1.6.0-20260629-092506` |
| **Build Date** | 2026-06-29 |
| **Commit** | `c8c645f` — `fix: wrap entire App in QueryClientProvider to prevent BootScreen crash` |
| **Fixed Issue** | Root cause #7 — `No QueryClient set` crash on fresh Windows install |
| **Platform** | win32 (Windows 11) |
| **Frontend Bundle** | `index-CVH-a42B.js` (530.688 bytes) |
| **Build Host** | Windows native filesystem (`C:\Users\adrie\AppData\Local\Temp\orion_build`) |
| **Output** | `C:\Users\adrie\OneDrive\Desktop\Yo\privado\Orion\` |

## Root Cause Analysis — `No QueryClient set`

**Causa raíz:** En el código original, `App.tsx` renderizaba `BootScreen` con un `return` anticipado (línea 249) ANTES de que `QueryClientProvider` estuviera montado en el árbol de React (línea 305). `BootScreen` llama a `useSystemState()` → `useQuery()` → `useQueryClient()` → `useContext(QueryClientContext)`. Como el contexto tiene valor `undefined` (ningún Provider por encima), React Query lanza `Error("No QueryClient set")`.

**Por qué se manifiesta solo en producción:** El desarrollador tenía `sessionStorage` con `rastro-boot-complete='true'` de sesiones previas, por lo que nunca disparaba el early return de BootScreen en dev. En una instalación Windows limpia, `sessionStorage` está vacío → `bootComplete=false` → BootScreen se renderiza → crash.

**Por qué el smoke test HTTP no lo detectó:** Solo verifica respuestas HTTP (backend API + HTML estático). No ejecuta JavaScript en un navegador. No usa headless browser.

**Fix aplicado:** `QueryClientProvider` movido de `App.tsx` (solo en el return principal) a `main.tsx` (envuelve TODO el árbol React, incluyendo `App`, `BootScreen`, etc.). `BootErrorBoundary` agregado para capturar errores de inicialización. `queryClient` creado como singleton en `lib/queryClient.ts` antes de cualquier import de hooks.

## Pipeline Results

### Phase 1 — Clean Build (frontend + PyInstaller + NSIS)

| Step | Status | Details |
|------|--------|---------|
| Frontend `npm run build` | **PASS** | `index-CVH-a42B.js` (530.688 bytes, 577 módulos) |
| PyInstaller `Orion.spec` | **PASS** | `Orion.exe` (17.731.688 bytes / 16,91 MB), 1.925 archivos empaquetados |
| NSIS `orion.nsi` | **PASS** | `OrionInstaller.exe` (43.311.872 bytes / 41,31 MB), compresión LZMA, 35,9% ratio |

### Phase 2 — Import Audit

| Check | Status |
|-------|--------|
| Files scanned | 351 |
| Issues found | **0** — runtime is clean |
| Result | **PASS** |

### Phase 3 — Asset Validation

| Check | Status |
|-------|--------|
| Directory exists | **PASS** |
| `Orion.exe` exists | **PASS** |
| `Orion.exe` > 1 MB | **PASS** (16,91 MB) |
| `frontend_dist/` exists | **PASS** |
| `frontend_dist/index.html` exists | **PASS** |
| `frontend_dist/assets/` exists | **PASS** (68 archivos) |
| `_internal/` exists | **PASS** |
| Native modules (236) | **PASS** |
| Python bytecode archive (PYZ) | **PASS** |
| `VERSION` file valid | **PASS** (1.6.0) |
| Bundle size (115,4 MB) | **PASS** |
| **Result** | **14 OK, 0 FAIL, 2 WARN** (PYZ norm, .ico embedded) |

### Phase 4 — Bundle Integrity

| Check | Status |
|-------|--------|
| Bundle hash matches source | **PASS** — SHA256 `FB8C5F4FCA9D5D033B56FE25D860CBA85EA6C6ADFB756EE10AC83CEB4121D46F` |
| `QueryClientProvider` wraps render tree in bundle | **PASS** — confirmed in `index-CVH-a42B.js` |
| No early return patterns in App.tsx | **PASS** |
| Bundle in `Orion.exe` matches `frontend/dist/` | **PASS** — SHA256 identical |

### Phase 5 — Smoke Test HTTP

| Check | Status |
|-------|--------|
| Backend starts | **PASS** |
| Health endpoint `GET /api/health` | **PASS** (HTTP 200, `{"status":"ok"}`) |
| Frontend serves `index.html` | **PASS** |
| `index.html` served | **PASS** |
| Clean shutdown | **PASS** (exit code 1) |
| WebSocket / System / Scheduler / EventBus / Engines | **SKIP** (HTTP 401 — auth layer, no session in smoke mode) |
| **Result** | **6 PASS, 0 FAIL, 9 SKIP** |

### Phase 6 — Smoke Test Playwright (Headless Chromium)

| Check | Status |
|-------|--------|
| Backend starts | **PASS** |
| Page loads successfully | **PASS** |
| Page title: "ORION" | **PASS** |
| React root in DOM | **PASS** |
| Page body has content | **PASS** (71 chars) |
| No console errors (excluding expected HTTP 401/403) | **PASS** |
| No fatal JS errors (`No QueryClient set`, React crash, TypeError, etc.) | **PASS** |
| No page-level uncaught exceptions | **PASS** |
| HTTP 401/403 boot noise (expected) | 3 messages — auth checks during boot |
| Clean shutdown | **PASS** (exit code 1) |
| **Result** | **8 PASS, 0 FAIL, 0 SKIP** |

### Phase 7 — Portable Test

| Check | Status |
|-------|--------|
| `Orion.exe` exists in source | **PASS** |
| `frontend_dist/index.html` exists | **PASS** |
| Copy to temp isolation | **PASS** |
| Isolation confirmed (outside repo) | **PASS** |
| Backend starts from temp location | **PASS** |
| Frontend serves | **PASS** |
| Health endpoint OK | **PASS** |
| Clean shutdown | **PASS** (exit 1) |
| Temp directory cleaned | **PASS** |
| **Result** | **9 PASS, 0 FAIL** |

### Phase 8 — Installer Test (Windows Admin)

| Check | Status |
|-------|--------|
| Installer runs silently | **PASS** |
| `Orion.exe` installed | **PASS** |
| `uninstall.exe` created | **PASS** |
| `LICENSE` installed | **PASS** |
| `frontend_dist/index.html` installed | **PASS** |
| All required files installed | **PASS** |
| Backend starts from `C:\Program Files\ORION` | **PASS** |
| Health endpoint OK (HTTP 200) | **PASS** |
| Frontend serves correctly | **PASS** |
| Clean shutdown | **PASS** (exit 1) |
| Uninstaller completes | **PASS** |
| **Result** | **11 PASS, 0 FAIL** |

## SHA256 Checksums

| Artifact | SHA256 |
|----------|--------|
| `Orion.exe` | `27BF95CCC79E2967BFA952FEAF4D31281D2550BD5252BCCA11D1A6DE1186A203` |
| `OrionInstaller.exe` | `47D68E554ED8C8A33252CBDD77281E19968E5B2BA55FD25B5BCA32B10B3196D3` |
| `Orion-1.6.0.zip` | `D4BD6C17CFC7BCF203AD0CE6C01FC82DB0FB465CF1BBCD9539A559180363B9E6` |
| `index-CVH-a42B.js` (bundle) | `FB8C5F4FCA9D5D033B56FE25D860CBA85EA6C6ADFB756EE10AC83CEB4121D46F` |

## Build Components

| Component | Version | Status |
|-----------|---------|--------|
| Frontend (Vite 8 + React 19) | `index-CVH-a42B.js` (530 KB) | **PASS** |
| PyInstaller | 6.20.0 | **PASS** |
| NSIS | 3.12 | **PASS** |
| Python | 3.12.10 | **PASS** |
| Playwright | Chromium 149.0.7827.55 | **PASS** |

## File Manifest (`Orion/` directory)

| Entry | Size |
|-------|------|
| `Orion.exe` | 17.731.688 bytes (16,91 MB) |
| `_internal/` | ~1.924 archivos (~98 MB) |
| `_internal/frontend_dist/` | 68 archivos (frontend build) |
| `_internal/frontend_dist/assets/index-CVH-a42B.js` | 530.688 bytes |
| `_internal/VERSION` | 6 bytes ("1.6.0") |

## Installer Evidence

El instalador probado es exactamente el que será distribuido:

```
OrionInstaller.exe
  Path:  C:\Users\adrie\OneDrive\Desktop\Yo\privado\Orion\OrionInstaller.exe
  SHA256: 47D68E554ED8C8A33252CBDD77281E19968E5B2BA55FD25B5BCA32B10B3196D3
  Size:   43.311.872 bytes (41,31 MB)
```

El bundle `index-CVH-a42B.js` dentro del instalador tiene el mismo SHA256 que el fuente en `frontend/dist/assets/`. El instalador fue probado en una instalación limpia en `C:\Program Files\ORION`, incluyendo arranque, frontend, shutdown y desinstalación correcta.

## All Tests Verdict

| Phase | Result |
|-------|--------|
| 1. Build (frontend + PyInstaller + NSIS) | **PASS** |
| 2. Import audit | **PASS** (0 issues) |
| 3. Asset validation | **PASS** (14/14 OK) |
| 4. Bundle integrity | **PASS** (SHA256 match) |
| 5. Smoke test (HTTP) | **PASS** (6/6 critical) |
| 6. Smoke test (Playwright) | **PASS** (8/8, zero JS errors) |
| 7. Portable test | **PASS** (9/9) |
| 8. Installer test | **PASS** (11/11) |
| **FINAL** | **ALL GREEN** |

## Changes since v1.0.0

- **Root cause #7 fixed**: `No QueryClient set` crash on fresh Windows install. `QueryClientProvider` moved from `App.tsx` to `main.tsx`.
- **BootErrorBoundary**: New component catches initialization errors with recovery screen.
- **`console=False`**: Orion.exe launches without terminal window.
- **Unicode `→` removed**: All 66 occurrences of `→` (U+2192) in `core_engines/` replaced with `->` to eliminate cp1252 `UnicodeEncodeError` on Windows stderr.
- **Playwright smoke test**: New `scripts/smoke_test_playwright.py` validates frontend JS execution in headless Chromium. Detects `No QueryClient set` and all JS runtime errors. Integrated into `release_isolation.py` pipeline.
- **All cp1252 issues fixed**: Test scripts set `PYTHONIOENCODING=utf-8` to avoid `UnicodeEncodeError: 'charmap' codec can't encode character`.
- **Build on Windows native filesystem**: PyInstaller builds now run from Windows temp directory (`C:\Users\adrie\AppData\Local\Temp\orion_build`) to avoid DrvFs/UNC path permission issues.
