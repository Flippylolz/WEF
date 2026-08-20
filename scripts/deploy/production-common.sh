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

require_plain_runtime_directory() {
  directory="$1"
  [ ! -L "$directory" ] || fail "runtime directory must not be a symlink: $directory"
  if [ -e "$directory" ] && [ ! -d "$directory" ]; then
    fail "runtime path must be a directory: $directory"
  fi
}

require_media_tree_directory() {
  directory="$1"
  expected_leaf="$2"
  if [ -L "$directory" ]; then
    root_resolved=$(readlink -f "$WEF_ROOT") || fail "unable to resolve WEF root: $WEF_ROOT"
    target=$(readlink -f "$directory") || fail "unable to resolve media symlink: $directory"
    case "$target" in
      "$root_resolved"/candidates/*/media/"$expected_leaf") ;;
      *)
        fail "media symlink must resolve under candidates/*/media/$expected_leaf: $directory"
        ;;
    esac
    [ -d "$target" ] || fail "media symlink target must be a directory: $directory"
    return 0
  fi
  if [ -e "$directory" ] && [ ! -d "$directory" ]; then
    fail "runtime path must be a directory: $directory"
  fi
}

prepare_runtime_directories() {
  require_plain_runtime_directory "$WEF_ROOT/media"
  require_plain_runtime_directory "$WEF_ROOT/media/reports"
  require_media_tree_directory "$WEF_ROOT/media/originals" originals
  require_media_tree_directory "$WEF_ROOT/media/public" public

  mkdir -p \
    "$WEF_ROOT/media/originals" \
    "$WEF_ROOT/media/public" \
    "$WEF_ROOT/media/reports"
  chmod 0750 \
    "$WEF_ROOT/media" \
    "$WEF_ROOT/media/originals" \
    "$WEF_ROOT/media/public" \
    "$WEF_ROOT/media/reports"
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
  if [ "$WEF_PUBLIC_PORT" -lt 1024 ] || [ "$WEF_PUBLIC_PORT" -gt 65535 ]; then
    fail "public port must be between 1024 and 65535"
  fi

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
