# Backend operator commands

This document is the canonical reference for **operator CLIs** shipped in the backend
image (`apps/backend/pyproject.toml` → `[project.scripts]`). Each command prints a
single JSON object to stdout on success and exits **2** on failure (message on stderr).

Use these tools for reviewed production catch-up. They are not invoked automatically by
live ingestion except where noted (for example `telegram-worker` runs recurring
geocode internally).

## Where to run commands

| Service | Geoapify | Groq | Typical commands |
|---------|----------|------|------------------|
| **`api`** | no (by design) | yes (`WEF_GROQ_*`) | AI parse batch, place review generate (via UI), `wef-promote-public-catalog` |
| **`telegram-worker`** | yes (`WEF_GEOAPIFY_API_KEY`) | no | `wef-accept-pending-geocode-pins`, backfill, worker status |
| **Operator one-shot** (`migrate`, `seed`, `import`, …) | varies | varies | Migrations, historical import, dry-run |

Production shell pattern (adjust paths if your host layout differs):

```bash
COMPOSE="docker compose --project-name wef-production \
  --env-file /home/nuc/wef/secrets/current/production.env \
  --file /home/nuc/wef/releases/current/compose.production.yaml"

# AI / admin (Groq)
$COMPOSE exec -T api <command> [flags]

# Geocoding (Geoapify)
$COMPOSE exec -T telegram-worker <command> [flags]
```

Local development uses the same command names inside the `api` or `telegram-worker`
Compose services (`make up`).

## Groq rate and application budgets

Two different limits apply to AI operator work:

| Limit | Window | Value | Applies to |
|-------|--------|-------|------------|
| **Groq provider RPM** | per minute | ~30 requests/min (free tier; verify in console) | Pace **all** Groq HTTPS calls |
| **WEF ingestion AI parse** | per UTC calendar day | **20** `ingestion_ai_parse_runs` / owner | `wef-batch-ingestion-ai-parse` generate steps only |
| **WEF place review + enrichment** | per UTC calendar day | **20** shared provider calls / owner | `/admin/places` review, `/admin/offer-enrichment` |

When batching Groq calls, keep **≥2 s** between generate requests (`--spacing-seconds
2.5` default) to stay under provider RPM. The WEF **daily** cap is independent: once
20 ingestion parse generates have run for the owner on the current UTC day, further
generate calls return `daily_limit` until UTC midnight.

Place review and offer enrichment share a separate daily counter; ingestion AI parse
has its own counter (`ingestion_ai_parse_runs` only).

Prerequisites for any Groq-backed command: `WEF_AI_CURATION_ENABLED=true`,
`WEF_GROQ_ZDR_VERIFIED=true`, `WEF_GROQ_API_KEY` set, exact model allowlist, and
**`api` attached to `provider-egress`** (see [DEPLOYMENT.md](DEPLOYMENT.md)).

---

## Parse-issue ledger (E21)

### `wef-backfill-parse-issues`

**Container:** `api` or `telegram-worker` (database access only; no provider calls).

**Purpose:** Populate `source_message_parse_issues` for historical Telegram messages
that predate the E21-T1 ledger. Re-runs the current deterministic parser on retained
messages that have **no** primary `offer_sources` row and **no** existing ledger row.

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | none (unbounded) | Max messages to process in this run |
| `--batch-size` | `500` | Rows committed per batch |

**Output (JSON):** counts from `backfill_parse_issues` (scanned, inserted, skipped).

**Idempotent:** safe to rerun after partial batches.

```bash
$COMPOSE exec -T api wef-backfill-parse-issues --limit 5000 --batch-size 500
```

See also [PIPELINE.md](../ingestion/PIPELINE.md) (parse-issue ledger).

### `wef-batch-ingestion-ai-parse`

**Container:** **`api` only** (Groq).

**Purpose:** Operator batch alternative to `/admin/ingestion-issues` **Generate** /
**Apply**. Selects distinct open `parser_miss` rows, calls the same application
interactors as the admin UI, and prints redacted success/skip counts.

| Flag | Default | Description |
|------|---------|-------------|
| `--owner-id` | auto | Owner UUID; if omitted, uses `WEF_BOOTSTRAP_OWNER_USERNAME` when set, otherwise the sole `users.role = 'owner'` row |
| `--limit` | `10` | Max **distinct** candidates (deduped by source-text hash) |
| `--spacing-seconds` | `2.5` | Minimum delay between **generate** calls (Groq RPM) |
| `--generate-only` | off | Generate pending runs without apply |
| `--link-existing-offers` | off | Before batching, set `source_message_parse_issues.offer_id` from primary `offer_sources` (no Groq) |
| `--min-text-length` | `120` | Minimum `source_message_revisions.text_original` length for candidates |

**Candidate filters (built-in):** excludes Serock/Dosin reposts, developer promo
templates (`застройщика`, `0% комиссии`), and rows that already have `offer_id`.

**Output (JSON):**

```json
{
  "applied": 3,
  "candidates_considered": 10,
  "generated": 5,
  "linked_existing_offers": 12,
  "skipped": {"offer_exists": 2, "daily_limit": 3}
}
```

**Skip reasons** mirror admin denials: `offer_exists`, `daily_limit`, `disabled`,
`in_flight`, `revision_not_found`, apply denials, and `AdminDeniedError` messages
(for example `proposal missing required fields`). Unapplyable pending runs are
marked **`failed`** on apply so the revision is not blocked until the 24-hour expiry.
Generate also persists **`proposal_incomplete`** as `failed` when Groq omits required
apply fields (`location`, `apartment_price_min`, `currency`).

**Recommended workflow:**

```bash
# 1. Link ledger rows that already have offers (no Groq quota)
$COMPOSE exec -T api wef-batch-ingestion-ai-parse --link-existing-offers --limit 0

# 2. Generate + apply up to daily budget, paced for Groq RPM
$COMPOSE exec -T api wef-batch-ingestion-ai-parse --link-existing-offers --limit 20

# 3. Geocode + map-ready promotion on worker (do not run parallel manual geocode)
$COMPOSE exec -T telegram-worker wef-accept-pending-geocode-pins
# Worker also runs promote_map_ready_offers each recurring_geocode cycle.
```

**Do not** use `wef-promote-public-catalog` for single-offer E21 recovery — it
publishes every `needs_review` offer, including listings still without map pins.

Applied offers use `parser_version=ai-parse-v1` and link `offer_id` on parse issues
(E21-T3).

---

## Catalog visibility and geocoding

### `wef-promote-public-catalog`

**Container:** `api`.

**Purpose:** Historical bulk promotion — hide synthetic M1 seed and set **all**
non-synthetic `needs_review` offers to `visible`. Does **not** require map pins.

Use only for deliberate catalog-wide promotion passes, not live E21 recovery.

### `wef-accept-pending-geocode-pins`

**Container:** **`telegram-worker`** (Geoapify environment; not on `api` by design).

**Purpose:** Accept in-scope pending geocode results onto locations (`manual_accept`
lineage). **Output:** `locations_accepted`, `map_eligible_locations`,
`remaining_needs_review_without_point`, `remaining_ungeocoded`.

The worker's `recurring_geocode` loop also calls map-ready promotion
(`promote_map_ready_offers`) after geocoding; manual runs are for operator catch-up.

If `telegram-worker` logs `recurring_geocode_cycle_failed` with
`CacheWaitExpiredError`, stale `geocode_miss_claims` rows may be blocking the
fence. Clear completed claims (safe once results are in `geocode_results`):

```bash
$COMPOSE exec -T api python -c "
import asyncio
from sqlalchemy import text
from wef_backend.database import create_database_resources
from wef_backend.settings import load_settings
async def main():
    db = create_database_resources(load_settings().database_url)
    async with db.session_factory() as s:
        deleted = (await s.execute(text(
            \"DELETE FROM geocode_miss_claims WHERE completed_geocode_result_id IS NOT NULL RETURNING 1\"
        ))).all()
        await s.commit()
        print({\"deleted_completed_claims\": len(deleted)})
    await db.engine.dispose()
asyncio.run(main())
"
```

Releases after the geocode-claim cleanup fix delete completed claims automatically.

### `wef-revalidate-recurring-geocoder`

**Container:** `telegram-worker` (optional `--live-check` for provider probe).

**Purpose:** Report recurring geocoder policy and optional live Geoapify check.
See [GEOCODING.md](../ingestion/GEOCODING.md).

---

## Telegram worker

| Command | Purpose |
|---------|---------|
| `wef-verify-telegram-channel` | Redacted channel identity and credential readiness |
| `wef-telegram-backfill` | Bounded overlap backfill |
| `wef-telegram-worker` | Long-running worker (supervised in Compose) |
| `wef-telegram-worker-status` | Checkpoint, gap, liveness, rotation dry-run |

See [DEPLOYMENT.md](DEPLOYMENT.md) (Telegram worker operations).

---

## Historical import and maintenance

| Command | Purpose |
|---------|---------|
| `wef-import` | Historical dataset import |
| `wef-importer-dry-run` | Dry-run parser audit |
| `wef-replay-parser` | Parser replay over raw archive |
| `wef-migrate` | Alembic migrations |
| `wef-seed-m1` | M1 synthetic seed |
| `wef-bootstrap-owner` | One-time owner bootstrap |
| `wef-geocoder-check` | Geocoder probe |
| `wef-export-openapi` | OpenAPI export (build/CI) |

---

## Related documentation

- [PIPELINE.md](../ingestion/PIPELINE.md) — ingestion stages, E21 UI, AI provenance
- [UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md](../ingestion/UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md) — place review + E21 recovery runbook
- [DEPLOYMENT.md](DEPLOYMENT.md) — Groq enablement, compose topology, worker ops
- [E21 epic](../epics/E21-ingestion-ai-fallback/README.md) — parse-issue AI fallback scope
