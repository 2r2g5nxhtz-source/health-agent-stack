#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
N8N_CONTAINER="${N8N_CONTAINER:-n8n}"
WORKFLOW_ID="${WORKFLOW_ID:-kX2G1iy8AuHuqTR9}"
WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:5678/webhook/apple-health}"
SMOKE_TEST_SCRIPT="${SMOKE_TEST_SCRIPT:-$ROOT_DIR/scripts/smoke-test.sh}"

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

wait_for_webhook() {
  local attempts="${1:-15}"
  local delay="${2:-2}"
  local body=""
  local http_code=""
  local timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  local payload="{\"heart_rate\":92,\"glucose\":118,\"weight\":81.4,\"sleep_hours\":5.6,\"timestamp\":\"$timestamp\"}"

  for ((i = 1; i <= attempts; i++)); do
    http_code="$(curl -sS -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      --data "$payload" \
      -o /tmp/health-agent-reactivate-body.txt \
      -w "%{http_code}" || true)"
    body="$(cat /tmp/health-agent-reactivate-body.txt 2>/dev/null || true)"

    if [[ "$http_code" == "404" && "$body" == *"not registered"* ]]; then
      sleep "$delay"
      continue
    fi

    if [[ "$http_code" != "000" ]]; then
      echo "$http_code"
      return 0
    fi

    sleep "$delay"
  done

  echo "$http_code"
}

section "Health Workflow Recovery"
echo "Container:  $N8N_CONTAINER"
echo "WorkflowId: $WORKFLOW_ID"
echo "Webhook:    $WEBHOOK_URL"

require_command docker
require_command curl

[[ -x "$SMOKE_TEST_SCRIPT" ]] || fail "Smoke test script is missing or not executable: $SMOKE_TEST_SCRIPT"

section "Activate Workflow"
docker exec "$N8N_CONTAINER" n8n update:workflow --id="$WORKFLOW_ID" --active=true >/tmp/health-agent-reactivate-update.txt 2>&1 || {
  cat /tmp/health-agent-reactivate-update.txt >&2
  fail "Could not activate workflow"
}
pass "Activation command sent"

section "Restart n8n"
docker restart "$N8N_CONTAINER" >/tmp/health-agent-reactivate-restart.txt 2>&1 || {
  cat /tmp/health-agent-reactivate-restart.txt >&2
  fail "Could not restart n8n container"
}
pass "n8n restarted"

section "Wait For Webhook"
http_code="$(wait_for_webhook 20 2)"
body="$(cat /tmp/health-agent-reactivate-body.txt 2>/dev/null || true)"

case "$http_code" in
  200|201|202|401|405)
    pass "Webhook responded after recovery (HTTP $http_code)"
    ;;
  404)
    if [[ "$http_code" == "404" && "$body" == *"not registered"* ]]; then
      fail "Webhook is still not registered after recovery"
    fi
    fail "Webhook returned 404 after recovery: $body"
    ;;
  000)
    fail "Webhook did not come back after restart"
    ;;
  *)
    pass "Webhook responded after recovery (HTTP $http_code)"
    ;;
esac

section "Smoke Test"
"$SMOKE_TEST_SCRIPT"
