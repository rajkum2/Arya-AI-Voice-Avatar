# Arya AI Voice Avatar — Complete Phase Plan

**Product:** Real-time interactive photorealistic AI avatar (speech-to-speech)  
**Surfaces:** Python backend (`BE/`), Next.js web (`FE/`), Kotlin Android (`android-app/`)  
**Architecture principle:** Provider-agnostic conversation engine; avatar/STT/LLM/TTS behind seams; clients only receive short-lived session tokens.

---

## Goals & non-goals

### Goals
- FaceTime-like call with AI avatar (listening / thinking / speaking)
- Captions, barge-in, quota, consent (EU AI Act Art. 50 + GDPR)
- Admin control plane (avatars, personas, keys, flags, live sessions)
- Swap HeyGen → Anam/Tavus → in-house renderer without client rewrites

### Non-goals (v1)
- iOS native app
- Multi-party group avatar calls
- Full offline conversation
- Immediate self-hosted MuseTalk in production (Phase 3 only)

---

## Success metrics (SLOs)

| Metric | Target | Warn | Critical |
|--------|--------|------|----------|
| Turn E2E p50 (end-of-speech → first audio) | <500–600 ms | >800 ms | >1200 ms |
| Turn E2E p95 | <800–1000 ms | >1200 ms | >1500 ms |
| Barge-in stop (TTS mute) | <100 ms | >150 ms | >200 ms |
| Session setup (token → first video) | <3 s | >5 s | >8 s |
| Error rate (failed sessions) | <2% | >5% | >10% |

---

## Repository layout

```
Arya-AI-Voice-Avatar/
├── docs/PHASE_PLAN.md          # this file
├── BE/                         # FastAPI + providers + orchestration
├── FE/                         # Next.js (user web + admin routes)
├── android-app/                # Kotlin + Jetpack Compose
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# PHASE 0 — Foundations (Week 0)

**Objective:** Runnable monorepo skeleton, local infra, shared contracts.

### Deliverables
- [x] Repo structure (`BE/`, `FE/`, `android-app/`)
- [x] Docker Compose: Postgres, Redis, (optional LiveKit)
- [x] `.env.example` for all secrets
- [x] OpenAPI-first session/auth contracts documented
- [x] CI stubs (lint/test hooks)

### Exit criteria
- `docker compose up` starts Postgres + Redis
- `uvicorn` starts and `/health` returns 200
- Next.js dev server loads landing page
- Android project opens / Gradle syncs (structure complete)

### Dependencies
None.

---

# PHASE 1A — Conversation MVP (Weeks 1–4)

**Objective:** One happy-path live (or mock) conversation on web, then Android.

### Backend
| Task | Detail |
|------|--------|
| Auth | JWT access + refresh; email/password; optional OAuth stubs |
| Bootstrap | `GET /api/v1/bootstrap` — flags, maintenance, min versions |
| Consent | Store consent version + timestamps; block session without required consents |
| Avatars | CRUD (admin) + public list of active avatars |
| Sessions | `POST /sessions` mints short-lived token; mock or HeyGen provider |
| Provider seam | `AvatarProvider` interface + `MockProvider` + `HeyGenProvider` stub |
| WebSocket | `/ws/session/{id}` for transcript + control events |
| Usage | Meter session minutes; basic quota check |

### Frontend (Next.js)
| Screen | Spec ref |
|--------|----------|
| Landing | 2.1 |
| Login / Sign up | 2.2 |
| Consent | 2.2 / Art. 50 |
| Gallery + Detail | 2.4–2.5 |
| Conversation | 2.6 (video placeholder or LiveKit) |
| Post-call summary | mirror 1.9 |

### Android
| Screen | Spec ref |
|--------|----------|
| Splash, Onboarding | 1.1–1.2 |
| Consent, Auth | 1.3–1.4 |
| Mic priming | 1.5 |
| Gallery, Detail | 1.6–1.7 |
| Conversation | 1.8 (LiveKit client path) |
| Summary | 1.9 |

### Exit criteria
- User can register → consent → pick avatar → “start session” → see turn states + mock captions
- Provider keys never leave server
- Feature flags `captions_default`, `barge_in_enabled` applied at session join

### Change triggers
- If HeyGen latency/realism fails A/B → try Anam behind same seam
- If LiveKit mobile path blocked → temporary WS audio + still video (degraded)

---

# PHASE 1B — Production hardening (Weeks 5–10)

### Backend
- Full admin APIs: personas, voices, KB upload stubs, moderation, audit log
- Encrypted API key storage (Fernet / KMS-ready)
- Spend caps + plan quotas
- Per-stage latency telemetry (VAD, STT, LLM, TTS, avatar)
- GDPR: export job + erasure job
- Rate limits, idle timeout, force-end session

### Frontend
- History + transcript detail
- Settings (captions, privacy, export/delete)
- Admin dashboard routes (`/admin/*`) with RBAC UI
- Device picker, keyboard shortcuts, `beforeunload` guard
- PWA shell (offline page only)

### Android
- Foreground service (`microphone` type)
- PiP, audio routing, deep links
- History, settings, privacy controls
- FCM push stubs

### Exit criteria
- Admin can enable/disable avatar, rotate keys, force-end session
- User can export/delete data
- Latency percentiles visible on admin home

---

# PHASE 1C — Polish & scale (Weeks 11–16)

- Multi-provider failover ordered list
- Stripe + Play Billing integration
- Advanced analytics (CSAT, interruption rate)
- Accessibility pass (WCAG-oriented captions, live regions)
- Load tests for concurrent sessions
- Security review (authz on every admin route)

---

# PHASE 2 — Multi-provider & enterprise (Weeks 17–24)

- Anam + Tavus providers fully implemented
- Knowledge base RAG pipeline
- SSO/SAML for admin
- Region routing (EU data residency option)
- SLA dashboards and PagerDuty alerts

---

# PHASE 3 — In-house migration (Month 6+)

Migrate **one layer at a time** behind existing interfaces:

1. STT → faster-whisper  
2. TTS → Kokoro / Fish Speech  
3. LLM → Qwen/Mistral on vLLM  
4. Avatar last → MuseTalk or Ditto  

Keep managed avatar as failover. Abort Phase 3 renderer if E2E >1.5s or <2 streams/GPU economically.

---

## Dependency graph (build order)

```
Phase 0 skeleton
    │
    ├─► Auth + Consent + Bootstrap
    │         │
    │         ▼
    ├─► Avatar catalog (DB + admin seed)
    │         │
    │         ▼
    ├─► Session service + MockProvider
    │         │
    │         ├─► Web Conversation UI
    │         └─► Android Conversation UI
    │                   │
    │                   ▼
    ├─► LiveKit/HeyGen real provider
    │         │
    │         ▼
    ├─► Captions WS + barge-in flags
    │         │
    │         ▼
    └─► Admin, quotas, moderation, GDPR
```

---

## Risk register

| Risk | Mitigation |
|------|------------|
| No official HeyGen Kotlin SDK | Use LiveKit Android SDK; prove in Phase 1A week 1 |
| Latency regressions | Per-stage metrics from day one; SLO gates in CI later |
| Cost runaway | Idle timeout, spend caps, per-user quotas |
| Art. 50 non-compliance | Consent gate + persistent AI badge before EU traffic |
| Provider lock-in | `AvatarProvider` interface mandatory; no client SDK secrets |
| OSS license traps | Only MIT/Apache for commercial self-host |

---

## Team / sequencing recommendation

| Stream | Owner focus | Parallel? |
|--------|-------------|-----------|
| BE | Auth, sessions, providers | Lead |
| FE | Landing → conversation | After session API stub |
| Android | Compose shell → conversation | After session API stub |
| Admin | After avatars + flags exist | Parallel to 1B |

---

## Definition of Done (overall Phase 1)

1. Web + Android can complete a full conversation loop with captions and AI disclosure  
2. Backend proxies all provider credentials  
3. Admin can manage avatars, personas, feature flags, and view live/historical sessions  
4. GDPR export/delete and consent audit work end-to-end  
5. Docker-based local demo documented in README  

---

## Implementation status (repo)

This repository ships **Phase 0 complete** and a **functional Phase 1A scaffold**:

- Runnable FastAPI with mock provider, auth, bootstrap, sessions, admin APIs  
- Next.js user + admin UI wired to the API  
- Kotlin Compose app with navigation and API client  

Wire real `HEYGEN_API_KEY` / LiveKit credentials to move from mock video to production streaming.
