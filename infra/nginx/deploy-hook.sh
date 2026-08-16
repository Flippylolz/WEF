#!/bin/sh
# Certbot deploy hook for the WEF shared edge. Certbot runs this script only
# after a successful issuance or renewal, as root inside the Certbot
# container. The hook aligns certificate-tree permissions for the
# least-privileged Nginx reader, records a reload request, and never reloads
# Nginx itself; the renewal orchestrator turns the request into `nginx -t`
# followed by a graceful reload.
set -eu

state_dir="${WEF_EDGE_STATE_DIR:-/var/lib/wef-edge}"
lineage="${RENEWED_LINEAGE:-}"
edge_gid="${WEF_EDGE_GID:-1000}"

fail() {
    echo "deploy-hook: $1" >&2
    exit 1
}

[ -n "$lineage" ] || fail "RENEWED_LINEAGE is not set"
[ -d "$lineage" ] || fail "renewed lineage directory does not exist: $lineage"
[ -r "$lineage/fullchain.pem" ] || fail "fullchain.pem is not readable"
[ -r "$lineage/privkey.pem" ] || fail "privkey.pem is not readable"

case "$lineage" in
    /etc/letsencrypt/live/*)
        # The persistent tree keeps Certbot-managed symlinks into archive/.
        [ -L "$lineage/fullchain.pem" ] || fail "fullchain.pem is not a Certbot-managed symlink"
        [ -L "$lineage/privkey.pem" ] || fail "privkey.pem is not a Certbot-managed symlink"
        ;;
    *)
        # `renew --dry-run` stages temporary lineages outside the live tree.
        ;;
esac

# Certbot writes root-only permissions. Open traversal and let the
# least-privileged edge group read exactly the material Nginx needs:
# directories traversable, public chain material world-readable, private
# keys restricted to the edge group. Accounts stay root-only.
chmod 0711 /etc/letsencrypt || fail "cannot set /etc/letsencrypt traversal"
find /etc/letsencrypt/live /etc/letsencrypt/archive -type d -exec chmod 0755 {} + ||
    fail "cannot open certificate directory traversal"
find /etc/letsencrypt/live /etc/letsencrypt/archive -type f \
    \( -name 'cert*.pem' -o -name 'chain*.pem' -o -name 'fullchain*.pem' \) \
    -exec chmod 0644 {} + || fail "cannot publish certificate material"
find /etc/letsencrypt/live /etc/letsencrypt/archive -type f \
    -name 'privkey*.pem' -exec chgrp "$edge_gid" {} + || fail "cannot group private keys"
find /etc/letsencrypt/live /etc/letsencrypt/archive -type f \
    -name 'privkey*.pem' -exec chmod 0640 {} + || fail "cannot restrict private keys"

mkdir -p "$state_dir"
umask 077
marker="$state_dir/reload-requested"
tmp="$state_dir/.reload-requested.tmp"
printf '%s\n' "$lineage" > "$tmp"
mv "$tmp" "$marker"
echo "deploy-hook: reload requested for $lineage"
