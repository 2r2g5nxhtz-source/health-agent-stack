#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 root@SERVER_IP"
  exit 1
fi

TARGET="$1"
PROJECT_DIR="/opt/ai-deals-monitor"
LOCAL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "${LOCAL_ROOT}/.env" ]]; then
  echo "Missing ${LOCAL_ROOT}/.env"
  exit 1
fi

echo "Uploading project to ${TARGET}..."
ssh "${TARGET}" "mkdir -p ${PROJECT_DIR}"
tar \
  --exclude '.git' \
  --exclude '.DS_Store' \
  -C "${LOCAL_ROOT}" \
  -czf - . | ssh "${TARGET}" "tar -xzf - -C ${PROJECT_DIR}"

echo "Running bootstrap..."
scp "${LOCAL_ROOT}/deploy/bootstrap-server.sh" "${TARGET}:/root/bootstrap-server.sh"
ssh "${TARGET}" "chmod +x /root/bootstrap-server.sh && /root/bootstrap-server.sh"

echo "Starting stack..."
ssh "${TARGET}" "cd ${PROJECT_DIR} && docker compose pull && docker compose up -d"

echo "Deployment complete"
echo "Open: https://$(grep '^N8N_HOST=' "${LOCAL_ROOT}/.env" | cut -d= -f2)"
