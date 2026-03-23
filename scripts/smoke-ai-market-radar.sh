#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[smoke] running AI Market Radar end-to-end smoke test"
python3 -m unittest tests.smoke.test_end_to_end_smoke
