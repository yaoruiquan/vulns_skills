#!/bin/bash
set -euo pipefail

SHARED_STARTER="/Users/yao/.claude/skills/shared-chrome-devtools/start-profile.sh"
DEFAULT_CHROME_USER_DATA_DIR="${HOME}/Library/Application Support/Google/Chrome"
MODE="${1:-isolated}"

case "$MODE" in
  isolated)
    exec "$SHARED_STARTER" cnnvd-report 9333
    ;;
  seed-default)
    export CLAUDE_CHROME_SEED_USER_DATA_DIR="${CLAUDE_CHROME_SEED_USER_DATA_DIR:-$DEFAULT_CHROME_USER_DATA_DIR}"
    export CLAUDE_CHROME_PROFILE_DIRECTORY="${CLAUDE_CHROME_PROFILE_DIRECTORY:-Default}"
    exec "$SHARED_STARTER" cnnvd-report 9333
    ;;
  live-default)
    export CLAUDE_CHROME_USE_USER_DATA_DIR="${CLAUDE_CHROME_USE_USER_DATA_DIR:-$DEFAULT_CHROME_USER_DATA_DIR}"
    export CLAUDE_CHROME_PROFILE_DIRECTORY="${CLAUDE_CHROME_PROFILE_DIRECTORY:-Default}"
    exec "$SHARED_STARTER" cnnvd-report 9333
    ;;
  *)
    echo "Usage: $0 [isolated|seed-default|live-default]" >&2
    echo "  isolated      Start a clean skill-local Chrome profile (default)." >&2
    echo "  seed-default  Copy your main Chrome profile into the skill profile before launch." >&2
    echo "  live-default  Launch directly against your main Chrome profile. Close normal Chrome first." >&2
    exit 1
    ;;
esac
