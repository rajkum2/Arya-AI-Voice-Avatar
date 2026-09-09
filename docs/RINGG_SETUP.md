# Ringg AI Phone-Call Channel — Setup Guide

The phone-call channel is a **separate seam** from the LiveKit avatar path: Ringg owns the call end-to-end (STT → LLM → TTS → telephony) and reports results back to us via webhook. Without a key, everything runs in **mock mode** (calls auto-complete after ~8s with a simulated transcript) so the flow is always demo-able.

Code entry points:

| Piece | File |
|---|---|
| Provider seam | `BE/app/providers/call_base.py` · `ringg.py` · `call_mock.py` · `call_registry.py` |
| DB model | `BE/app/models/call.py` |
| Service | `BE/app/services/call_service.py` |
| Routes + webhook | `BE/app/api/rest/calls.py` |
| Web UI | `FE/src/app/avatars/[id]/page.tsx` (call card) · `FE/src/app/calls/[id]/page.tsx` (status) |
| Webhook subscription helper | `scripts/subscribe-ringg-webhook.sh` |

---

## 1. Ringg dashboard setup (one-time)

1. **Account** — sign up at https://www.ringg.ai; calls consume workspace credits.
2. **API key** — Dashboard → **Settings → API Key → Generate API Key**. Shown **once** — copy immediately. Regenerating instantly revokes the old key.
3. **Number** — Dashboard → **Numbers → Buy new number**, or connect your own telephony (Integrations → Your Telephony → Twilio/Exotel/Plivo). Get the number's **`from_number_id`**:
   ```bash
   curl -H "X-API-KEY: <key>" https://prod-api.ringg.ai/ca/api/v0/workspace/numbers
   ```
4. **Assistant** — Dashboard → **Assistants → Create** → Direction: **Outbound**, Style: **Single Prompt**.
   - Our backend always sends `callee_name`; reference it in the prompt as `@{{callee_name}}`.
   - Any extra per-call variables (`custom_args`) must match `@{{variable}}` placeholders **exactly**.
   - Set a calling window (e.g. 09:00–18:00 Asia/Kolkata).
   - Copy the **`agent_id`** from the assistant page.
5. **Test inside Ringg first** — dashboard **Test call** to your own mobile. Fix prompt/voice issues here before touching our app.

## 2. Backend env vars

In the repo-root `.env`:

```
RINGG_API_KEY=...
RINGG_AGENT_ID=...
RINGG_FROM_NUMBER_ID=...
RINGG_WEBHOOK_TOKEN=<any long random string you invent>
# RINGG_BASE_URL=https://prod-api.ringg.ai/ca/api/v0   # only to override
```

Restart the backend. The registry switches mock → real automatically when key + agent + number are all set. `RINGG_WEBHOOK_TOKEN` is required for the webhook endpoint; when empty it rejects everything (503).

## 3. Webhook subscription (one-time per assistant)

Ringg must deliver `all_processing_completed` events to `POST /api/v1/webhooks/ringg`, authenticated with your bearer token.

Local dev needs a public URL first:

```bash
ngrok http 8000    # → https://<random>.ngrok.io
```

Then run the helper script from the repo root — it reads the credentials from `.env` and asks only for the public URL:

```bash
./scripts/subscribe-ringg-webhook.sh
# or non-interactively:
./scripts/subscribe-ringg-webhook.sh https://<random>.ngrok.io
```

Notes:

- Subscription is **per assistant** and persists — re-run only when the URL changes (free ngrok gives a new URL every restart) or for a new assistant. Re-subscribing replaces the old config.
- Deployed to a stable domain (e.g. Railway)? Subscribe once with that URL; no ngrok needed.
- Webhook security = the shared bearer token (Ringg forwards your subscription headers back to you). Ringg does not sign webhooks.

## 4. Verify

1. Web app → avatar detail → **Get a phone call instead** → your own number (E.164, e.g. `+919876543210`).
2. Phone rings within seconds; talk; hang up.
3. Status page (`/calls/{id}`) polls every 5s and flips to **completed** with transcript + summary once the webhook lands.

Debug order:

- **Phone never rings** → Ringg-side: check dashboard call logs, credits, agent config, calling window.
- **Rang but status stuck** → webhook delivery: inspect `http://127.0.0.1:4040` (ngrok web interface) for the POST. `401` = token mismatch with `RINGG_WEBHOOK_TOKEN`; `204` = processed fine.
- **Call ran as `mock` unexpectedly** → one of `RINGG_API_KEY` / `RINGG_AGENT_ID` / `RINGG_FROM_NUMBER_ID` is unset; the failover reason is logged and stored on the call metadata.

## 5. Persona variables

The backend sends the selected avatar's persona to Ringg as custom variables, so
gallery selection actually changes the call:

| Variable | Source |
|---|---|
| `callee_name` | always sent — `CallCreateRequest.callee_name` |
| `avatar_name` | `Avatar.name` |
| `greeting` | published `Persona.greeting` |
| `system_prompt` | published `Persona.system_prompt` |

These only take effect if the assistant prompt declares matching placeholders.
In the dashboard: **Assistants → your assistant → Custom Variables**, add each
key with the exact spelling above, then reference them in the prompt as
`@{{avatar_name}}` etc. A variable with no placeholder is ignored.

Explicit `custom_args` on the API request override the persona values.

Set `CALL_SEND_PERSONA=false` to send only `callee_name` — use this if Ringg
starts rejecting variables it has no placeholder for.

## 6. Known caveat

We use Ringg's `/calling/outbound/individual` (explicit `from_number_id`). Ringg marks it **deprecated** in favor of the number-pool `v2` endpoint — still works today; migrating later is a one-function change inside `RinggCallProvider.start_call` in `BE/app/providers/ringg.py`.
