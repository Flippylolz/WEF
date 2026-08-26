#!/bin/sh

set -eu
umask 027

WEF_ROOT=/home/nuc/wef

[ "$(id -un)" = "nuc" ] || {
  printf 'provisioning error: expected the nuc account\n' >&2
  exit 1
}
[ "$HOME" = "/home/nuc" ] || {
  printf 'provisioning error: unexpected home directory\n' >&2
  exit 1
}

if [ -e "$WEF_ROOT" ] && [ -L "$WEF_ROOT" ]; then
  printf 'provisioning error: WEF root must not be a symlink\n' >&2
  exit 1
fi

for command_name in docker python3 curl flock ss awk df; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'provisioning error: required command is unavailable: %s\n' "$command_name" >&2
    exit 1
  }
done

docker info >/dev/null
docker compose version >/dev/null

if [ -n "$(ss -H -ltn 'sport = :3100' 2>/dev/null || true)" ]; then
  printf 'provisioning error: port 3100 is already occupied\n' >&2
  exit 1
fi

mkdir -p \
  "$WEF_ROOT/releases" \
  "$WEF_ROOT/secrets/releases" \
  "$WEF_ROOT/secrets/telegram" \
  "$WEF_ROOT/postgres" \
  "$WEF_ROOT/media" \
  "$WEF_ROOT/media/originals" \
  "$WEF_ROOT/media/public" \
  "$WEF_ROOT/media/reports" \
  "$WEF_ROOT/imports/incoming" \
  "$WEF_ROOT/imports/extracted" \
  "$WEF_ROOT/caddy-data" \
  "$WEF_ROOT/state" \
  "$WEF_ROOT/logs"

chmod 0750 \
  "$WEF_ROOT" \
  "$WEF_ROOT/releases" \
  "$WEF_ROOT/media" \
  "$WEF_ROOT/media/originals" \
  "$WEF_ROOT/media/public" \
  "$WEF_ROOT/media/reports" \
  "$WEF_ROOT/imports" \
  "$WEF_ROOT/imports/incoming" \
  "$WEF_ROOT/imports/extracted" \
  "$WEF_ROOT/caddy-data" \
  "$WEF_ROOT/state" \
  "$WEF_ROOT/logs"
chmod 0700 "$WEF_ROOT/secrets" "$WEF_ROOT/secrets/releases" "$WEF_ROOT/secrets/telegram" "$WEF_ROOT/postgres"

printf 'Prepared the isolated WEF server boundary at %s.\n' "$WEF_ROOT"
