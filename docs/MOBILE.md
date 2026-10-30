# OWNEX Mobile — Android Companion

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

OWNEX Mobile is the Android companion app built with **Capacitor** wrapping the Vue 3 frontend. It provides a native Android experience with push notifications, biometric authentication, and Wear OS integration.

## Architecture

```
OWNEX Mobile (Android)
├── Capacitor Shell (ai.rastro.app)
│   ├── WebView loads `frontend/dist` (https://capacitor.localhost)
│   ├── Native plugins via Capacitor
│   └── Native Android module for Wear OS
├── Wear OS Module (ai.rastro.watch)
│   ├── Standalone Wear OS app
│   ├── Data Layer API for phone↔watch sync
│   └── Ongoing Activity for persistent notifications
└── Backend Communication
    ├── REST API to `https://<desktop-ip>:8000/api/`
    ├── WebSocket for real-time updates
    └── FCM for push notifications
```

## Android App (`android/`)

### Configuration

**Package**: `ai.rastro.app` (unified namespace — resolves previous `ai.rastro/catseye/CATEYE` conflict)

**build.gradle** (key settings):
```gradle
namespace = "ai.rastro.app"
applicationId "ai.rastro.app"
minSdkVersion 23 (Android 6.0)
targetSdkVersion 34 (Android 14)
compileSdkVersion 34
compileOptions { sourceCompatibility = targetCompatibility = '17' }
```

**Signing** (release):
- Keystore: `ownex-release.jks` (or env var `OWNEX_KEYSTORE_PATH`)
- Alias: `ownex` (or env var `OWNEX_KEY_ALIAS`)
- Passwords via env vars: `OWNEX_KEYSTORE_PASSWORD`, `OWNEX_KEY_PASSWORD`

### Capacitor Configuration (`capacitor.config.json`)

```json
{
  "appId": "ai.rastro.app",
  "appName": "CATEYE",
  "webDir": "frontend/dist",
  "server": {
    "androidScheme": "https",
    "cleartext": false
  },
  "android": {
    "backgroundColor": "#0d0f17"
  },
  "plugins": {
    "PushNotifications": {
      "presentationOptions": ["badge", "sound", "alert"]
    },
    "SplashScreen": {
      "backgroundColor": "#0d0f17",
      "showSpinner": false
    }
  }
}
```

### Key Plugins

| Plugin | Purpose |
|--------|---------|
| `@capacitor/push-notifications` | FCM push notifications |
| `@capacitor/biometric-auth` | Fingerprint/Face ID for approvals |
| `@capacitor/filesystem` | Local persistence |
| `@capacitor/share` | Share actions |
| `@capacitor/background-runner` | Background sync |
| `@capacitor-community/speech-recognition` | Voice input (v7.0.1) |

### Android Manifest Permissions

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.BLUETOOTH_ADVERTISE" />
<uses-permission android:name="android.permission.BODY_SENSORS" />
```

### Voice Integration (`MobileCompanionJarvis.vue`)

- **STT**: `@capacitor-community/speech-recognition` (native Android)
- **TTS**: Backend Piper → Web Speech API fallback
- **Wake Word**: Not implemented (manual tap to record)

### Push Notifications (FCM)

1. **Token Registration**: On app start, registers FCM token with backend
2. **Topics**: Subscribes to `findings`, `approvals`, `alerts`, `system`
3. **Payload**: Custom data routes to specific screens
4. **Background**: `BackgroundRunner` handles silent pushes

### Biometric Authentication

```typescript
// Used for: approvals, sensitive actions, app unlock
await BiometricAuth.authenticate({
  reason: 'Authenticate to approve action',
  fallbackTitle: 'Use PIN',
  cancelTitle: 'Cancel',
})
```

## Backend Communication

### API Base URL
- **Development**: `http://10.0.2.2:8000` (Android emulator → host)
- **Production**: `https://<desktop-ip>:8000` (mTLS in future)

### Key Endpoints Used

| Feature | Endpoint |
|---------|----------|
| Health Check | `GET /api/health` |
| Dashboard Data | `GET /api/ownex/dashboard` |
| Mission Status | `GET /api/mission/status` |
| Activity Feed | `GET /api/activity` |
| Opportunities | `GET /api/opportunities` |
| Work Bank | `GET /api/direct-work/workbank` |
| Approvals | `GET /api/approvals/pending` |
| Wear OS Status | `GET /api/wear-os/status` |
| Wear OS Notifications | `GET /api/wear-os/notifications` |
| Wear OS Approvals | `GET /api/wear-os/approvals/pending` |

### WebSocket (Real-time)
- **Endpoint**: `wss://<host>/api/ws/terminal` (also used for live updates)
- **Reconnection**: Exponential backoff (1s, 2s, 4s, 8s, max 30s)

## Mobile-Specific Features

### 1. Quick Actions (Home Screen)
- **Start Validation Cycle** → Triggers `/api/hunt/start`
- **Approve Pending** → Opens approvals list
- **Check Capital** → Opens Capital tab
- **View Alerts** → Notification center

### 2. Offline Support (Partial)
- **Cached Reads**: Last successful API responses cached via `localStorage` + IndexedDB
- **Queued Writes**: Mutations (approvals, actions) queued in `outbox` table
- **Sync on Reconnect**: Background runner flushes queue on network restore
- **Not Supported**: Full offline DB, background sync without app open

### 3. Background Behavior
- **FCM**: High-priority messages wake app for critical alerts
- **Background Runner**: Periodic sync (configurable, default 15min)
- **Wake Lock**: Held during active sync/approval processing

## Build & Release

### Debug APK
```bash
cd android
./gradlew assembleDebug
# Output: android/app/build/outputs/apk/debug/app-debug.apk (~5MB)
```

### Release AAB/APK
```bash
cd android
# Requires env vars:
#   OWNEX_KEYSTORE_PATH
#   OWNEX_KEYSTORE_PASSWORD
#   OWNEX_KEY_ALIAS
#   OWNEX_KEY_PASSWORD
./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

### Signing (Release)
Env vars (CI/CD):
```bash
OWNEX_KEYSTORE_PATH=/path/to/ownex-release.jks
OWNEX_KEYSTORE_PASSWORD=***
OWNEX_KEY_ALIAS=ownex
OWNEX_KEY_PASSWORD=***
```

### Keystore Generation (One-time)
```bash
./generate_keystore.sh
# Creates ownex-release.jks with 25-year validity
```

## Device Pairing

### Desktop ↔ Mobile
1. Desktop shows QR code with `ws://<ip>:8000/pair?token=<jwt>`
2. Mobile scans QR → Opens WebSocket to desktop
3. Exchange device IDs, capabilities, permissions
4. Persisted in `localStorage` (mobile) + `~/.ownex/devices.json` (desktop)

### Mobile ↔ Watch
1. Standard Wear OS pairing (system Settings)
2. Data Layer API auto-syncs notifications/approvals
3. Companion app shows connection status

## Troubleshooting

| Issue | Solution |
|-------|----------|
| App won't connect to desktop | Check desktop IP, firewall port 8000, same network |
| Push notifications not working | Verify `google-services.json`, FCM token registered |
| Biometric auth fails | Check Android BiometricPrompt compatibility, fallback to PIN |
| WebSocket disconnects | Check network, backend `/api/ws/terminal` health |
| Wear OS not syncing | Re-pair watch, check Data Layer API permissions |
| FCM token not registered | Ensure `google-services.json` in `android/app/`, check logcat |

## Known Limitations

| Limitation | Status |
|------------|--------|
| Full offline DB | ❌ Not implemented |
| Background sync without app open | ⚠️ Partial (FCM only) |
| Voice wake word | ❌ Manual tap required |
| mTLS for API | 🔄 Planned |
| Widget support | ❌ Not implemented |

---

*Document generated from codebase. Last verified: 2026-08-27*