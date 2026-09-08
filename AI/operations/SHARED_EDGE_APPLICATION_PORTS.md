# Shared edge application ports

Owner-requested unplanned infrastructure change, 2026-09-08. This task is the
coordination point for changes to shared Nginx; contact Codex in this task before
changing its listeners, templates, certificates, or deployment settings.

## Routing

- AI Forecast keeps its existing host port 3000. Shared Nginx adds HTTP port 3100,
  proxying to `host.docker.internal:3000` without a TLS requirement or redirect.
- Fillable uses HTTPS on port 3200, with the existing WEF hostname certificate.
  Its `fillable-production` TCP relay owns host port 3200 and forwards encrypted
  bytes over `wef-edge` to shared Nginx port 3200. Nginx terminates TLS and proxies
  to `http://fillable-gateway:8080`, preserving the public Host including port and
  forwarding HTTPS scheme and port 3200. The body limit is 12 MiB for the 10 MiB
  document limit plus multipart overhead.
- WEF retains HTTPS on port 443. Its Caddy rollback listener moves from public
  port 3100 to loopback port 13101. GitHub deployment variables must use
  `WEF_PUBLIC_PORT=13101` and `WEF_BIND_ADDRESS=127.0.0.1` so later releases retain
  the port assignment. Historical references to rollback port 3100 describe the
  old topology.

## Rendering and deployment

Render with `--forecast-http-upstream host.docker.internal:3000` and
`--fillable-upstream fillable-gateway:8080`. Both options are opt-in; existing
renders remain unchanged. Apply `infra/compose.shared-edge-http.yaml` after the
base edge Compose file to publish 3100. Do not publish 3200 from this project:
Fillable owns its relay. Preserve existing Certbot state and WEF upstream aliases.

HSTS applies to every port of a hostname. Enabling Forecast HTTP clears WEF's
HSTS policy with `Strict-Transport-Security: max-age=0` over HTTPS; TLS on 443 and
3200 remains enabled. Browsers with a cached policy must revisit WEF HTTPS once
before HTTP 3100 works. A distinct non-HSTS hostname or IP is another option.
TLS-only Fillable does not disable HSTS when Forecast HTTP is omitted.

Validate rendered Nginx as the serving UID before atomically activating a new
release, then reload/recreate the edge with the extra published port. Preserve
previous configuration and Compose files for rollback. Restore WEF's old port
only after removing Nginx's 3100 binding, and restore the GitHub variables too.
Verify WEF HTTPS, Forecast 3000 and 3100, and Fillable TLS/application health.
Fillable is not yet deployed as of initial inventory: its DNS resolves only once
its gateway joins `wef-edge`; variable proxy resolution allows Nginx to start
beforehand, but successful Fillable application verification remains pending.
