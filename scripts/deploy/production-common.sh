#!/bin/sh

set -eu

fail() {
  printf 'deployment error: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command is unavailable: $1"
}

require_file() {
  [ -f "$1" ] || fail "required file is missing"
}

require_directory() {
  [ -d "$1" ] || fail "required directory is missing"
}

initialize_release_context() {
  [ "$#" -eq 5 ] || fail "expected root, release directory, config file, SHA, and port"

  WEF_ROOT=$1
  WEF_RELEASE_DIR=$2
  WEF_CONFIG_FILE=$3
  WEF_RELEASE_SHA=$4
  WEF_PUBLIC_PORT=$5
  export WEF_ROOT WEF_RELEASE_DIR WEF_CONFIG_FILE WEF_RELEASE_SHA WEF_PUBLIC_PORT

  [ "${#WEF_RELEASE_SHA}" -eq 40 ] ||
    fail "release SHA must contain exactly 40 lowercase hexadecimal characters"
  case "$WEF_RELEASE_SHA" in
    *[!0-9a-f]*) fail "release SHA must contain exactly 40 lowercase hexadecimal characters" ;;
  esac
  case "$WEF_PUBLIC_PORT" in
    *[!0-9]* | "") fail "public port must be numeric" ;;
  esac
  [ "$WEF_PUBLIC_PORT" -ge 1024 ] && [ "$WEF_PUBLIC_PORT" -le 65535 ] ||
    fail "public port must be between 1024 and 65535"

  if [ "${WEF_DEPLOY_TEST_MODE:-0}" != "1" ]; then
    [ "$WEF_ROOT" = "/home/nuc/wef" ] || fail "production root must be /home/nuc/wef"
  fi

  case "$WEF_RELEASE_DIR" in
    "$WEF_ROOT"/releases/*) ;;
    *) fail "release directory must stay under the WEF release root" ;;
  esac
  case "$WEF_CONFIG_FILE" in
    "$WEF_ROOT"/secrets/releases/*/production.env) ;;
    *) fail "configuration must stay under the WEF secret release root" ;;
  esac

  require_directory "$WEF_ROOT"
  require_directory "$WEF_RELEASE_DIR"
  require_file "$WEF_CONFIG_FILE"
  require_file "$WEF_RELEASE_DIR/compose.production.yaml"
  require_file "$WEF_RELEASE_DIR/Caddyfile.production"
}

production_compose() {
  docker compose \
    --project-name wef-production \
    --env-file "$WEF_CONFIG_FILE" \
    --file "$WEF_RELEASE_DIR/compose.production.yaml" \
    "$@"
}
