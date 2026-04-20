#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SKILL_ROOT}/.env"
ENV_EXAMPLE="${SKILL_ROOT}/.env.example"
ENV_TEMPLATE="${SKILL_ROOT}/.env.template"
MCP_WRAPPER="${SKILL_ROOT}/scripts/chrome-devtools-mcp-wrapper.sh"
MCP_FILE="${SKILL_ROOT}/.mcp.json"

echo "Skill root: ${SKILL_ROOT}"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created .env from .env.example"
  elif [[ -f "$ENV_TEMPLATE" ]]; then
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    echo "Created .env from legacy .env.template"
  else
    echo "Missing .env.example or .env.template" >&2
    exit 1
  fi
else
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
chmod +x "${SKILL_ROOT}/scripts/compress_zip.py"
chmod +x "${SKILL_ROOT}/scripts/extract_vuln_data.py"
chmod +x "${SKILL_ROOT}/scripts/update_summary.py"
chmod +x "${SKILL_ROOT}/scripts/captcha_ocr.py"

echo "Wrote MCP config: ${MCP_FILE}"
echo "Next:"
echo "1. Edit ${ENV_FILE}"
echo "2. Start browser: ${SKILL_ROOT}/scripts/start-chrome-debug.sh"
echo "3. Verify: curl -s http://127.0.0.1:9333/json/version"
