#!/bin/bash
set -euo pipefail

PROFILE_NAME="${1:-}"
PORT="${2:-}"

if [[ -z "$PROFILE_NAME" || -z "$PORT" ]]; then
  echo "Usage: $0 <profile-name> <remote-debugging-port>" >&2
  exit 1
fi

SHARED_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_ROOT="${SHARED_ROOT}/profiles"
RUNTIME_ROOT="${SHARED_ROOT}/runtime"
PROFILE_DIR="${PROFILE_ROOT}/${PROFILE_NAME}"
DEFAULT_PROFILE_DIR="${CLAUDE_CHROME_PROFILE_DIRECTORY:-Default}"
CHROME_USER_DATA_DIR="${CLAUDE_CHROME_USE_USER_DATA_DIR:-$PROFILE_DIR}"
SEED_USER_DATA_DIR="${CLAUDE_CHROME_SEED_USER_DATA_DIR:-}"
START_URL="${CLAUDE_CHROME_START_URL:-about:blank}"

mkdir -p "$PROFILE_ROOT" "$RUNTIME_ROOT"

find_chrome_app() {
  local candidates=(
    "/Applications/Google Chrome.app"
    "/Applications/Google Chrome Canary.app"
    "/Applications/Chromium.app"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

seed_profile_if_needed() {
  if [[ -z "$SEED_USER_DATA_DIR" || -n "${CLAUDE_CHROME_USE_USER_DATA_DIR:-}" ]]; then
    return 0
  fi

  if [[ -d "$PROFILE_DIR" && -f "${PROFILE_DIR}/.seeded" ]]; then
    return 0
  fi

  mkdir -p "$PROFILE_DIR"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --delete \
      --exclude='Cache' \
      --exclude='Code Cache' \
      --exclude='GPUCache' \
      --exclude='Crashpad' \
      --exclude='GrShaderCache' \
      --exclude='ShaderCache' \
      --exclude='Singleton*' \
      "${SEED_USER_DATA_DIR}/" "${PROFILE_DIR}/"
  else
    cp -R "${SEED_USER_DATA_DIR}/." "$PROFILE_DIR/"
  fi

  touch "${PROFILE_DIR}/.seeded"
}

if ! CHROME_APP="$(find_chrome_app)"; then
  echo "Google Chrome not found in standard macOS locations." >&2
  exit 1
fi

seed_profile_if_needed

if [[ -n "${CLAUDE_CHROME_USE_USER_DATA_DIR:-}" ]]; then
  mkdir -p "$CHROME_USER_DATA_DIR"
else
  mkdir -p "$PROFILE_DIR"
fi

LOG_FILE="${RUNTIME_ROOT}/${PROFILE_NAME}-${PORT}.log"

open -na "$CHROME_APP" --args \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$CHROME_USER_DATA_DIR" \
  --profile-directory="$DEFAULT_PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-background-networking \
  "$START_URL" \
  >"$LOG_FILE" 2>&1

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
    echo "Chrome debugging ready on port ${PORT}"
    echo "Profile: ${PROFILE_NAME}"
    echo "User data dir: ${CHROME_USER_DATA_DIR}"
    exit 0
  fi
  sleep 1
done

echo "Chrome started but debugging endpoint did not become ready on port ${PORT}" >&2
echo "Log: ${LOG_FILE}" >&2
exit 1
