# Arya AI Voice Avatar

Real-time interactive photorealistic AI avatar platform:

| Surface | Stack | Folder |
|---------|--------|--------|
| Backend | Python 3.11+ · FastAPI · SQLAlchemy · provider abstraction | `BE/` |
| Web | Next.js 15 · React 19 · TypeScript | `FE/` |
| Mobile | Kotlin · Jetpack Compose · Hilt · Retrofit | `android-app/` |

**Phase plan (read first):** [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md)

---

## Architecture (short)

```
Client (Web / Android)
   │  JWT + short-lived session token
   ▼
FastAPI (BE)
   │  AvatarProvider seam
   ├── MockProvider (default local)
   ├── HeyGenProvider (when HEYGEN_API_KEY set)
   └── AnamProvider (scaffold)
   │
   └── WebSocket /ws/session/{id}  → captions + turn state
```

Keys **never** leave the server. Clients join with session tokens only.

---

## Quick start (local mock mode)

### 1. Backend

```bash
cd BE
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example ../.env  # optional
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

**Seeded accounts**

| Email | Password | Role |
|-------|----------|------|
| `demo@example.com` | `demo12345` | user |
| `admin@example.com` | `admin12345` | super_admin |

SQLite is used by default (`BE/arya.db`). For Postgres:

```bash
docker compose up -d postgres redis
# set DATABASE_URL=postgresql+asyncpg://arya:arya@localhost:5432/arya
```

### 2. Frontend

```bash
cd FE
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 → Log in → Consent → Gallery → Start conversation (type to mock STT).

### 3. Android

1. Open `android-app/` in Android Studio (Ladybug+ / AGP 8.7).  
2. Emulator uses `http://10.0.2.2:8000/` (see `BuildConfig.API_BASE_URL`).  
3. Run the `app` configuration.  
4. Grant microphone when starting a conversation.  
5. Type messages in mock mode; LiveKit/HeyGen video is the next integration step.

---

## Key API routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/auth/register` / `login` | JWT auth |
| POST | `/api/v1/auth/consent` | EU AI Act / GDPR gate |
| GET | `/api/v1/bootstrap` / `bootstrap/me` | Flags + disclosure |
| GET | `/api/v1/avatars` | Gallery |
| POST | `/api/v1/sessions` | Mint provider session |
| DELETE | `/api/v1/sessions/{id}` | End + quota |
| WS | `/ws/session/{id}?token=` | Captions + turn state |
| GET | `/api/v1/admin/dashboard` | Admin KPIs |
| GET | `/api/v1/me/export` | GDPR export |

---

## Enabling HeyGen

1. Set `HEYGEN_API_KEY` and `DEFAULT_AVATAR_PROVIDER=heygen` in `.env`.  
2. Update avatar `provider` / `provider_avatar_id` via admin API.  
3. Client receives LiveKit `room_url` + `room_token` from `POST /sessions`.  
4. Attach LiveKit JS / Android SDK to the conversation screen video surface.

Until the key is set, the API **falls back to mock** so demos always work.

---

## Phase status

| Phase | Status |
|-------|--------|
| 0 Foundations | ✅ Scaffold, compose, seed, docs |
| 1A Conversation MVP | ✅ Mock path end-to-end (web + Android structure) |
| 1B Hardening | 🔲 Real LiveKit, full admin CRUD UI, billing |
| 2 Multi-provider | 🔲 Anam/Tavus production |
| 3 In-house render | 🔲 MuseTalk/Ditto |

Details: [`docs/PHASE_PLAN.md`](docs/PHASE_PLAN.md)

---

## License

Proprietary / unlicensed scaffold — add your license before publishing.
