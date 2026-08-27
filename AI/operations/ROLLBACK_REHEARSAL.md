# Production Rollback Rehearsal

This rehearsal completed under E7-T4. `AUTO_DEPLOY_ENABLED=true` is now active; use this runbook only for a deliberate repeat through `workflow_dispatch`, temporarily disabling automatic deployment if the exercise requires an isolated window.

## Safety gates

- Use two different commits already reachable from `main`: healthy release `A`, then candidate `B`.
- Keep the workflow's automatic gate false throughout a repeated rehearsal.
- Confirm the `production` environment has the documented variables/secrets and port 3100 is unoccupied.
- Do not import historical/private data. The only data is the idempotent synthetic fixture.
- Do not run Docker prune, Compose volume deletion, Alembic downgrade, or any command against a non-WEF project.

## Healthy activation

1. Dispatch `Release and deploy production` for SHA `A`.
2. Set `seed_rehearsal=true` and `force_rollback_rehearsal=false`.
3. Require verification/audits, immutable image publication, transfer checksum, remote preflight/migration, complete smoke, and non-interference comparison to pass.
4. Confirm `/home/nuc/wef/state/current.json`, `releases/current`, and `secrets/current` all identify `A`.
5. Confirm the public endpoint on port 3100 returns the `X-WEF-Release: A` marker and the synthetic map.

## Forced health-gate failure

1. Dispatch the same workflow for a newer SHA `B`.
2. Set `seed_rehearsal=false` and `force_rollback_rehearsal=true`.
3. The workflow refuses this mode unless a different active release already exists.
4. Candidate `B` must first pass the complete real smoke. The reviewed failpoint then converts that result into a deployment failure, requiring automatic rollback and previous-release smoke.
5. Exit code `42` is accepted only in this explicit manual mode. Any normal failure, missing previous release, failed rollback, wrong current SHA, or non-interference mismatch fails the workflow.

## Required evidence

- `current.json` and `previous.json` identify `A`.
- `last-failure.json` identifies candidate `B`, reason `health_verification`, restored SHA `A`, and a UTC timestamp.
- Active release/config symlinks resolve to `A`; its configuration is mode `0600`.
- Both release manifests identify their source SHA, migration revision, timestamp, and immutable backend/web digests.
- API/web/map-style smoke passes after restoration and synthetic PostGIS data remains available.
- Before/after inventory files under `/home/nuc/wef/state/` prove existing Compose projects, containers, watched non-WEF listeners, and HTTP services unchanged; WEF services are healthy on 3100.

The workflow runs `verify_rollback_rehearsal.py` over this evidence without reading or printing secret configuration values.

## Enable or abort

After a repeated rehearsal, restore `AUTO_DEPLOY_ENABLED=true` only after both dispatches and all evidence pass. The normal merged-PR `main` deployment path is already proven and active.

On any failure, leave the variable false. If rollback cannot restore health, stop only WEF application services, retain PostgreSQL/media/Caddy paths, and record the blocker. Never delete or restart another project.
