# Deleted hostname retirement — 2026-10-20

The owner deleted `2fa54e2405.duckdns.org` and explicitly requested server
cleanup. This is unplanned operations maintenance, outside an epic's application
implementation scope. The supported hostname is `flipstarnuc.duckdns.org`.

## Observed problem

- The deleted name no longer resolved, but the DuckDNS container still attempted
  updates for both names. Its update at 15:27 CEST returned `KO`.
- Nginx accepted both hostnames on WEF 443 and Fillable 3200 and rewrote the old
  Fillable Origin to the current Origin.
- The public certificate covered both hostnames; its DNS-01 hook allowed both.
  Keeping the deleted domain in future certificate requests would make renewal
  depend on a domain the owner no longer controls.
- GitHub's repository `DEPLOY_HOST` variable still used the deleted name.

## Applied changes

- Changed the private DDNS environment to `DUCKDNS_SUBDOMAINS=flipstarnuc` and
  recreated only the `duckdns-ddns` project's DuckDNS service, without pulling a
  different image. The first subsequent update at 15:29 CEST succeeded.
- Restricted the existing DNS-01 auth/cleanup hook to the primary hostname.
- Reissued the existing Certbot lineage with only
  `DNS:flipstarnuc.duckdns.org`; the new certificate expires 2027-01-18.
- Created and activated `r-20261020-retire-domain` from the then-current edge
  release. Removed the retired `server_name` alias and temporary Fillable Origin
  mapping, preserving the listeners, upstreams, security headers and unrelated
  temporary-page configuration. Updated the release's issuance instructions to
  request only the primary hostname using the existing DNS-01 hooks.
- Validated the candidate as the serving UID and checked upstream connectivity
  through the existing release manager. Validated again in the running Nginx
  container, then sent HUP for a graceful reload.
- Set GitHub's repository variable `DEPLOY_HOST=flipstarnuc.duckdns.org` and its
  production `DEPLOY_KNOWN_HOSTS` secret to the verified current hostname/key
  association. Strict SSH host checking remains enabled; the deployment key is
  unchanged.

The internal Certbot lineage name remains `2fa54e2405.duckdns.org`. Its managed
paths are used by Nginx and retained rollback releases and are deliberately not
renamed or removed. The certificate's DNS names and subsequent renewal are
single-domain despite that historical directory name. Historical evidence,
inactive releases and private rollback copies retain their original contents.

## Verification

- Public WEF HTTPS and readiness returned 200 before the change.
- Public Fillable HTTPS on 3200 returned 200 before the change.
- After activation, WEF rollback HTTP on 3100 and Forecast HTTP on 3000 returned
  200; DDNS reported a successful update for the remaining name.
- No running container environment referenced the retired hostname after the
  DDNS service recreation.
- Certificate-verified connections to both 443 and 3200 confirmed the only SAN
  is `DNS:flipstarnuc.duckdns.org`, expiring 2027-01-18 at 12:31:28 UTC.
- The scheduled `shared_edge_renew.sh` path passed
  `--dry-run --run-deploy-hooks`: the DNS challenge propagated, the previous TXT
  value was restored, the deploy hook ran, `nginx -t` passed and Nginx reloaded.
  No pending TXT challenge-state file remained.
- Final external checks returned 200 for WEF HTTPS, API readiness, Fillable HTTPS
  on 3200 and Forecast HTTP on 3000.
- All 16 protected containers retained their IDs, images, start times, health,
  runtime status and published ports. Only DuckDNS was intentionally recreated;
  WEF production containers were recorded separately because an independent
  release workflow was already in progress when maintenance began.
- Documentation validation: `make lint` and `make format-check` passed using the
  existing pinned Docker runtime wrappers; `make test` passed with 2,304 backend
  and 357 frontend tests and 100% enforced coverage. Repository Markdown links
  and `git diff --check` passed. No API or application code changed, so contract
  regeneration was unnecessary.

## Recovery boundary

Before-state files and container snapshots are retained privately, mode 0700,
under `/home/nuc/wef-shared-edge/changes/retire-domain-20261020/`. They include the
old DDNS environment and DNS hook, edge state/pointers and non-secret container
identities. Do not copy the DDNS environment or certificate account/key material
into Git, logs or artifacts.

The edge's `previous` pointer retains `r-20260908-fillable-tls`. A deliberate
rollback requires inspecting its configuration, validating it and gracefully
reloading Nginx; that historical configuration restores alias support and the
temporary Origin rewrite, so reapply this retirement before declaring cleanup
complete. Retain the valid single-domain certificate and current SSH/DDNS targets
when recovering application routing. Restoring the deleted name to a DNS update
or certificate request will fail while the owner does not control it.

No database, application volume, export, source media, Telegram session or VPN
configuration was removed. This maintenance does not claim off-host backups or
change the documented single-host recovery limits.
