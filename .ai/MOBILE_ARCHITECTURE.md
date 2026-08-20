# Mobile Architecture — Ownex Ecosystem

## Current State (v7.0.0)

**Windows Desktop Architecture:**
```
Windows User → OWNEX Launcher (PowerShell)
     ↓
WSL2 Ubuntu → start_backend.sh
     ↓
FastAPI Backend → SQLite DB (in WSL repo)
     ↓
Tauri Desktop Shell → Frontend → API
```

**Key Design Principles:**
- Windows client runs backend locally (WSL2)
- Database lives in WSL2 filesystem
- No external network dependencies
- Zero-config installation

## Proposed Mobile Architecture

```
                OWNEX BACKEND (Cloud/Server)
                       │
          ┌────────────┴────────────┐
          │                         │
     Windows Client            Mobile Client
          │                         │
    Tauri + WSL2            Android/iOS
    (local backend)         (remote API)
```

## Mobile Client Requirements

### API Layer
- **REST API** over HTTPS
- **Authentication**: JWT tokens with refresh
- **Authorization**: Role-based access (user/admin)
- **Rate limiting**: Per-user, per-endpoint
- **CORS**: Configured for mobile domains

### Core Features
1. **Dashboard** — Mission Control view
2. **Career Engine** — Skill gaps, roadmaps, training
3. **Copilot** — AI assistant chat
4. **Findings** — Bug bounty results
5. **Opportunities** — Available work
6. **Settings** — User preferences
7. **Notifications** — Push notifications
8. **Activity Timeline** — Recent actions

### Technology Stack
- **Frontend**: React Native (cross-platform) OR Capacitor (Vue-based)
- **State Management**: Redux Toolkit or Pinia
- **Networking**: Axios or fetch API
- **Authentication**: JWT storage in secure storage
- **Push Notifications**: Firebase Cloud Messaging (FCM)

## API Endpoints for Mobile

### Authentication
- `POST /api/auth/register` — User registration
- `POST /api/auth/login` — JWT token issuance
- `POST /api/auth/refresh` — Token refresh
- `POST /api/auth/logout` — Token invalidation

### Dashboard
- `GET /api/dashboard` — Mission Control summary
- `GET /api/dashboard/kpi` — Key performance indicators
- `GET /api/dashboard/activity` — Recent activity

### Career Engine
- `GET /api/career/status` — Current profile status
- `POST /api/career/analyze` — Skill gap analysis
- `POST /api/career/roadmap` — Learning roadmap
- `POST /api/career/daily-training` — Daily training plan

### Copilot
- `GET /api/copilot/status` — Agent status
- `POST /api/copilot/chat` — Chat with AI
- `GET /api/copilot/recommendations` — System recommendations
- `GET /api/copilot/context` — System context

### Findings
- `GET /api/findings` — List findings (paginated)
- `GET /api/findings/{id}` — Finding details
- `POST /api/findings/{id}/approve` — Approve finding
- `POST /api/findings/{id}/reject` — Reject finding

### Opportunities
- `GET /api/opportunities` — Available opportunities
- `GET /api/opportunities/{id}` — Opportunity details
- `POST /api/opportunities/{id}/claim` — Claim opportunity

### Settings
- `GET /api/settings` — User settings
- `PUT /api/settings` — Update settings
- `GET /api/settings/profile` — User profile

## Security Considerations

### Authentication
- **JWT Access Tokens**: 15-30 minute expiry
- **Refresh Tokens**: 7-30 day expiry, stored securely
- **Token Rotation**: Invalidate old tokens on refresh
- **Device Binding**: Tokens bound to device ID

### Data Protection
- **HTTPS Only**: All API calls over TLS 1.3+
- **Certificate Pinning**: Prevent MITM attacks
- **Encrypted Storage**: Sensitive data encrypted at rest
- **Secure Storage**: Use platform secure storage (Keychain/Keystore)

### Rate Limiting
- **Per-User Limits**: Prevent abuse
- **Endpoint-Specific**: Different limits per endpoint
- **Burst Allowance**: Short burst allowance for UX

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mobile.ownex.app", "exp://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Implementation Phases

### Phase 1: API Authentication Layer
- JWT token system
- User registration/login
- Token refresh mechanism
- Secure mobile-specific endpoints

### Phase 2: Mobile API Endpoints
- Paginated data endpoints
- Mobile-optimized responses (lightweight JSON)
- Offline-first caching strategy
- Background sync

### Phase 3: Mobile Frontend Prototype
- React Native project setup
- Authentication flow
- Dashboard prototype
- Basic navigation

### Phase 4: Feature Integration
- Career Engine mobile UI
- Copilot chat interface
- Findings list/details
- Settings management

### Phase 5: Push Notifications
- FCM integration
- Event-driven notifications
- Notification preferences
- Battery optimization

## Current Backend Compatibility

**Already Ready for Mobile:**
- ✅ FastAPI REST API foundation
- ✅ Career Engine endpoints (`/api/career/*`)
- ✅ Copilot endpoints (`/api/copilot/*`)
- ✅ Findings endpoints (`/api/findings/*`)
- ✅ Activity timeline (`/api/activity`)
- ✅ Dashboard endpoints (`/api/dashboard`)

**Missing for Mobile:**
- ❌ JWT authentication system
- ❌ User registration/login
- ❌ Token refresh mechanism
- ❌ Rate limiting per user
- ❌ Mobile-specific CORS
- ❌ Push notification system
- ❌ Offline data sync

## Next Steps

1. **Implement JWT Authentication** — Add user management
2. **Add Rate Limiting** — Per-user limits
3. **Configure CORS** — Mobile domain whitelisting
4. **Create Mobile API Spec** — Document mobile-specific endpoints
5. **Build Mobile Prototype** — React Native boilerplate
6. **Test API Integration** — Mobile ↔ Backend communication

## Decision Required

Before proceeding with mobile development, decide:

1. **Backend Deployment**: Cloud hosting for mobile backend (AWS/GCP/Azure)?
2. **Database Migration**: Move from local SQLite to PostgreSQL for cloud?
3. **User Management**: Implement full user accounts system?
4. **Push Notifications**: Choose FCM or alternative?
5. **Mobile Framework**: React Native or Capacitor?

## Status

⚠️ **PLANNING PHASE** — Architecture designed, awaiting implementation decision.

Windows Desktop architecture is production-ready. Mobile requires backend cloud deployment and authentication system.
