# Shared edge application ports

Owner-requested unplanned infrastructure change, deployed 2026-09-08. This task is
the coordination point for shared Nginx changes: contact Codex in this task before
changing its listeners, templates, certificates, or deployment settings.

## Confirmed setup

- AI Forecast remains on its existing HTTP host port 3000. No new Forecast proxy
  listener is enabled, and its containers were not recreated.
- WEF retains HTTPS on port 443 and its existing Caddy rollback listener on 3100.
  GitHub deployment variables remain `WEF_PUBLIC_PORT=3100` and
  `WEF_BIND_ADDRESS=0.0.0.0`.
- Fillable uses HTTPS on port 3200 with the existing WEF hostname certificate.
  Its `fillable-production` TCP relay owns host port 3200 and forwards encrypted
  bytes over `wef-edge` to shared Nginx port 3200. Nginx terminates TLS and proxies
  to `http://fillable-gateway:8080`, preserving the public Host including port and
  forwarding HTTPS scheme and port 3200. The body limit is 12 MiB for the 10 MiB
  document limit plus multipart overhead.
- WEF's HSTS policy remains enabled. No HTTP 3100 overlay or HSTS reset is active.

The owner initially requested Forecast on HTTP 3100, then explicitly chose to
leave it on 3000. The attempted loopback migration never changed the running
server; its unneeded validator follow-up PR #379 was closed. PR #378 supplies the
optional renderer capabilities; the final deployed release enables only Fillable.

## Deployment and verification

The active edge release is `r-20260908-fillable-tls` under
`/home/nuc/wef-shared-edge/root/releases/`. Render with
`--fillable-upstream fillable-gateway:8080` and the existing WEF upstream inputs.
Do not pass `--forecast-http-upstream` or apply `compose.shared-edge-http.yaml`
for this setup. Do not publish host port 3200 from the shared-edge Compose project:
Fillable owns its TCP relay. Preserve Certbot state and existing WEF aliases.

The release passed `nginx -t` before and after a graceful HUP reload. WEF HTTPS,
WEF rollback HTTP 3100, and Forecast HTTP 3000 returned 200. A certificate-verified
HTTPS request to Nginx's internal port 3200 reached the new listener and returned
502 because Fillable is not deployed. The owner explicitly confirmed that the
upstream is pending: Nginx uses deferred Docker DNS resolution to prepare the TLS
listener without claiming application readiness. Normal release activation still
requires all upstreams; this scoped rollout validated the existing WEF/Forecast
upstreams and separately recorded the absent Fillable application.

Fillable's public relay and application must be deployed before its public URL
works. Its staged `/home/nuc/fillable/runtime.env` currently uses an HTTP public
origin; the Fillable deployment must set
`FILLABLE_PUBLIC_ORIGIN=https://2fa54e2405.duckdns.org:3200`.

Rollback restores the `previous` edge release (`r-20260830-osm-tiles`), validates
Nginx, and sends HUP. Before-state configuration and activation evidence are kept
under `/home/nuc/wef-shared-edge/changes/fillable-tls-3200/`. WEF and Forecast
listener assignments do not change during this rollback.
