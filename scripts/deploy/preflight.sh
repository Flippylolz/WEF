#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/production-common.sh"

initialize_release_context "$@"

for command_name in docker python3 df awk ss; do
  require_command "$command_name"
done

if [ "${WEF_DEPLOY_TEST_MODE:-0}" = "1" ]; then
  python3 "$SCRIPT_DIR/validate_release.py" \
    "$WEF_CONFIG_FILE" \
    "$WEF_ROOT" \
    "$WEF_RELEASE_DIR" \
    "$WEF_RELEASE_SHA" \
    "$WEF_PUBLIC_PORT" \
    --test-mode
else
  python3 "$SCRIPT_DIR/validate_release.py" \
    "$WEF_CONFIG_FILE" \
    "$WEF_ROOT" \
    "$WEF_RELEASE_DIR" \
    "$WEF_RELEASE_SHA" \
    "$WEF_PUBLIC_PORT"
fi

docker info >/dev/null
docker compose version >/dev/null
production_compose --profile operator --profile rehearsal config --quiet

available_kb=$(df -Pk "$WEF_ROOT" | awk 'NR == 2 {print $4}')
minimum_kb=${WEF_MIN_FREE_KB:-10485760}
[ "$available_kb" -ge "$minimum_kb" ] ||
  fail "insufficient free disk space for a release"

meminfo_file=${WEF_MEMINFO_FILE:-/proc/meminfo}
require_file "$meminfo_file"
available_memory_kb=$(awk '/^MemAvailable:/ {print $2}' "$meminfo_file")
minimum_memory_kb=${WEF_MIN_AVAILABLE_MEMORY_KB:-1048576}
[ "$available_memory_kb" -ge "$minimum_memory_kb" ] ||
  fail "insufficient available memory for a release"

running_edge=$(production_compose ps --status running --quiet edge 2>/dev/null || true)
if [ -z "$running_edge" ] &&
  [ -n "$(ss -H -ltn "sport = :$WEF_PUBLIC_PORT" 2>/dev/null || true)" ]; then
  fail "public port is already occupied outside the active WEF edge"
fi

printf 'WEF production preflight passed for release %.12s.\n' "$WEF_RELEASE_SHA"
