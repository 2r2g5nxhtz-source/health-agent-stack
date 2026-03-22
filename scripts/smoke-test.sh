#!/bin/zsh
set -euo pipefail

N8N_CONTAINER="${N8N_CONTAINER:-n8n}"
WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:5678/webhook/apple-health}"
HEALTH_SECRET="${HEALTH_SECRET:-}"
TIMESTAMP="${TIMESTAMP:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}"
PAYLOAD="${PAYLOAD:-"{\"heart_rate\":92,\"glucose\":118,\"weight\":81.4,\"sleep_hours\":5.6,\"timestamp\":\"$TIMESTAMP\"}"}"

section() {
  echo
  echo "==> $1"
}

pass() {
  echo "[PASS] $1"
}

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

retry_curl_post_status() {
  local output_file="$1"
  local attempts="${2:-10}"
  local delay="${3:-2}"
  local http_code=""

  for ((i = 1; i <= attempts; i++)); do
    http_code="$(curl "${curl_args[@]}" || true)"
    if [[ "$http_code" != "000" ]]; then
      echo "$http_code"
      return 0
    fi
    sleep "$delay"
  done

  echo "$http_code"
}

section "Health Agent Smoke Test"
echo "Container: $N8N_CONTAINER"
echo "Webhook:   $WEBHOOK_URL"
echo "Timestamp: $TIMESTAMP"

require_command docker
require_command curl

section "Docker"
docker info >/dev/null 2>&1 || fail "Docker daemon is not reachable"
pass "Docker daemon is reachable"

section "Container"
docker inspect "$N8N_CONTAINER" >/dev/null 2>&1 || fail "Container '$N8N_CONTAINER' was not found"

container_running="$(docker inspect -f '{{.State.Running}}' "$N8N_CONTAINER" 2>/dev/null || echo false)"
[[ "$container_running" == "true" ]] || fail "Container '$N8N_CONTAINER' is not running"
pass "Container '$N8N_CONTAINER' is running"

section "POST Payload"
curl_args=(
  -sS
  -X POST
  "$WEBHOOK_URL"
  -H "Content-Type: application/json"
  --data "$PAYLOAD"
  -o /tmp/health-agent-smoke-post-body.txt
  -w "%{http_code}"
)

if [[ -n "$HEALTH_SECRET" ]]; then
  curl_args+=(-H "X-Health-Agent-Secret: $HEALTH_SECRET")
fi

post_status="$(retry_curl_post_status /tmp/health-agent-smoke-post-body.txt 12 2)"
post_body="$(cat /tmp/health-agent-smoke-post-body.txt 2>/dev/null || true)"

case "$post_status" in
  200|201|202)
    pass "Webhook accepted the payload (HTTP $post_status)"
    ;;
  401)
    fail "Webhook rejected the shared secret (HTTP 401)"
    ;;
  404)
    if [[ "$post_body" == *"not registered"* ]]; then
      fail "Webhook is not registered in n8n. The workflow is likely inactive or unpublished."
    fi
    fail "Webhook path was not found during POST"
    ;;
  000)
    fail "POST request could not reach the webhook"
    ;;
  *)
    fail "Unexpected webhook response (HTTP $post_status): $post_body"
    ;;
esac

echo "Response body: $post_body"

section "n8n Workflow Presence"
workflow_list="$(docker exec "$N8N_CONTAINER" n8n list:workflow 2>/dev/null || true)"
if [[ -z "$workflow_list" ]]; then
  fail "No workflows were listed by n8n"
fi
pass "n8n lists at least one workflow"
echo "$workflow_list"

section "Done"
pass "Health Agent smoke test finished successfully"
