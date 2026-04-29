#!/bin/bash
# Initialize md2wechat skill local config.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SKILL_ROOT}/.env"
ENV_EXAMPLE="${SKILL_ROOT}/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created ${ENV_FILE}"
else
  chmod 600 "$ENV_FILE"
  echo ".env already exists; keeping current file"
fi

chmod +x "${SKILL_ROOT}/scripts/"*.sh
chmod +x "${SKILL_ROOT}/scripts/"*.py 2>/dev/null || true

echo "Next:"
echo "1. Edit ${ENV_FILE}"
echo "2. Validate config: ${SKILL_ROOT}/scripts/md2wechat-env.sh config show --format json"
echo "3. Validate draft readiness after cover exists: ${SKILL_ROOT}/scripts/md2wechat-env.sh inspect article.md --draft --cover cover.png --strict"
