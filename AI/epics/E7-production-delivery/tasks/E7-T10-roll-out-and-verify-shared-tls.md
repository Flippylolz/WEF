---
schema: ai-workflow/task@1
id: E7-T10
epic: E7
title: "Roll out and verify WEF-only shared TLS"
status: done
revision: 2
priority: P1
size: M
milestone: M3
dependencies: [E7-T9]
requirement_ids: []
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-019, ADR-020]
deferred_decision_ids: []
promotion:
  source: ../tasks/E7-T10-roll-out-and-verify-shared-tls.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T13:45:55Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T13:45:55Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 7
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T13:45:55Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T13:45:55Z"
  evidence:
    - "E7-T9 | done | PRs #106/#107"
    - "D-009 | resolved | WEF 2fa54e2405.duckdns.org; Forecast :3000 only (PR #119)"
branch:
  required: true
  name: feat/E7-T10-wef-only-shared-tls
  task_id: E7-T10
  one_task_only: true
  created_at: "2026-08-20T13:59:05Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/121"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T14:22:18Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/121"
  evidence:
    - "Tooling: merged https://github.com/Flippylolz/WEF/pull/121 (optional Forecast vhost; WEF-only production render)"
    - "Live NUC: wef-shared-edge on /home/nuc/wef-shared-edge; release r-20260820-wef-only; config tls-redirect"
    - "Production Let's Encrypt cert CN/SAN 2fa54e2405.duckdns.org; issuer YE2; expiry 2026-11-18"
    - "External smoke: https://2fa54e2405.duckdns.org/ and /api/v1/health/ready → 200; http→https 301; Forecast :3000 and Caddy :3100 → 200"
    - "certbot renew --dry-run succeeded; daily cron 04:15 UTC via shared_edge_renew.sh"
    - "Inventories: /home/nuc/wef/state/e7-t10/inventory-before.json and inventory-after.json (on NUC, not committed)"
---

# E7-T10: Roll out and verify WEF-only shared TLS

## Outcome

Activate and verify the shared Nginx/Certbot edge for **WEF** on `2fa54e2405.duckdns.org` with valid public TLS, unattended renewal, WEF health evidence, and rehearsed rollback. AI Forecast remains on public host port **3000** and is not terminated by this edge.

## Scope

- Confirm WEF hostname DNS and public TCP 80/443 reach the NUC (D-009 evidence).
- Adapt shared-edge tooling for optional Forecast hostname; production config is WEF-only.
- Capture sanitized before inventory; keep Caddy `:3100` and Forecast `:3000` as rollback paths.
- Start HTTP-only ACME bootstrap, staging then production certificate for `2fa54e2405.duckdns.org`, validate, activate TLS.
- Move WEF public routing to Nginx while retaining `:3100` until WEF smokes pass.
- Enable HTTP→HTTPS redirect for the WEF hostname only after WEF HTTPS is healthy.
- Prove Forecast `:3000` health before/after; do not change Forecast Compose/image/data.
- Prove renewal dry-run, success-only reload hook, external chain/hostname/expiry, and rollback.
- Capture sanitized after inventory without committing certs or production edge secrets.

## Out of scope

- Second hostname / Nginx TLS for AI Forecast (deferred).
- Sensitive WEF feature enablement (E7-T7), historical public activation (E7-T11), DNS-01, paid certs, backups.
- Destructive cleanup of `:3100`/`:3000` listeners without a separate owner action.

## Affected modules

- `scripts/deploy/shared_edge_*.py`, `scripts/prove_shared_edge_*.py`, `infra/nginx/*.in`, operations docs, NUC shared-edge root (operator path).

## Acceptance criteria

- [x] D-009 remains resolved; staging/production ACME for `2fa54e2405.duckdns.org` succeeds.
- [x] Nginx owns public 80/443; every reload follows passing config validation.
- [x] WEF has a valid public certificate chain and correct web/API/media upstreams through HTTPS.
- [x] HTTP redirects to `https://2fa54e2405.duckdns.org` only after WEF HTTPS smoke passes.
- [x] Certbot renew `--dry-run` and success-only deploy hook reload pass.
- [x] WEF web/API/media/release-marker smoke passes without exposing Next.js/FastAPI ports.
- [x] AI Forecast remains healthy on `:3000`; image/data/API unchanged.
- [x] Before/after inventory shows DuckDNS, WireGuard, PostgreSQL, WEF persistence, and unrelated workloads unchanged.
- [x] Failures abort/roll back without taking Forecast offline.
- [x] No certificate private keys, ACME account material, or generated production edge secrets are committed.

## Rollback

Restore previous validated Nginx config or drop back to Caddy `:3100` for WEF; leave Forecast `:3000` untouched. Preserve cert state unless a separate owner cleanup is approved.

## Live cutover notes (2026-08-20)

- Shared-edge root: `/home/nuc/wef-shared-edge/root` (outside `/home/nuc/wef` cleanup boundary).
- Ops copy of templates/scripts: `/home/nuc/wef-shared-edge/ops` (synced from main after PR #121).
- WEF upstreams joined to `wef-edge` as `wef-api` / `wef-web`; `wef-media` via dedicated media-edge container. After a WEF container recreate, run `/home/nuc/wef-shared-edge/ops/reconnect-wef-upstreams.sh` until cutover overlay is the default deploy path.
- Caddy on `:3100` intentionally retained as rollback.
