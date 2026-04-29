#!/bin/bash
# Run md2wechat after loading this skill's local .env.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/load_env.sh"

exec md2wechat "$@"
