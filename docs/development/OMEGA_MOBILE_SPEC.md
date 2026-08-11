# OMEGA Mobile — Companion App Development Specification

> **Status**: Active Development (Expo/React Native skeleton exists at `omega/`)
> **Platforms**: iOS (primary), Android (Capacitor), Wear OS (Compose)
> **Backend**: WebSocket to `ws://localhost:8000/api/ws/terminal` + REST API
> **Design**: Tesla dark, pure black #05060A, Space Grotesk/Inter/JetBrains Mono

---

## 1. Product Vision

OMEGA is the **mobile command center** for OWNEX. It answers one question every morning:

> **"What is the single highest-EV action I can take today, and what do I need to do to execute it?"**

Not a dashboard. Not a monitoring tool. A **decision companion** that surfaces the next best action with full context, lets you approve/execute from your pocket, and syncs seamlessly with the desktop Mission Control.

---

## 2. Current State

### Existing Codebase (`omega/`)
```
omega/
├── app.json                    # Expo config, bundleId: com.ownex.omega
├── package.json                # Expo 51, React Native 0.74, TypeScript 5.3
├── tsconfig.json
├── src/
│   ├── App.tsx                 # Root with providers
│   ├── navigation/
│   │   └── AppNavigator.tsx    # Bottom tabs + stack navigation
│   ├── screens/
│   │   └── DashboardScreen.tsx # Placeholder
│   ├── services/
│   │   ├── api.ts              # REST client (axios)
│   │   ├── socket.ts           # WebSocket client
│   │   └── notifications.ts    # Expo notifications
│   └── stores/
│       └── useStore.ts         # Zustand store
└── assets/                     # Icons, splash
```

### Working Features
- ✅ Expo project compiles
- ✅ Navigation structure (5 tabs)
- ✅ API service with token auth
- ✅ WebSocket service (reconnection, heartbeat)
- ✅ Push notification setup (Expo)
- ✅ Zustand store with persistence
- ✅ Dark theme (black background)

### Missing (Priority Order)
1. **Real Dashboard** — TodayView with next action + metrics
2. **Opportunities List** — Swipeable cards with actions
3. **MERLIN Chat** — Voice + text, streaming responses
4. **Agent Fleet** — Status grid with tap-to-expand
5. **Push Notifications** — Rich actions, deep linking
6. **Apple Watch App** — Compose for Wear OS
7. **Biometric Auth** — FaceID/TouchID + Secure Enclave
7. **Offline Queue** — Mutation queue with sync

---

## 3. Architecture

### Tech Stack
| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Expo (managed) | 51 |
| Runtime | React Native | 0.74 |
| Language | TypeScript | 5.3 |
| Navigation | React Navigation | 6.x |
| State | Zustand | 4.x |
| API | Axios + TanStack Query | 5.x |
| WebSocket | react-native-websocket | latest |
| Notifications | Expo Notifications | latest |
| Secure Storage | Expo SecureStore | latest |
| Biometrics | Expo LocalAuthentication | latest |
| Charts | Victory Native | latest |
| Icons | Lucide React Native | latest |
| Fonts | Space Grotesk, Inter, JetBrains Mono | local |

### Data Flow
```
┌─────────────┐     REST/WS      ┌─────────────┐
│  OMEGA App  │ ◄──────────────► │  OWNEX API  │
│  (Expo RN)  │   ws://:8000     │  (FastAPI)  │
└─────────────┘                  └─────────────┘
       │                                │
       ▼                                ▼
┌─────────────┐                  ┌─────────────┐
│ SecureStore │                  │  PostgreSQL │
│ (tokens,    │                  │  + Redis    │
│  biometrics)│                  │  (prod)     │
└─────────────┘                  └─────────────┘
       │
       ▼
┌─────────────┐
│  Watch App  │  (Compose, BLE/WS sync)
└─────────────┘
```

### Offline-First Strategy
- All mutations (approve, defer, execute) go to **local queue** first
- Queue persisted in AsyncStorage + SecureStore
- Background sync when online (exponential backoff)
- Optimistic UI updates — immediate feedback
- Conflict resolution: server wins, local replay

---

## 4. Screen Specifications

### 4.1 Home / TodayView (Primary Screen)

**Route**: `/(tabs)/home`
**Purpose**: Answer "What do I do today?"

```
┌─────────────────────────────────────┐
│  ● ONLINE          $2,400 potential │  ← System health + top metric
├─────────────────────────────────────┤
│  TODAY                                │  ← Section header
│  ┌─────────────────────────────────┐ │
│  │ 🎯 Execute Top Pick            │ │  ← Primary CTA (full width)
│  │ OpenAI Bug Bounty — $1,200     │ │
│  │ 2.3h prep · 78% success · 83%  │ │
│  │ [Prepare] [Explain] [Defer]    │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  QUICK METRICS                       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ 3    │ │ 78%  │ │ 83%  │ │ 2.3h │ │
│  │Opps  │ │Accept│ │Auto  │ │ Prep │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ │
├─────────────────────────────────────┤
│  AGENT FLEET          [View All]     │
│  🔴 Security  ● Working  ████░░ 65%  │
│  🟢 Coding    ○ Idle     ░░░░░░  0%  │
│  🔵 QA        ● Complete ██████ 100% │
└─────────────────────────────────────┘
```

**Data Sources**:
- `GET /direct-work/daily-companion` → briefing + top pick
- `GET /direct-work/workbank` → opportunities summary
- `GET /api/mission/status` → agent fleet

**Interactions**:
- Tap "Execute Top Pick" → navigates to Opportunity Detail
- Tap agent → expands to Agent Detail
- Pull-to-refresh → re-fetches daily-companion
- Long-press CTA → "Explain" modal (MERLIN reasoning)

---

### 4.2 Opportunities List

**Route**: `/(tabs)/opportunities`
**Purpose**: Browse, filter, act on work bank

```
┌─────────────────────────────────────┐
│  🔍 Search opportunities...        │  ← Search bar (cyan focus)
├─────────────────────────────────────┤
│  Filters: [All] [Ready] [Need Acc] │  ← Segmented control
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐ │
│  │ 🏷️ H1    $1,200  2.3h  ████░░ │ │  ← Card: platform, reward, effort
│  │ OpenAI — IDOR in API v2         │ │
│  │ [Prepare] [Defer] [Dismiss]     │ │  ← Swipe actions revealed
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ 🏷️ BC    $800   1.5h  ██████  │ │
│  │ Stripe — XSS in Checkout        │ │
│  │ [Prepare] [Defer] [Dismiss]     │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Swipe Actions** (left→right):
- **Prepare** (cyan) → Generates delivery package, navigates to Detail
- **Defer** (gray) → Moves to "Later" section, schedules reminder
- **Dismiss** (orange) → Marks rejected, records reason

**Data**: `POST /direct-work/workbank/cycle` (trigger), `GET /direct-work/workbank` (list)

---

### 4.3 Opportunity Detail

**Route**: `/opportunities/:id`
**Purpose**: Full context + execution

```
┌─────────────────────────────────────┐
│  ←  🏷️ H1    $1,200  2.3h  78%    │
├─────────────────────────────────────┤
│  OpenAI Bug Bounty Program          │
│  IDOR in API v2 — User Data Access  │
│                                     │
│  ┌─ EXECUTION PLAN ────────────────┐ │
│  │ 1. Prepare → Generate package   │ │
│  │ 2. Review  → Verify evidence    │ │
│  │ 3. Submit  → H1 platform        │ │
│  │ 4. Track   → Monitor status     │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ SKILL GAP ────────────────────┐ │
│  │ GraphQL mutation crafting       │ │
│  │ 45 min learning → 85% ready    │ │
│  │ [Open Learning Plan]           │ │
│  └────────────────────────────────┘ │
│                                     │
│  [EXECUTE NOW]        [DEFER]       │  ← Primary + secondary
└─────────────────────────────────────┘
```

**Data**: `POST /direct-work/plan/opportunity` → full plan with roadmap

---

### 4.4 MERLIN Chat

**Route**: `/(tabs)/merlin`
**Purpose**: Voice-first AI assistant

```
┌─────────────────────────────────────┐
│  MERLIN          ● SYSTEM ONLINE    │  ← Emerald pulsing dot
├─────────────────────────────────────┤
│                                     │
│  ┌────────────────────────────────┐ │  ← MERLIN message (cyan bubble)
│  │ Top pick today: OpenAI H1       │ │
│  │ $1,200 EV, 2.3h prep. Want me  │ │
│  │ to prepare the package?         │ │
│  └────────────────────────────────┘ │
│                    ┌──────────────┐ │  ← User message (emerald bubble)
│                    │ Yes, prepare  │ │
│                    └──────────────┘ │
│                                     │
│  ┌────────────────────────────────┐ │  ← Streaming indicator
│  │ Preparing package... ████░░     │ │
│  └────────────────────────────────┘ │
├─────────────────────────────────────┤
│  🎤 [Hold to talk]   💬 Type...    │  ← Voice + text input
└─────────────────────────────────────┘
```

**Features**:
- **Voice**: Hold button → WebSocket audio stream → STT → LLM → TTS response
- **Streaming**: Token-by-token response rendering
- **Context**: Auto-includes daily briefing, work bank, agent status
- **Actions**: Buttons in messages → deep link to screens
- **History**: Persisted in SecureStore, searchable

**Endpoints**:
- `POST /api/voice/assistant` (voice + text)
- `WS /api/ws/merlin` (streaming)
- `GET /api/merlin/history` (pagination)

---

### 4.5 Agent Fleet

**Route**: `/(tabs)/agents`
**Purpose**: Monitor + control autonomous agents

```
┌─────────────────────────────────────┐
│  AGENT FLEET              8/12 OK   │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐ │
│  │ 🔴 Security      ● WORKING      │ │
│  │ Scanning targets... 65%         │ │
│  │ [Pause] [View Logs] [Config]    │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ 🟢 Coding        ○ IDLE         │ │
│  │ Awaiting task...                │ │
│  │ [Assign] [View Logs] [Config]   │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ 🔵 QA            ● COMPLETE     │ │
│  │ 47 tests passed                 │ │
│  │ [View Report] [Rerun]           │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Tap Agent → Detail Modal**:
- Full conversation log
- Decision history
- Current task breakdown
- Config: model, temperature, autonomy level
- Kill switch (emergency stop)

**Data**: `GET /api/mission/status` → agent fleet status
**Control**: `POST /api/agents/:id/control` (pause/resume/configure)

---

### 4.6 Settings

**Route**: `/(tabs)/settings`
**Tabs**: Account, AI Providers, Notifications, Appearance, Advanced

```
┌─────────────────────────────────────┐
│  SETTINGS                           │
├─────────────────────────────────────┤
│  ACCOUNT                    [👤]    │
│  ┌─────────────────────────────────┐ │
│  │ Biometric Auth          [ON] ●  │ │  ← FaceID/TouchID toggle
│  │ Session Timeout         30 min  │ │
│  │ Auto-lock on Background  [ON] ● │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  AI PROVIDERS                 [🤖]  │
│  ┌─────────────────────────────────┐ │
│  │ Primary: OAR Router (Local)     │ │
│  │ Fallback: FCC Proxy (Claude)    │ │
│  │ Premium: OpenRouter (Optional)  │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  NOTIFICATIONS                [🔔]  │
│  ┌─────────────────────────────────┐ │
│  │ High-EV Opportunities    [ON] ● │ │
│  │ Agent Completion         [ON] ● │ │
│  │ MERLIN Replies           [ON] ● │ │
│  │ Critical Alerts          [ON] ● │ │
│  │ Quiet Hours: 22:00-07:00       │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│  APPEARANCE                   [🎨]  │
│  ┌─────────────────────────────────┐ │
│  │ Theme: Dark (Fixed)             │ │
│  │ Font Size: Medium [−] [+]       │ │
│  │ Reduced Motion: [OFF]           │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## 5. Apple Watch App (Wear OS Companion)

### Platform: watchOS (SwiftUI) / Wear OS (Compose)
**Bundle ID**: `com.ownex.omega.watch`

### Watch Face Complications
| Slot | Complication | Data Source |
|------|--------------|-------------|
| Top Leading | System Health | `GET /api/system/health` |
| Top Trailing | Next Action Count | `GET /direct-work/daily-companion` |
| Bottom | MERLIN Status | WebSocket event |
| Center (Modular) | Execute Button | Custom action |

### Watch App Screens

**1. Main (Glance)**
```
┌─────────────────┐
│  ● ONLINE  3 🎯 │  ← Health + opportunity count
│                 │
│  EXECUTE TOP    │  ← Full-width button (tap → haptic)
│  $1,200 · 2.3h  │
│                 │
│  MERLIN: READY  │
└─────────────────┘
```

**2. Opportunities (Scroll)**
```
┌─────────────────┐
│  1. OpenAI H1   │
│  $1,200 · 2.3h  │
│  [PREP] [SKIP]  │
├─────────────────┤
│  2. Stripe BC   │
│  $800 · 1.5h    │
│  [PREP] [SKIP]  │
└─────────────────┘
```

**3. Agent Status**
```
┌─────────────────┐
│  🔴 Security 65%│
│  🟢 Coding  0%  │
│  🔵 QA     100% │
│  🟡 Debug   0%  │
└─────────────────┘
```

**4. MERLIN Micro**
```
┌─────────────────┐
│  "Package ready │
│   for review"   │
│                 │
│  [OK] [LATER]   │
└─────────────────┘
```

### Sync Protocol
- **Phone → Watch**: BLE (WatchConnectivity) for instant actions
- **Watch → Phone**: Actions queued, synced via WCSession
- **Background**: App refresh every 15 min (budgeted)
- **Complications**: Timeline entries updated every 30 min

---

## 6. Native Capabilities

### 6.1 Biometric Authentication
```typescript
// Expo LocalAuthentication
import * as LocalAuthentication from 'expo-local-authentication';

async function authenticate(): Promise<boolean> {
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const isEnrolled = await LocalAuthentication.isEnrolledAsync();
  
  if (!hasHardware || !isEnrolled) return false;
  
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock OMEGA',
    fallbackLabel: 'Use Passcode',
    cancelLabel: 'Cancel',
  });
  
  return result.success;
}
```

**Storage**: Tokens in **SecureStore** (iOS Keychain / Android Keystore)
- Access controlled by biometric policy
- Auto-lock on app background > 30s

### 6.2 Push Notifications
```typescript
// Expo Notifications + APNs/FCM
import * as Notifications from 'expo-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// Rich notification categories
Notifications.setNotificationCategoryAsync('OPPORTUNITY_READY', [
  { identifier: 'PREPARE', buttonTitle: 'Prepare', options: { opensAppToForeground: true } },
  { identifier: 'DISMISS', buttonTitle: 'Dismiss', options: { isDestructive: true } },
]);
```

**Payload Structure**:
```json
{
  "aps": { "alert": { "title": "High-EV Opportunity", "body": "OpenAI H1 — $1,200" }, "category": "OPPORTUNITY_READY" },
  "data": { "type": "opportunity", "id": "opp_abc123", "action": "prepare" },
  "thread-id": "opportunities"
}
```

### 6.3 Voice Interface
```typescript
// WebSocket audio streaming
const ws = new WebSocket('ws://localhost:8000/api/ws/voice');

// Audio capture (React Native)
const audio = await AudioRecorder.start({
  sampleRate: 16000,
  channels: 1,
  format: 'wav',
});

// Stream chunks
audio.addListener('data', chunk => ws.send(chunk));

// Receive TTS response
ws.onmessage = event => {
  const audio = new Audio('data:audio/wav;base64,' + event.data);
  audio.play();
};
```

---

## 7. Data Models (TypeScript)

```typescript
// types/index.ts

interface Opportunity {
  id: string;
  platform: 'hackerone' | 'bugcrowd' | 'intigriti' | 'yeswehack' | 'synack';
  title: string;
  reward: number;
  effortHours: number;
  evScore: number;           // 0-1
  acceptanceProbability: number;
  automationPercent: number;
  skillGap: SkillGap[];
  status: 'ready' | 'need_access' | 'preparing' | 'delivered';
  createdAt: string;
  executionPlan: ExecutionPlan;
}

interface ExecutionPlan {
  steps: PlanStep[];
  humanMinutes: number;
  automationPercent: number;
  expectedValue: number;
  roadmap: RoadmapStep[];
}

interface SkillGap {
  skill: string;
  currentLevel: number;    // 0-1
  requiredLevel: number;
  learningPlan: LearningStep[];
}

interface AgentStatus {
  id: string;
  name: string;
  type: 'security' | 'coding' | 'qa' | 'debug' | 'docs' | 'research' | 
        'product' | 'revenue' | 'automation' | 'infra' | 'evolution' | 'orchestrator';
  status: 'idle' | 'working' | 'complete' | 'error';
  currentTask: string | null;
  progress: number;        // 0-1
  lastUpdate: string;
}

interface DailyCompanion {
  generatedAt: string;
  system: { score: number; status: string };
  personal: { pendingTasks: number; deliveredToday: number };
  market: { opportunitiesAnalyzed: number; topSources: Source[] };
  focus: { stop: string[]; automate: string[]; delegate: string[]; improve: string[] };
  briefing: string;
  projection: { monthlyCurve: number[]; monthsToTarget: number };
}
```

---

## 8. API Integration

### REST Client (Axios + TanStack Query)
```typescript
// services/api.ts
import axios from 'axios';
import { QueryClient } from '@tanstack/react-query';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
});

api.interceptors.request.use(async config => {
  const token = await SecureStore.getItemAsync('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30000, retry: 1, refetchOnWindowFocus: true },
  },
});

// Hooks
export function useDailyCompanion() {
  return useQuery({ queryKey: ['daily-companion'], queryFn: () => api.post('/direct-work/daily-companion') });
}

export function useWorkBank() {
  return useQuery({ queryKey: ['workbank'], queryFn: () => api.get('/direct-work/workbank') });
}

export function useAgentFleet() {
  return useQuery({ queryKey: ['agent-fleet'], queryFn: () => api.get('/api/mission/status'), refetchInterval: 10000 });
}
```

### WebSocket Service
```typescript
// services/socket.ts
type WSMessage = 
  | { type: 'agent:status'; payload: AgentStatus }
  | { type: 'opportunity:ready'; payload: Opportunity }
  | { type: 'merlin:reply'; payload: { text: string; audio?: string } }
  | { type: 'system:alert'; payload: { level: 'info'|'warning'|'critical'; message: string } };

class SocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnect = 10;
  private listeners: Map<string, Set<(msg: WSMessage) => void>> = new Map();

  connect() {
    this.ws = new WebSocket('ws://localhost:8000/api/ws/terminal');
    this.ws.onopen = () => this.reconnectAttempts = 0;
    this.ws.onmessage = e => this.handleMessage(JSON.parse(e.data));
    this.ws.onclose = () => this.scheduleReconnect();
  }

  private handleMessage(msg: WSMessage) {
    this.listeners.get(msg.type)?.forEach(cb => cb(msg));
  }

  subscribe(type: string, cb: (msg: WSMessage) => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(cb);
    return () => this.listeners.get(type)!.delete(cb);
  }
}
```

---

## 9. Build & Deploy

### Development
```bash
cd omega
npm install
npm run dev          # Expo dev server
npm run ios          # iOS simulator
npm run android      # Android emulator
```

### Production (EAS Build)
```bash
# eas.json configured for:
# - iOS: App Store distribution
# - Android: Play Store (AAB)
# - Watch: separate target

eas build --platform ios --profile production
eas build --platform android --profile production
eas submit --platform ios
eas submit --platform android
```

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `EXPO_PUBLIC_API_URL` | Backend URL (e.g., `https://api.ownex.dev`) | Yes |
| `EXPO_PUBLIC_WS_URL` | WebSocket URL | Yes |
| `EXPO_PUBLIC_SENTRY_DSN` | Error tracking | No |
| `APPLE_TEAM_ID` | iOS signing | iOS only |
| `GOOGLE_SERVICES_JSON` | FCM config | Android only |

---

## 10. Testing Strategy

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Unit | Jest + React Native Testing Library | 80% |
| Integration | Detox (iOS/Android) | Critical flows |
| E2E | Maestro | User journeys |
| Visual | Chromatic (Storybook) | UI components |
| Performance | Flipper + React DevTools | 60fps, <100ms TTI |

**Critical Test Scenarios**:
1. Cold start → TodayView loads < 2s
2. Offline queue → mutations persist → sync on reconnect
3. Push notification → deep link → correct screen
4. Voice input → STT → LLM → TTS < 3s latency
5. Watch action → phone sync < 5s
5. Biometric unlock → token refresh

---

## 11. Roadmap

| Phase | Timeline | Deliverable |
|-------|----------|-------------|
| **M1** | Week 1-2 | TodayView + Opportunities + MERLIN text chat |
| **M2** | Week 3 | Agent Fleet + Voice + Push notifications |
| **M3** | Week 4 | Apple Watch app + Biometric auth |
| **M4** | Week 5 | Offline queue + Background sync + EAS build |
| **M5** | Week 6 | TestFlight / Play Console internal testing |
| **M6** | Week 7 | Production release + App Store / Play Store |

---

## 12. Design Handoff

### Figma File Structure
```
OWNEX OMEGA Mobile/
├── 01 - Design System
│   ├── Colors (dark/light tokens)
│   ├── Typography (Space Grotesk/Inter/JetBrains)
│   ├── Spacing (8px grid)
│   ├── Components (buttons, cards, inputs, badges)
│   └── Icons (Lucide + custom OWNEX)
├── 02 - Screens (Dark)
│   ├── Home / TodayView
│   ├── Opportunities List
│   ├── Opportunity Detail
│   ├── MERLIN Chat
│   ├── Agent Fleet
│   └── Settings
├── 03 - Screens (Light) — mirrors of Dark
├── 04 - Watch App
│   ├── Complications
│   ├── Main Glance
│   ├── Opportunities
│   ├── Agents
│   └── MERLIN Micro
├── 05 - States
│   ├── Loading skeletons
│   ├── Empty states
│   ├── Error states
│   ├── Offline banner
│   └── Success toasts
└── 06 - Prototypes
    ├── Home → Detail flow
    ├── Voice interaction
    ├── Swipe actions
    └── Watch → Phone handoff
```

### Asset Export Specs
| Asset | Format | Sizes |
|-------|--------|-------|
| App Icon | PNG | 1024×1024 (iOS), 512×512 (Android), 48×48 (Watch) |
| Splash | PNG | 2732×2732 (iOS), 1242×2436 (Android) |
| Illustrations | PNG @3x | 375×812 (iPhone), 414×896 (Plus) |
| Watch Complications | PNG | 192×192 (modular), 100×100 (circular) |

---

## 13. Security Checklist

- [ ] All tokens in SecureStore (never AsyncStorage)
- [ ] Certificate pinning for API
- [ ] Biometric required for sensitive actions
- [ ] Auto-lock on background > 30s
- [ ] Remote wipe capability (MDM)
- [ ] Audit logging for all mutations
- [ ] No PII in logs
- [ ] Encrypted WebSocket (WSS in prod)
- [ ] Rate limiting on client side
- [ ] Dependency scanning (npm audit + Snyk)

---

## 14. Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold start (TTI) | < 2.0s | `expo-startup` |
| Screen transition | < 300ms | React DevTools Profiler |
| List scroll (60fps) | 0 dropped frames | `why-did-you-render` |
| Voice latency (E2E) | < 3.0s | Manual + automated |
| Background sync | < 5s | Network timing |
| Bundle size (JS) | < 5MB gzipped | `expo-bundle-analyzer` |
| Memory (idle) | < 150MB | Xcode Instruments / Android Studio |

---

*Document Version: 1.0 | Last Updated: 2026-08-10 | Author: OWNEX Engineering*