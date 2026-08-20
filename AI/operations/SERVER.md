# Production Server Baseline

This document records read-only inspection of the supplied production host on 2026-08-12. Re-run the inventory immediately before deployment because ports, containers, and capacity can change.

## Access

- SSH: `nuc@2fa54e2405.duckdns.org`
- Public DNS observed: `2fa54e2405.duckdns.org` → `79.184.113.242`
- SSH port: 22/TCP
- SSH key authentication works non-interactively.
- User `nuc` can run Docker/Compose directly.
- Passwordless sudo is not available. No sudo credential is recorded; request it from the owner only when a genuinely necessary privileged operation cannot be avoided.

Do not store SSH private keys, known-host material, or server secrets in Git.

## Hardware and operating system

- Hostname: `asusnuc`
- Model: ASUS NUC15CRHC3
- Operating system: Ubuntu 24.04.4 LTS
- Kernel: Linux 6.8.0-111-generic
- Architecture: x86-64
- CPU: Intel Core 3 100U, 6 physical cores / 8 logical CPUs, up to 4.7 GHz
- RAM: approximately 7.3 GiB total; 6.3 GiB available during inspection
- Swap: 4 GiB, unused during inspection
- Disk: approximately 954 GB NVMe
- Root filesystem: 936 GB ext4 on LVM; approximately 877 GB free during inspection

The host has sufficient initial disk and idle memory for WEF, PostgreSQL/PostGIS, and the existing dataset. Full media processing and any self-hosted geocoder still require resource limits and a benchmark because this is a shared 8 GB host.

## Docker

- Docker Engine/client: 29.5.1
- Docker Compose: 5.1.3
- Storage driver: overlayfs
- Docker root: `/var/lib/docker`
- Cgroup driver: systemd
- Docker reports 8 logical CPUs and approximately 7.3 GiB memory.

WEF uses Compose project name `wef-production`, its own default network, its own volumes/bind mounts, and no explicit generic `container_name` values.

## Existing workloads

### `ai-forecast-production`

- Compose file: `/home/nuc/ai-forecast/docker-compose.production.yml`
- Services:
  - `ai-forecast-frontend`: `dmitryleschenko/ai-forecast:frontend-1.0.5`, host 3000/TCP → container 3000.
  - `ai-forecast-backend`: `dmitryleschenko/ai-forecast:backend-1.0.5`, host 8080/TCP → container 8080.
  - `ai-forecast-db`: `postgres:18`, internal 5432 only, healthy.
- Network: `ai-forecast-production_default` (`172.19.0.0/16` observed).
- Persistent volumes:
  - `ai-forecast-production_postgres_data`
  - `ai-forecast-production_backend_data`
- Restart policy: `unless-stopped`.

WEF must not connect to, reuse, restart, rename, or prune these containers, volumes, or network.

### `duckdns-ddns`

- Compose file: `/home/nuc/duckdns-ddns/docker-compose.yml`
- Container: `duckdns`
- Image: `lscr.io/linuxserver/duckdns:latest`
- Bind mount: `/home/nuc/duckdns-ddns/config` → `/config`
- No published container port.
- Restart policy: `unless-stopped`.

Do not inspect or copy the DuckDNS configuration secret.

### `wireguard`

- Compose file: `/home/nuc/wireguard/docker-compose.yml`
- Container: `wireguard`
- Image: `lscr.io/linuxserver/wireguard:latest`
- Host port: 51820/UDP
- Bind mount: `/home/nuc/wireguard/config` → `/config`
- Network: `wireguard_default` (`172.18.0.0/16` observed).
- Restart policy: `unless-stopped`.

Do not inspect/copy VPN configuration or change host networking/kernel modules.

### Other Docker/network artifacts

- An unused/down `valheim-net` bridge was present.
- One anonymous local volume was present.
- WEF cleanup commands must target the `wef-production` project explicitly; never use global volume/network prune in deployment.

## Network and ports

Observed host addresses:

- LAN: `192.168.1.25`
- Tailscale: `100.127.193.23`
- Public DNS address: `79.184.113.242`

Observed listeners:

- 22/TCP: SSH
- 3000/TCP: AI Forecast frontend
- 8080/TCP: AI Forecast backend
- 51820/UDP: WireGuard
- 41641/UDP and Tailscale-specific high TCP ports

Ports 80/TCP and 443/TCP were not listening during inspection. Caddy, Nginx, and Apache system services were inactive.

The current AI Forecast application is reachable at `http://2fa54e2405.duckdns.org:3000/`. WEF uses configurable `WEF_PUBLIC_PORT`, initially confirmed as `3100/TCP`, subject to router/firewall forwarding.

External checks on 2026-08-12 found:

- 3000/TCP accepted connections.
- 3100/TCP timed out.
- 80/TCP and 443/TCP accepted a TCP connection externally, but HTTP/HTTPS requests timed out and the NUC had no corresponding listener.

The owner reports that a router rule now forwards 3100/TCP. The external check still times out while no WEF service is listening, so forwarding/firewall behavior must be verified again after Caddy binds 3100.

Privileged UFW/router configuration still needs an interactive, non-logged administrative check. Before deployment, confirm:

- Router/NAT forwarding from the public address to `192.168.1.25` reaches the WEF listener.
- Host/provider firewall allowance.
- Whether the initial endpoint may use plain HTTP or must use HTTPS.

Public launch should use HTTPS. A high non-standard HTTPS port or DNS challenge requires additional shared-ingress/DuckDNS design; plain `http://...:3100` should be treated as an interim deployment, not the final security posture.

[ADR-020](../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) selects Nginx as the target public web server with Certbot/Let's Encrypt auto-renewal. Owner amendment via [D-009](../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md): the initial E7-T10 cutover is **WEF-only** on `2fa54e2405.duckdns.org`; AI Forecast remains on port 3000. This does not change the observed/current listeners above until gated [E7-T10](../epics/E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md) completes. [E7-T8](../epics/E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md) and [E7-T9](../epics/E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md) proved inert topology/automation. Until live cutover, Caddy/3100 and AI Forecast/3000 remain current facts.

## Deployment paths

`/srv` is owned by root and is not writable by `nuc`. Use:

- `/home/nuc/wef/releases/` — release manifests and Compose/Caddy files.
- `/home/nuc/wef/secrets/releases/<git-sha>/` — deploy-generated mode-0600 complete environment/service configuration from GitHub Actions variables/secrets.
- `/home/nuc/wef/secrets/current` — atomically switched pointer to the active configuration release.
- `/home/nuc/wef/postgres/` — WEF PostgreSQL/PostGIS persistence.
- `/home/nuc/wef/media/` — imported media and derivatives.
- `/home/nuc/wef/imports/incoming/` — resumable incoming source archives.
- `/home/nuc/wef/imports/extracted/` — read-only extracted source mounted into importer jobs.
- `/home/nuc/wef/caddy-data/` — Caddy state when used.

Directories should be owned by `nuc`, default mode `0750`; secret files use `0600`. The inactive PostgreSQL root starts as `nuc:0700`; immediately before database startup, the bounded no-network `db-permissions` service changes that root only to the pinned PostGIS UID/GID `999:999`. Caddy runs as the NUC's UID/GID `1000:1000` and retains ownership of its data root. No sudo or recursively broad permission is used.

GitHub Actions variables/secrets are the deployment configuration source of truth. Each release transfers complete config to temporary files, validates it, and atomically activates it; transfer files are deleted and values never enter Git/logs/images.

### E7-T2 preparation evidence

On 2026-08-13 UTC, strict known-host/batch SSH prepared only the WEF boundary:

- Created `/home/nuc/wef` and its release, media, import, Caddy, state, and log directories as owner `nuc` with mode `0750`.
- Created `secrets`, `secrets/releases`, and `postgres` with mode `0700`.
- Transferred the inert E7-T1 manifests/scripts for commit `394329cb6a1a00f97c9a8533336667d1c072d2ac` to its versioned release directory with mode `0640`/`0750`.
- Validated complete-config and Compose rendering with a temporary non-default fixture, then removed the fixture. No active environment, current/previous release state, application image, container, network, or database was created.
- Recorded approximately 941 GB free disk and 6.35 GiB available memory after preparation; 3100/TCP remained unbound.
- Automated before/after comparison proved the existing three Compose projects, five container/image identities, health/state/port bindings, watched listeners, and HTTP checks on 3000/8080 were unchanged.
- No source export, media payload, credential, session, or sudo password was transferred.

External 3100/router verification was deliberately not attempted because no immutable WEF images or edge listener exist while B-006 is active. E7-T4 performs that check only during the bounded release/rollback rehearsal.

### E7-T3 deployment-identity preparation evidence

On 2026-08-13 UTC:

- Created the GitHub `production` environment and repository variables for host/user/ports, database identity, bind/log settings, and `AUTO_DEPLOY_ENABLED=false`.
- Stored only three environment secrets: a generated production database password, the strict known-host material, and a new dedicated Ed25519 deployment private key. Values were piped directly to GitHub and were not printed or written into the repository.
- Appended the corresponding public key to `nuc`'s `authorized_keys` without removing or changing existing keys, set the existing SSH file modes defensively, and proved batch login with that dedicated identity.
- Kept GHCR authentication ephemeral: the workflow uses its job-scoped package-read token during the remote pull and logs out in its exit trap; no registry token is stored on the host.
- Did not create a production config/release, start a container, bind port 3100, touch existing Compose projects, or enable automatic SSH. Hosted execution remains blocked by B-006, and E7-T4 owns the first bounded activation.

### E7-T4 bind-permission proof

On 2026-08-13 UTC, a temporary directory under `/home/nuc/wef/state` proved the pinned PostGIS UID 999 cannot write a native `nuc:0700` bind, while the exact no-network/read-only-root initializer with only `CHOWN` and `DAC_OVERRIDE` changes that one root to `999:999` and makes it writable. The trap changed the temporary directory back to `nuc`, removed it, and left the real inactive `/home/nuc/wef/postgres` at `nuc:0700`. Pulling the public pinned PostGIS image started no service and changed no active project.

## Local dataset transfer

The preferred transfer sends the single compressed archive rather than approximately 25,000 individual files:

1. Calculate SHA-256 for local `est-test.tar.gz`.
2. Create `/home/nuc/wef/imports/incoming/`.
3. Use resumable rsync over SSH without compression (the tarball/media are already compressed):

```text
rsync -a --partial --append-verify --info=progress2 \
  est-test.tar.gz \
  nuc@2fa54e2405.duckdns.org:/home/nuc/wef/imports/incoming/
```

4. Calculate SHA-256 on the server and compare exactly.
5. Extract into a checksum/version-specific directory under `/home/nuc/wef/imports/extracted/`.
6. Mark the extracted source read-only and mount it read-only into the importer.
7. Run dry-run, canonical import, geocoding, media verification/copy, and reconciliation reports.
8. Remove the transferred archive only after the source checksum, canonical import, and media checks are verified.

The server has `rsync`, `tar`, and `sha256sum` installed. Do not send both the archive and already extracted directory unless troubleshooting requires it. Do not put either in Git, GHCR, Docker images, or GitHub Actions artifacts.

The import location is not a staging application environment; the project intentionally has only local development and production for now.

## Data persistence

- Canonical/raw message data, parsed records, geocode cache, ingest runs, and Telegram checkpoints: WEF-owned PostgreSQL/PostGIS.
- Photos/videos and generated derivatives: `/home/nuc/wef/media/`, referenced by opaque database keys.
- Source archive/extraction: `/home/nuc/wef/imports/`, read-only during import and not used as the live application database.
- Telegram session when added later: the active deploy-managed service secret beneath `/home/nuc/wef/secrets/current`, never PostgreSQL/Git/logs.
- Backups: out of scope initially. All data currently has a single-host failure domain; see [ADR-015](../decisions/adr/ADR-015-defer-backups.md).

Containers may be recreated without losing these paths. A Docker image or container writable layer is never treated as persistent storage.

## No-staging policy

- Environments: local development and production only.
- Pull-request CI uses ephemeral containers/fixtures, not a persistent staging deployment.
- Production changes use immutable SHA images, compatibility-tested migrations, health checks, and application-image rollback. Data rollback is not guaranteed without backups.
- Initial deployment/rollback rehearsal uses production infrastructure with synthetic/empty data before the historical import.

## Pre-deploy non-interference check

Capture before and after:

- `docker compose ls`
- Running container names/images/status
- Published/listening ports
- Existing project volume/network names
- Free memory/disk
- HTTP checks for the existing 3000 and 8080 services

Abort if:

- The selected WEF port is occupied.
- Existing container/project state changes unexpectedly.
- Disk/memory headroom falls below agreed limits.
- A command would run global Docker prune or target a non-WEF resource.
- A migration is not backward-compatible with the retained application release or has an unaccepted data-loss path.
