"""Mobile Companion - Capacitor app for OWNEX mobile."""
// This is the Capacitor wrapper. All core functionality is the same.
// The app is a "Capacitor app" that has:
// - Same UI as the web view
// - Same backend API
// - Same storage
// - Additional mobile features (QR scan, push notifications, camera)

// Package: ownex-mobile
// Entry point: src/app.tsx
// Build: npm run build
// Publish: npx cap build

// Core exports:
// - @ownex/core (shared)
// - @ownex/secure (vault lock)
// - @ownex/mobile (device API)
// - @ownex/dispute (auto-dispute)

// Mobile features:
// - Camera for evidence capture (scanned images + OCR)
// - Push notifications for claim status
// - QR code scan for bounty discovery
// - Background sync (full-cycle every 15min)
// - Biometric login (Face ID / Touch ID)

// Mobile App Structure:
// ├── src/
// │   ├── components/          # UI components (mobile-first)
// │   ├── screens/             # Screens (home, bounty, dispute, settings)
// │   ├── services/            # API + storage
// │   ├── config/              # Config (capacitor, tokens)
// │   ├── providers/           # Context providers
// │   ├── utils/               # Helpers
// │   ├── types/               # Type definitions
// │   └── index.ts             # Entry point
// ├── capacitor.config.json
// ├── package.json
// ├── tsconfig.json
// └── ts-node.config.json

// Build command:
// npx cap build android
// npx cap build ios
// npx cap run android (dev)
// npx cap run ios (dev)

// Features:
// 1. Camera for capture (capture evidence image)
// 2. Biometric auth (FaceID/TouchID)
// 3. Push notifications (claim status)
// 4. QR code scanning (bounty discovery)
// 5. Background sync (full-cycle every 15 min)
// 6. NFC/Barcode (scan bounties)
// 7. Local cache (offline mode)
// 8. File attachment (media, receipts)
// 9. Voice notes (audio capture)

// Dependencies (added to package.json):
// - @capacitor/core (native bridge)
// - @capacitor/camera (camera)
// - @capacitor/communications (push)
// - @capacitor/utils (file picker)
// - qrcode-scanner (QR codes)
// - @react-native-async-storage/encrypted-storage (secure storage)
// - expo (optional: for React Native hybrid)
// - zxcrypt (AES-256 encryption)

// API integration:
// All endpoints same as web. Mobile uses:
// - /api/sandbox/submit (submission)
// - /api/evidence/claim (claim)
// - /api/dispute/open (dispute)
// - /api/obsidian/sync (sync)
// - /api/sandbox/state (state)
// - /api/vpn/info (VPN)
// - /api/scheduler (cron jobs)
// - /api/auto-dispute/list (list disputes)
// - /api/auto-dispute/status (check)