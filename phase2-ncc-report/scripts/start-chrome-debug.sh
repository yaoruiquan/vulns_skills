#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${SKILL_ROOT}/.env"
SHARED_SKILLS_DIR="${SHARED_SKILLS_DIR:-${HOME}/.claude/skills/shared-chrome-devtools}"
SHARED_STARTER="${SHARED_STARTER:-${SHARED_SKILLS_DIR}/start-profile.sh}"
DEFAULT_CHROME_USER_DATA_DIR="${HOME}/Library/Application Support/Google/Chrome"
MODE="${1:-isolated}"

if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    value="${value#\"}"
    value="${value%\"}"
    value="${value#\'}"
    value="${value%\'}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    export "$key"="$value"
  done < "$ENV_FILE"
fi

PORT="${CHROME_DEBUG_PORT:-${CLAUDE_CHROME_MCP_PORT:-9334}}"
PROFILE_NAME="${CHROME_PROFILE_NAME:-${CLAUDE_CHROME_PROFILE_NAME:-ncc-report}}"

if [[ ! -x "$SHARED_STARTER" ]]; then
  echo "Shared Chrome starter not found or not executable: $SHARED_STARTER" >&2
  exit 1
fi

case "$MODE" in
  isolated)
    exec "$SHARED_STARTER" "$PROFILE_NAME" "$PORT"
    ;;
  seed-default)
    export CLAUDE_CHROME_SEED_USER_DATA_DIR="${CLAUDE_CHROME_SEED_USER_DATA_DIR:-$DEFAULT_CHROME_USER_DATA_DIR}"
    export CLAUDE_CHROME_PROFILE_DIRECTORY="${CLAUDE_CHROME_PROFILE_DIRECTORY:-Default}"
    exec "$SHARED_STARTER" "$PROFILE_NAME" "$PORT"
    ;;
  live-default)
    export CLAUDE_CHROME_USE_USER_DATA_DIR="${CLAUDE_CHROME_USE_USER_DATA_DIR:-$DEFAULT_CHROME_USER_DATA_DIR}"
    export CLAUDE_CHROME_PROFILE_DIRECTORY="${CLAUDE_CHROME_PROFILE_DIRECTORY:-Default}"
    exec "$SHARED_STARTER" "$PROFILE_NAME" "$PORT"
    ;;
  *)
    echo "Usage: $0 [isolated|seed-default|live-default]" >&2
    echo "  isolated      Start a clean skill-local Chrome profile (default)." >&2
    echo "  seed-default  Copy your main Chrome profile into the skill profile before launch." >&2
    echo "  live-default  Launch directly against your main Chrome profile. Close normal Chrome first." >&2
    exit 1
    ;;
esac
