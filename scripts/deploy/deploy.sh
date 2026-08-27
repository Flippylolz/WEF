#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/production-common.sh"

initialize_release_context "$@"
require_command flock
require_directory "$WEF_ROOT/state"

exec 9>"$WEF_ROOT/state/deploy.lock"
flock -n 9 || fail "another WEF deployment holds the host lock"

prepare_runtime_directories

"$SCRIPT_DIR/preflight.sh" \
  "$WEF_ROOT" \
  "$WEF_RELEASE_DIR" \
  "$WEF_CONFIG_FILE" \
  "$WEF_RELEASE_SHA" \
  "$WEF_PUBLIC_PORT"

if [ "${WEF_DEPLOY_SKIP_PULL:-0}" != "1" ]; then
  production_compose pull db api web edge
elif [ "${WEF_DEPLOY_TEST_MODE:-0}" != "1" ]; then
  fail "image pull can be skipped only in deployment test mode"
fi

if [ "${WEF_DEPLOY_TEST_MODE:-0}" != "1" ] &&
  ! production_compose --profile operator run --rm geocoder-check; then
  fail "Geoapify readiness failed; existing application release was not replaced"
fi

production_compose --profile operator run --rm db-permissions
production_compose up --detach --wait db
if ! production_compose --profile operator run --rm migrate; then
  fail "forward migration failed; existing application release was not replaced"
fi

if [ "${WEF_SEED_REHEARSAL:-0}" = "1" ]; then
  production_compose --profile rehearsal run --rm seed
fi

current_state="$WEF_ROOT/state/current.json"
previous_state="$WEF_ROOT/state/previous.json"
had_previous=0
if [ -f "$current_state" ]; then
  cp "$current_state" "$previous_state"
  chmod 600 "$previous_state"
  had_previous=1
fi

candidate_healthy=0
if bring_up_application_services &&
  "$SCRIPT_DIR/smoke.sh" \
    "http://127.0.0.1:$WEF_PUBLIC_PORT" \
    "$WEF_RELEASE_SHA" \
    "https://tiles.openfreemap.org/styles/dark" &&
  smoke_public_https_origin; then
  candidate_healthy=1
fi

forced_failure=0
if [ "$candidate_healthy" -eq 1 ] &&
  [ "${WEF_FORCE_ROLLBACK_REHEARSAL:-0}" = "1" ]; then
  printf 'Forcing the reviewed rollback rehearsal after successful smoke.\n' >&2
  candidate_healthy=0
  forced_failure=1
fi

if [ "$candidate_healthy" -eq 1 ]; then
  python3 "$SCRIPT_DIR/release_state.py" write \
    "$current_state" \
    "$WEF_RELEASE_DIR" \
    "$WEF_CONFIG_FILE" \
    "$WEF_RELEASE_SHA" \
    "$WEF_PUBLIC_PORT"
  python3 "$SCRIPT_DIR/release_state.py" activate \
    "$WEF_ROOT" \
    "$WEF_RELEASE_DIR" \
    "$WEF_CONFIG_FILE"
  printf 'Activated WEF release %.12s.\n' "$WEF_RELEASE_SHA"
  exit 0
fi

printf 'Candidate release failed health verification.\n' >&2
recorded_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ "$had_previous" -eq 1 ]; then
  restored_sha=$(
    python3 "$SCRIPT_DIR/release_state.py" get "$previous_state" release_sha
  )
  if "$SCRIPT_DIR/rollback.sh" "$WEF_ROOT" "$previous_state"; then
    python3 "$SCRIPT_DIR/release_state.py" failure \
      "$WEF_ROOT/state/last-failure.json" \
      "$WEF_RELEASE_SHA" \
      health_verification \
      "$recorded_at" \
      "$restored_sha"
    printf 'Previous WEF application release restored.\n' >&2
    if [ "$forced_failure" -eq 1 ]; then
      exit 42
    fi
  else
    python3 "$SCRIPT_DIR/release_state.py" failure \
      "$WEF_ROOT/state/last-failure.json" \
      "$WEF_RELEASE_SHA" \
      health_verification \
      "$recorded_at"
    printf 'deployment error: automatic application rollback failed\n' >&2
  fi
else
  production_compose stop edge web api || true
  python3 "$SCRIPT_DIR/release_state.py" failure \
    "$WEF_ROOT/state/last-failure.json" \
    "$WEF_RELEASE_SHA" \
    health_verification \
    "$recorded_at"
  printf 'No previous release exists; unhealthy WEF application services were stopped.\n' >&2
fi
exit 1
