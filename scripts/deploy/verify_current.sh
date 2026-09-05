#!/bin/sh
# Verify an already-current release without migrations, activation or configuration changes.
set -eu
export PYTHONDONTWRITEBYTECODE=1
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/production-common.sh"
initialize_release_context "$@"
exec 9>"$WEF_ROOT/state/deploy.lock"
flock -n 9 || fail "another WEF deployment holds the host lock"
python3 "$SCRIPT_DIR/release_order.py" guard "$WEF_ROOT" "$WEF_RELEASE_SHA"
"$SCRIPT_DIR/smoke.sh" \
  "http://127.0.0.1:$WEF_PUBLIC_PORT" \
  "$WEF_RELEASE_SHA" \
  "https://tiles.openfreemap.org/styles/dark"
smoke_public_https_origin
