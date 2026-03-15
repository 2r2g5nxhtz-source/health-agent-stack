#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
TARGET="${2:-}"
OUTPUT="${3:-}"

if [[ -z "${MODE}" || -z "${TARGET}" ]]; then
  cat <<'EOF'
Usage:
  run-skill-scanner.sh basic <target>
  run-skill-scanner.sh behavioral <target>
  run-skill-scanner.sh deep <target>
  run-skill-scanner.sh all <skills-root>
  run-skill-scanner.sh sarif <skills-root> <output.sarif>
EOF
  exit 2
fi

USER_BIN="${HOME}/Library/Python/3.14/bin"
if [[ -d "${USER_BIN}" ]]; then
  export PATH="${USER_BIN}:${PATH}"
fi

if ! command -v skill-scanner >/dev/null 2>&1; then
  echo "skill-scanner is not installed."
  echo "Install with: uv pip install cisco-ai-skill-scanner"
  exit 127
fi

case "${MODE}" in
  basic)
    exec skill-scanner scan "${TARGET}"
    ;;
  behavioral)
    exec skill-scanner scan "${TARGET}" --use-behavioral
    ;;
  deep)
    exec skill-scanner scan "${TARGET}" --use-behavioral --use-llm --enable-meta
    ;;
  all)
    exec skill-scanner scan-all "${TARGET}" --recursive
    ;;
  sarif)
    if [[ -z "${OUTPUT}" ]]; then
      echo "sarif mode requires an output path"
      exit 2
    fi
    exec skill-scanner scan-all "${TARGET}" --recursive --format sarif --output "${OUTPUT}"
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    exit 2
    ;;
esac
