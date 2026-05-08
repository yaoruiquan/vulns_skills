#!/bin/bash
# Run md2wechat after loading this skill's local .env.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/load_env.sh"

if [[ "${1:-}" == "test-draft" && $# -ge 3 ]]; then
  HTML_FILE="$2"
  COVER_IMAGE="$3"
  META_FILE="${HTML_FILE}.meta.json"
  if [[ -f "${META_FILE}" ]]; then
    exec python3 "${SCRIPT_DIR}/create_alert_draft.py" "${HTML_FILE}" "${COVER_IMAGE}" --metadata "${META_FILE}" --create --json
  fi
fi

exec md2wechat "$@"
