#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
N8N_CONTAINER="${N8N_CONTAINER:-n8n}"
WORKFLOW_ID="${WORKFLOW_ID:-kX2G1iy8AuHuqTR9}"
WORKFLOW_FILE="${WORKFLOW_FILE:-$ROOT_DIR/workflows/health-agent-webhook.workflow.json}"
WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:5678/webhook/apple-health}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/n8n}"
SMOKE_TEST_SCRIPT="${SMOKE_TEST_SCRIPT:-$ROOT_DIR/scripts/smoke-test.sh}"
RECOVERY_SCRIPT="${RECOVERY_SCRIPT:-$ROOT_DIR/scripts/reactivate-health-workflow.sh}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_FILE="$BACKUP_DIR/${WORKFLOW_ID}-${TIMESTAMP}.json"
CONTAINER_IMPORT_PATH="/tmp/health-agent-workflow-update-${TIMESTAMP}.json"

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

rollback_workflow() {
  echo
  echo "==> Rollback"
  echo "Restoring backup: $BACKUP_FILE"

  docker cp "$BACKUP_FILE" "$N8N_CONTAINER:$CONTAINER_IMPORT_PATH.rollback" >/tmp/health-agent-update-rollback-copy.txt 2>&1 || {
    cat /tmp/health-agent-update-rollback-copy.txt >&2
    fail "Rollback failed while copying backup into container"
  }

  docker exec "$N8N_CONTAINER" n8n import:workflow --input="$CONTAINER_IMPORT_PATH.rollback" >/tmp/health-agent-update-rollback-import.txt 2>&1 || {
    cat /tmp/health-agent-update-rollback-import.txt >&2
    fail "Rollback failed while importing backup workflow"
  }

  WORKFLOW_ID="$WORKFLOW_ID" \
  N8N_CONTAINER="$N8N_CONTAINER" \
  WEBHOOK_URL="$WEBHOOK_URL" \
  "$RECOVERY_SCRIPT" >/tmp/health-agent-update-rollback-recovery.txt 2>&1 || {
    cat /tmp/health-agent-update-rollback-recovery.txt >&2
    fail "Rollback imported the backup, but recovery failed"
  }

  docker exec "$N8N_CONTAINER" rm -f "$CONTAINER_IMPORT_PATH.rollback" >/dev/null 2>&1 || true
  echo "[PASS] Backup restored"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

section "n8n Workflow Update"
echo "Container:     $N8N_CONTAINER"
echo "Workflow ID:   $WORKFLOW_ID"
echo "Workflow file: $WORKFLOW_FILE"
echo "Webhook:       $WEBHOOK_URL"
echo "Backup file:   $BACKUP_FILE"

require_command docker
require_command curl
require_command python3
[[ -f "$WORKFLOW_FILE" ]] || fail "Workflow file not found: $WORKFLOW_FILE"
[[ -x "$SMOKE_TEST_SCRIPT" ]] || fail "Smoke test script is missing or not executable: $SMOKE_TEST_SCRIPT"
[[ -x "$RECOVERY_SCRIPT" ]] || fail "Recovery script is missing or not executable: $RECOVERY_SCRIPT"

mkdir -p "$BACKUP_DIR"

section "Backup Current Workflow"
docker exec "$N8N_CONTAINER" n8n export:workflow --id="$WORKFLOW_ID" --output="$CONTAINER_IMPORT_PATH.backup" >/tmp/health-agent-update-backup.txt 2>&1 || {
  cat /tmp/health-agent-update-backup.txt >&2
  fail "Could not export current workflow for backup"
}
docker cp "$N8N_CONTAINER:$CONTAINER_IMPORT_PATH.backup" "$BACKUP_FILE" >/tmp/health-agent-update-docker-cp.txt 2>&1 || {
  cat /tmp/health-agent-update-docker-cp.txt >&2
  fail "Could not copy backup out of the container"
}
docker exec "$N8N_CONTAINER" rm -f "$CONTAINER_IMPORT_PATH.backup" >/dev/null 2>&1 || true
pass "Backup saved"

section "Build Import Payload"
python3 - "$BACKUP_FILE" "$WORKFLOW_FILE" "/tmp/health-agent-workflow-import-${TIMESTAMP}.json" <<'PY'
import json
import sys
from pathlib import Path

backup_path = Path(sys.argv[1])
template_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

backup = json.loads(backup_path.read_text())
template = json.loads(template_path.read_text())

if not isinstance(backup, list) or not backup:
    raise SystemExit("Backup export does not contain a workflow entity array")

entity = backup[0]

for key in ["name", "nodes", "connections", "settings", "staticData", "pinData", "meta", "tags"]:
    if key in template:
        entity[key] = template[key]

output_path.write_text(json.dumps([entity], ensure_ascii=False))
PY
IMPORT_SOURCE_FILE="/tmp/health-agent-workflow-import-${TIMESTAMP}.json"
[[ -f "$IMPORT_SOURCE_FILE" ]] || fail "Could not build merged import payload"
pass "Merged import payload created from backup + repo workflow"

section "Copy New Workflow Into Container"
docker cp "$IMPORT_SOURCE_FILE" "$N8N_CONTAINER:$CONTAINER_IMPORT_PATH" >/tmp/health-agent-update-copy.txt 2>&1 || {
  cat /tmp/health-agent-update-copy.txt >&2
  fail "Could not copy workflow file into container"
}
pass "Workflow file copied into container"

section "Import Workflow"
docker exec "$N8N_CONTAINER" n8n import:workflow --input="$CONTAINER_IMPORT_PATH" >/tmp/health-agent-update-import.txt 2>&1 || {
  cat /tmp/health-agent-update-import.txt >&2
  fail "Workflow import failed"
}
pass "Workflow import completed"

section "Recovery And Validation"
WORKFLOW_ID="$WORKFLOW_ID" \
N8N_CONTAINER="$N8N_CONTAINER" \
WEBHOOK_URL="$WEBHOOK_URL" \
"$RECOVERY_SCRIPT" || {
  echo
  echo "Recovery/validation failed. Attempting rollback..." >&2
  rollback_workflow
  fail "Workflow imported, but validation failed. Backup was restored."
}

section "Cleanup"
docker exec "$N8N_CONTAINER" rm -f "$CONTAINER_IMPORT_PATH" >/dev/null 2>&1 || true
rm -f "$IMPORT_SOURCE_FILE"
pass "Temporary import file removed"

section "Final Smoke Test"
"$SMOKE_TEST_SCRIPT"
