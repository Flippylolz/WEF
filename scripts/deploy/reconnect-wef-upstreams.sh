#!/bin/sh
# Re-attach WEF application containers to shared Nginx (wef-edge) and reload
# Nginx so upstream DNS picks up new container IPs after a recreate.
#
# Safe to run repeatedly. Does not start/stop/remove the wef-shared-edge project.

set -eu

EDGE_NETWORK=${WEF_EDGE_NETWORK:-wef-edge}
NGINX_CONTAINER=${WEF_SHARED_EDGE_NGINX_CONTAINER:-wef-shared-edge-nginx-1}

if ! docker network inspect "$EDGE_NETWORK" >/dev/null 2>&1; then
  printf 'shared edge network %s absent; skipping upstream reconnect\n' "$EDGE_NETWORK"
  exit 0
fi

connect() {
  container=$1
  alias_name=$2
  if ! docker inspect "$container" >/dev/null 2>&1; then
    printf 'missing %s (skip)\n' "$container" >&2
    return 0
  fi
  if docker inspect "$container" --format '{{json .NetworkSettings.Networks}}' |
    grep -q "\"$EDGE_NETWORK\""; then
    printf '%s already on %s\n' "$container" "$EDGE_NETWORK"
    return 0
  fi
  docker network connect --alias "$alias_name" "$EDGE_NETWORK" "$container"
  printf 'connected %s as %s\n' "$container" "$alias_name"
}

connect wef-production-api-1 wef-api
connect wef-production-web-1 wef-web
connect wef-production-media-edge-1 wef-media

if docker inspect "$NGINX_CONTAINER" >/dev/null 2>&1; then
  docker exec "$NGINX_CONTAINER" nginx -t
  docker exec "$NGINX_CONTAINER" nginx -s reload
  printf 'reloaded %s upstream DNS\n' "$NGINX_CONTAINER"
else
  printf 'shared-edge nginx container %s missing; upstreams attached without reload\n' \
    "$NGINX_CONTAINER" >&2
fi
