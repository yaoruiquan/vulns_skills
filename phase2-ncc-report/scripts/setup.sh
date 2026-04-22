#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SKILL_ROOT}/.env"
ENV_EXAMPLE="${SKILL_ROOT}/.env.example"
MCP_WRAPPER="${SKILL_ROOT}/scripts/chrome-devtools-mcp-wrapper.sh"
MCP_FILE="${SKILL_ROOT}/.mcp.json"

echo "Skill root: ${SKILL_ROOT}"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "Created .env from .env.example"
  else
    echo "Missing .env.example: ${ENV_EXAMPLE}" >&2
    exit 1
  fi
else
  chmod 600 "$ENV_FILE"
  echo ".env already exists; keeping current file"
fi

cat > "$MCP_FILE" << EOF
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "${MCP_WRAPPER}",
      "args": []
    }
  }
}
EOF

chmod +x "${SKILL_ROOT}/scripts/start-chrome-debug.sh"
chmod +x "${SKILL_ROOT}/scripts/chrome-devtools-mcp-wrapper.sh"
chmod +x "${SKILL_ROOT}/scripts/extract_vuln_data.py"
chmod +x "${SKILL_ROOT}/scripts/captcha_ocr.py"
chmod +x "${SKILL_ROOT}/scripts/dingtalk_notify.py"

echo "Wrote MCP config: ${MCP_FILE}"
echo "Next:"
echo "1. Edit ${ENV_FILE}"
echo "2. Start browser: ${SKILL_ROOT}/scripts/start-chrome-debug.sh"
echo "3. Verify: curl -s http://127.0.0.1:9334/json/version"
