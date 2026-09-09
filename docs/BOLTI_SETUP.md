# Bolti AI Phone-Call Channel — Setup Guide

Bolti is the second provider on the `CallProvider` seam (next to Ringg — see `docs/RINGG_SETUP.md`). Bolti owns the call end-to-end and reports results via **HMAC-SHA256-signed webhooks** configured at the workspace level. Without a token, selecting Bolti falls back to **mock mode** (auto-completes after ~8s with a simulated transcript).

Why Bolti: 50 free trial minutes (no credit card), transparent ₹6/min PAYG, per-agent STT/LLM/TTS choice, TRAI 140-series compliance, best-in-class webhook security.

Code entry points: `BE/app/providers/bolti.py` · webhook route `POST /api/v1/webhooks/bolti` in `BE/app/api/rest/calls.py`.

---

## 1. Bolti dashboard setup (one-time)

1. **Sign up** at https://app.bolti.co.in — an organization + default workspace are auto-created; you start with 50 free minutes.
2. **Create the agent** — Assistants → **Create AI Agent** wizard (persona, goal, voice, guardrails). Test it in the **Preview** tab (browser mic, no phone needed).
3. **Phone number** — buy one from Bolti (agent → **Make Outbound Call** / Settings → Phone) or bring your own SIP trunk. The number must be **assigned to the agent** or calls fail with `403`.
4. **Copy the `agent_id`** from the agent page.
5. **Create a Personal Access Token** — sidebar → profile → **Access Tokens → Create Token**. Shown **once** — store immediately.

## 2. Backend env vars

In the repo-root `.env`:

```
BOLTI_TOKEN=...
BOLTI_AGENT_ID=...
BOLTI_FROM_NUMBER=+917969541371      # literal E.164 number (no from_number_id like Ringg)
BOLTI_WEBHOOK_SECRET=...             # from step 3 below
# BOLTI_BASE_URL=https://api.bolti.co.in/v1   # only to override
```

Restart the backend. With token + agent + number all set, selecting **Bolti AI** in the call dropdown (or Auto when Ringg is unconfigured) places real calls; otherwise mock.

## 3. Webhook setup (dashboard, one-time)

Unlike Ringg there is **no per-call/per-agent subscription API** — webhooks are workspace-level:

1. Expose the backend locally: `ngrok http 8000` → `https://<random>.ngrok.io` (skip when deployed on a stable domain).
2. Bolti dashboard → **Settings → Webhooks → Add endpoint**:
   - URL: `https://<your-domain>/api/v1/webhooks/bolti`
   - Events: **`conversation.completed`** (required) + optionally `scheduled_call.failed`, `scheduled_call.cancelled`
3. The **signing secret is shown once** → save it as `BOLTI_WEBHOOK_SECRET`, restart the backend.
4. Use the dashboard's **Send test event** button to sanity-check the receiver (expect `204`).

Security notes (already implemented in `BE/app/api/rest/calls.py`):

- Signature verified over the **raw request body** (`HMAC-SHA256(secret, "<ts>.<raw>")`), constant-time compare
- Timestamps older than 5 minutes rejected (replay protection)
- During secret rotation Bolti sends **two `v1=` digests** — any match is accepted, so you can rotate without downtime
- Deliveries are at-least-once with retries; dedupe on payload `id` is handled via the call's `processed_events`

## 4. Verify

1. Web app → avatar detail → **Get a phone call instead** → Provider: **Bolti AI** → your own number.
2. Phone rings; talk; hang up.
3. Status page flips to **completed** with transcript/summary when the webhook lands.

Debug order:

- **Call rejected instantly** → Bolti error is stored as the call's failover reason; `402` = out of credits, `403` = number not assigned to agent, `404` = wrong `agent_id`.
- **Rang but status stuck** → webhook: Bolti dashboard shows delivery attempts + auto-disabled endpoints; `401` on our side = wrong `BOLTI_WEBHOOK_SECRET`, stale clock, or body tampering.
- **Ran as `mock` unexpectedly** → one of `BOLTI_TOKEN` / `BOLTI_AGENT_ID` / `BOLTI_FROM_NUMBER` is unset.

## 5. Persona variables

The avatar's persona is sent in `custom_variables` alongside Bolti's own
`customer_name`: `callee_name`, `avatar_name`, `greeting`, `system_prompt`
(from the published `Persona` row). Declare matching variables on the agent for
them to take effect. Explicit `custom_args` on the request win over the
persona. `CALL_SEND_PERSONA=false` sends only `callee_name`.

## 6. Out of scope (for later)

Scheduled calls (`POST /v1/scheduled-calls` + `Idempotency-Key`), bulk/recurring campaigns, MCP server, dead-letter replay tooling.
