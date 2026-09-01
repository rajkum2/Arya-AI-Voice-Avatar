#!/usr/bin/env bash
# Subscribe a Ringg assistant to our webhook endpoint.
# Reads RINGG_API_KEY / RINGG_AGENT_ID / RINGG_WEBHOOK_TOKEN from the repo .env,
# prompts only for the public base URL (e.g. your ngrok link).
#
# Usage:
#   ./scripts/subscribe-ringg-webhook.sh
#   ./scripts/subscribe-ringg-webhook.sh https://abc123.ngrok.io   # skip the prompt

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  # export only the RINGG_* lines, ignore comments/blank lines
  set -a
  # shellcheck disable=SC1090
  source <(grep -E '^RINGG_[A-Z_]+=' "$ENV_FILE" | sed 's/\r$//')
  set +a
else
  echo "No .env found at $ENV_FILE — relying on exported environment variables."
fi

RINGG_BASE_URL="${RINGG_BASE_URL:-https://prod-api.ringg.ai/ca/api/v0}"

missing=()
[[ -z "${RINGG_API_KEY:-}" ]] && missing+=("RINGG_API_KEY")
[[ -z "${RINGG_AGENT_ID:-}" ]] && missing+=("RINGG_AGENT_ID")
[[ -z "${RINGG_WEBHOOK_TOKEN:-}" ]] && missing+=("RINGG_WEBHOOK_TOKEN")
if (( ${#missing[@]} > 0 )); then
  echo "Missing required values: ${missing[*]}"
  echo "Set them in $ENV_FILE first."
  exit 1
fi

BASE_URL="${1:-}"
if [[ -z "$BASE_URL" ]]; then
  read -rp "Paste your public base URL (e.g. https://abc123.ngrok.io): " BASE_URL
fi
BASE_URL="${BASE_URL%/}"   # strip trailing slash

if [[ ! "$BASE_URL" =~ ^https:// ]]; then
  echo "Error: URL must start with https:// (Ringg requires HTTPS)."
  exit 1
fi

CALLBACK_URL="$BASE_URL/api/v1/webhooks/ringg"
echo
echo "Subscribing assistant $RINGG_AGENT_ID to:"
echo "  $CALLBACK_URL"
echo

response=$(curl -sS -w "\n%{http_code}" -X PATCH "$RINGG_BASE_URL/agent/v1" \
  -H "X-API-KEY: $RINGG_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"operation\": \"edit_event_subscriptions\",
    \"agent_id\": \"$RINGG_AGENT_ID\",
    \"event_subscriptions\": [{
      \"event_type\": [\"all_processing_completed\"],
      \"callback_url\": \"$CALLBACK_URL\",
      \"headers\": {\"Authorization\": \"Bearer $RINGG_WEBHOOK_TOKEN\"},
      \"method_type\": \"POST\"
    }]
  }")

http_code="${response##*$'\n'}"
body="${response%$'\n'*}"

echo "HTTP $http_code"
echo "$body"

if [[ "$http_code" =~ ^2 ]]; then
  echo
  echo "Done — the assistant now posts results to $CALLBACK_URL"
  echo "Reminder: free ngrok URLs change on every restart; re-run this script with the new URL."
else
  echo
  echo "Subscription failed — check your API key and agent_id."
  exit 1
fi
