#!/bin/sh
# Renew shared-edge certificates and reload Nginx only through the
# success-only validated chain: certbot renew (saved webroot settings,
# unattended) -> deploy-hook reload marker -> nginx -t gate -> graceful
# reload. Any failure leaves the running configuration untouched.
#
# usage: shared_edge_renew.sh EDGE_ROOT COMPOSE_FILE [certbot renew args...]
# The optional WEF_EDGE_UPSTREAM_NETWORK names the network used to resolve
# upstream hosts during reload validation (default: wef-edge).
set -eu

if [ "$#" -lt 2 ]; then
  printf 'usage: shared_edge_renew.sh EDGE_ROOT COMPOSE_FILE [certbot args...]\n' >&2
  exit 2
fi

edge_root=$1
compose_file=$2
shift 2

if [ ! -f "$compose_file" ]; then
  printf 'shared_edge_renew: compose file not found: %s\n' "$compose_file" >&2
  exit 2
fi

edge_root_abs=$(cd "$edge_root" && pwd)
export WEF_SHARED_EDGE_ROOT="$edge_root_abs"
marker="$edge_root_abs/state/reload-requested"
upstream_network="${WEF_EDGE_UPSTREAM_NETWORK:-wef-edge}"
nginx_image=nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236

# A stale marker from an interrupted run must never trigger a reload.
rm -f "$marker"

printf 'shared_edge_renew: running certbot renew...\n'
set +e
docker compose --file "$compose_file" --profile renew run --rm certbot \
  renew --non-interactive --deploy-hook /edge-hooks/deploy-hook.sh "$@"
renew_status=$?
set -e

if [ "$renew_status" -ne 0 ]; then
  printf 'shared_edge_renew: renewal failed (%s); reload skipped\n' "$renew_status" >&2
  exit "$renew_status"
fi

if [ ! -f "$marker" ]; then
  printf 'shared_edge_renew: no reload marker; reload skipped\n' >&2
  exit 0
fi

printf 'shared_edge_renew: validating configuration before reload...\n'
if ! docker run --rm --user 1000:1000 \
  --tmpfs /var/cache/nginx:rw,noexec,nosuid,size=64m,mode=1777 \
  --tmpfs /var/run:rw,noexec,nosuid,size=1m,mode=1777 \
  --network "$upstream_network" \
  --volume "$edge_root_abs:/etc/nginx-edge:ro" \
  "$nginx_image" \
  nginx -t -c /etc/nginx-edge/current/active.conf; then
  printf 'shared_edge_renew: nginx -t failed; reload skipped\n' >&2
  exit 1
fi

printf 'shared_edge_renew: reloading nginx...\n'
# Non-root shared-edge nginx leaves /run/nginx.pid empty, so pid-file reload
# fails. Signal HUP on the running container instead (same as reconnect/activate).
if ! docker compose --file "$compose_file" kill -s HUP nginx; then
  printf 'shared_edge_renew: graceful reload failed\n' >&2
  exit 1
fi

rm -f "$marker"
printf 'shared_edge_renew: renewal and validated reload complete\n'
