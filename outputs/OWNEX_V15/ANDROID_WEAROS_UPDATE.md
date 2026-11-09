# ANDROID_WEAROS_UPDATE — OWNEX V15

**Date:** 2026-11-09 · **Status:** AUDITED — no installable Wear OS app exists

## 1. What actually exists

### Android app — REAL, build-verified

- `android/` — Capacitor 8 Android project, Gradle wrapper present,
  `app/build/intermediates/` contains prior debug+release build outputs
  (APK was built at some point — artifacts exist in-tree).
- `android/app/src/main/java/ai/rastro/app/MainActivity.java` — single
  activity, package `ai.rastro.app`.
- `capacitor.config.json` (repo root): `appId: "ownex.desktop.app"`,
  `webDir: "frontend/dist"`, push notifications + splash plugins.
- `android/app/build.gradle`: `applicationId "ai.rastore.app"`→ actually
  **`ai.rastro.app`**, `versionCode 1`, `versionName "1.0"`, release
  signing via env vars (`OWNEX_KEYSTORE_*`) — keystore NOT in repo ✅.
- **App ID mismatch (real bug):** `capacitor.config.json` declares
  `ownex.desktop.app` while `build.gradle` declares `ai.rastro.app`.
  Capacitor sync regenerates `capacitor.config.json` inside
  `android/app/src/main/assets/` — the two IDs disagree; whichever the
  last `npx cap sync` wrote wins at runtime. Must be reconciled before
  any release build (pick one — `ai.rastro.app` is the shipped one).
- Frontend mobile pages: `MobileApp.vue` (429 LOC), `MobileCompanionJarvis.vue`
  (730 LOC) — device-status cards, companion UI. Served inside the
  Capacitor WebView (`webDir: frontend/dist`).

### Wear OS — NOT an app. Backend bridge + mock UI only.

- `cores/wear_os/integration.py` (264 LOC): `WearOSIntegration` — a
  **server-side** module: file-backed queue of `WatchNotification`,
  `WatchApprovalRequest`, `WatchStatus`; publishes `WatchEventType`s on the
  event bus; auth via `verify_token`. It is the backend half of a watch
  companion — there is **no Wear OS module**:
  - No `android/wear/`, no wear-compose/tiltify Gradle module.
  - No watch APK, no `BUILD_WEAR_APK.md`, no Wear OS manifest.
  - `MobileCompanionJarvis.vue` shows a "⌚ Wear OS" card with a
    **Connect button backed by local component state** — it simulates
    connection status; it is not a paired-device client.
- Honest status: **EXPERIMENTAL / PLANNED** — backend notification +
  approval queue exists and is unit-testable; the watch app itself was
  never built. Old README's "Wear OS Completed" claim is false.

## 2. Contract gaps vs V15 §6 requirements

| Requirement | Status |
|---|---|
| Shared backend/auth/permissions | ✅ Capacitor WebView → same FastAPI; `verify_token` in wear bridge |
| Device auth, limited tokens, revocation | 🟡 `cores/auth/` exists; per-device token scoping for watch NOT verified |
| Notifications (critical alerts) | 🟡 backend queue exists; no push transport to a watch (FCM/wear data layer absent) |
| Approvals from watch | 🟡 `request_approval`/`respond_approval` API exists server-side; no watch UI to send them |
| Offline handling | ❌ none found |
| Audit | 🟡 event-bus published; dedicated audit trail not verified |
| No financial ops from watch | ✅ by absence — no such endpoints exposed to watch scope (verify consent scopes) |
| Release APK + checksums + manifest | ❌ no release keystore, no checksums, `versionCode 1` |

## 3. Blockers (environment, not code)

- No Android SDK / emulator in this environment → cannot run
  `./gradlew assembleDebug`, install, or exercise device flows.
- No Wear OS emulator/image → watch app can't even be scaffolded+verified.
- Release signing needs `OWNEX_KEYSTORE_*` env + a generated keystore
  (`android/generate_keystore.sh` exists).

## 4. Recommended next steps (ordered, honest)

1. **Fix appId mismatch** — decide `ai.rastro.app` vs `ownex.desktop.app`,
   align `capacitor.config.json` + `build.gradle`, re-run `npx cap sync`.
2. On a machine with Android SDK: `cd android && ./gradlew
   assembleDebug`, install on device, verify login + Work Bank +
   opportunities screens against a running backend.
3. Wear OS: scaffold a minimal Wear Compose companion (notifications +
   approve/deny) that talks to `cores/wear_os` endpoints — OR downgrade
   the claim permanently to "backend bridge only".
4. Cut `versionCode 2`+ with real versioning; generate keystore; document
   checksums in a release manifest.
5. Termux: verify CLI-only scope (`run.py`, `scripts/dev`) — do not claim
   full app support.

## 5. What V15 did NOT do

No APK built, no emulator run, no watch code written — blocked by missing
SDK. Claims in README reflect this: Android = BUILD_VERIFIED (prior build
artifacts + documented process), Wear OS = EXPERIMENTAL.
