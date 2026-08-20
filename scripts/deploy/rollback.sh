#!/bin/sh

set -eu

if [ "$#" -ne 2 ]; then
  printf 'usage: rollback.sh WEF_ROOT TARGET_STATE\n' >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
WEF_ROOT=$1
target_state=$2

case "$target_state" in
  "$WEF_ROOT"/state/*) ;;
  *)
    printf 'deployment error: rollback state must stay under the WEF state root\n' >&2
    exit 1
    ;;
esac

release_dir=$(python3 "$SCRIPT_DIR/release_state.py" get "$target_state" release_dir)
config_file=$(python3 "$SCRIPT_DIR/release_state.py" get "$target_state" config_file)
release_sha=$(python3 "$SCRIPT_DIR/release_state.py" get "$target_state" release_sha)
public_port=$(python3 "$SCRIPT_DIR/release_state.py" get "$target_state" public_port)

# shellcheck disable=SC1091
. "$SCRIPT_DIR/production-common.sh"
initialize_release_context \
  "$WEF_ROOT" \
  "$release_dir" \
  "$config_file" \
  "$release_sha" \
  "$public_port"

"$SCRIPT_DIR/preflight.sh" \
  "$WEF_ROOT" \
  "$WEF_RELEASE_DIR" \
  "$WEF_CONFIG_FILE" \
  "$WEF_RELEASE_SHA" \
  "$WEF_PUBLIC_PORT"

production_compose up --detach --wait db
bring_up_application_services
"$SCRIPT_DIR/smoke.sh" \
  "http://127.0.0.1:$WEF_PUBLIC_PORT" \
  "$WEF_RELEASE_SHA" \
  "https://tiles.openfreemap.org/styles/liberty"
smoke_public_https_origin

python3 "$SCRIPT_DIR/release_state.py" write \
  "$WEF_ROOT/state/current.json" \
  "$WEF_RELEASE_DIR" \
  "$WEF_CONFIG_FILE" \
  "$WEF_RELEASE_SHA" \
  "$WEF_PUBLIC_PORT"
python3 "$SCRIPT_DIR/release_state.py" activate \
  "$WEF_ROOT" \
  "$WEF_RELEASE_DIR" \
  "$WEF_CONFIG_FILE"

printf 'Restored compatible application release %.12s.\n' "$WEF_RELEASE_SHA"
