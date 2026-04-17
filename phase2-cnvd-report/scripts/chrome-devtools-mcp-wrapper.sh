#!/bin/bash
set -euo pipefail

export CLAUDE_CHROME_MCP_PORT="${CLAUDE_CHROME_MCP_PORT:-9332}"
exec /Users/yao/.claude/skills/shared-chrome-devtools/mcp-wrapper.sh "$@"
