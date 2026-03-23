#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
This setup script belongs to the legacy AI Deals Monitor stack.
It is not a valid deployment path for the current Health Agent iPhone app.
EOF
exit 1

PROJECT_DIR="${PROJECT_DIR:-/opt/ai-deals-monitor}"

cd "${PROJECT_DIR}"

if [[ ! -f .env ]]; then
  echo "Missing .env in ${PROJECT_DIR}"
  exit 1
fi

echo "Waiting for postgres..."
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-deals}" -d "${POSTGRES_DB:-deals_monitor}" >/dev/null 2>&1; do
  sleep 2
done

echo "Applying SQL migrations..."
docker compose exec -T postgres psql -U "${POSTGRES_USER:-deals}" -d "${POSTGRES_DB:-deals_monitor}" -f /docker-entrypoint-initdb.d/001_init.sql
docker compose exec -T postgres psql -U "${POSTGRES_USER:-deals}" -d "${POSTGRES_DB:-deals_monitor}" -f /docker-entrypoint-initdb.d/002_sources.sql

echo "Done"
