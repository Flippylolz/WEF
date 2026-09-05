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
| **`telegram-worker`** | yes (`WEF_GEOAPIFY_API_KEY`) | yes, when explicitly activated | `wef-accept-pending-geocode-pins`, backfill, worker status |
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

### GitHub Actions alternative: parser replay

`wef-replay-parser` can also be run without NUC shell access via the
**Replay parser over raw archive** workflow (`replay-parser.yml`, manual
dispatch): type `REPLAY` in the `confirm` input and optionally enable
`seed_archive`. It runs
`docker compose ... run --rm --no-deps api wef-replay-parser` on the NUC with
the deploy SSH identity and prints the replay counts JSON in the run summary.
Use it for contact backfill after the contact-cipher fix (#301) and for
canonical renames after E23 normalization lands.

## Groq rate and application budgets

Manual place review, owner enrichment, ingestion parse and scheduled recovery share
one durable allocation of **20 generation items per owner per UTC day**. The
ledger permits one in-flight item and at least 60 seconds between starts. Initial
cutover includes pre-ledger usage for that owner/day; drain old writers first.
Provider-side limits remain independent and must be checked in the account.

Under E25 revision 2, all composed Groq work uses single-item Chat Completions
with `openai/gpt-oss-20b`; no ZDR path calls Batch/Files. Legacy batch settings do
not select another transport. Cohorts are durable application work, and their
items reserve the same allocation before each request. Inputs are bounded to
5,500 estimated tokens and outputs to 1,500 tokens, with a 30-second attempt
timeout. Uncertain attempts count and are not automatically resent. Quota/429
deferrals retain their next eligible time across restarts.

Prerequisites for any Groq-backed command: `WEF_AI_CURATION_ENABLED=true`,
`WEF_GROQ_ZDR_VERIFIED=true`, `WEF_GROQ_API_KEY` set, exact model allowlist, and
**`api` attached to `provider-egress`** (see [DEPLOYMENT.md](DEPLOYMENT.md)).

---

## Parse-issue ledger (E21)

### `wef-backfill-parse-issues`

**Container:** `api` or `telegram-worker` (database access only; no provider calls).

**Purpose (E25-T1):** Evaluate current retained source revisions, including linked
offers, under the running parser and `source-evidence-v2` classification policy.
The command writes classification and issue-lifecycle metadata only. It does not
change canonical offers, call providers, or activate historical parser recovery.

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | `100` | Max current revisions considered in this invocation |
| `--batch-size` | `10` | Transaction size, capped at 10 even when a larger value is supplied |

**Output (JSON):** `processed`, `inserted` (legacy issue rows), `skipped_clean`
(no new legacy issue insert, including duplicate/stale evaluations), and `batches`.
These counts describe this invocation, not field accuracy or unique missed offers.

Selection uses source-message UUID keyset order and excludes already evaluated
source/parser/policy identities. Evaluations persist for clean, irrelevant and
source-absent records too, so those records cannot starve later pages. After a
restart, committed observations are skipped and incomplete work remains eligible.
Deleted messages are excluded. No old ledger rows or source payloads are deleted.

```bash
$COMPOSE exec -T api wef-backfill-parse-issues --limit 100 --batch-size 10
```

Compare the old ledger count with current classified eligibility before production
queue rollout; these denominators intentionally differ. This aggregate query
contains no source text:

```sql
SELECT pe.classification, count(*) AS current_source_revisions,
       count(*) FILTER (WHERE pe.recovery_eligible) AS recovery_eligible
FROM parse_evaluations pe
JOIN source_messages sm ON sm.id = pe.source_message_id
WHERE pe.source_message_revision_id = sm.current_revision_id
  AND pe.state = 'open' AND sm.deleted_at IS NULL
GROUP BY pe.classification ORDER BY pe.classification;

SELECT count(*) AS legacy_parser_miss_rows
FROM source_message_parse_issues WHERE issue_outcome = 'parser_miss';
```

Unclassified legacy rows remain inspectable but cannot automatically qualify for
expensive recovery. Admin JSON/CSV exports retain `issue_outcome` and add
`classification`, `lifecycle_state`, `recovery_eligible` and `policy_version`.

See also [PIPELINE.md](../ingestion/PIPELINE.md) (parse-issue ledger).

---

## Property type backfill (E22)

### `wef-backfill-property-type`

**Container:** `api` (database access only; no provider calls).

**Purpose:** Re-extract `offers.property_type` from the newest **primary**
`offer_sources` revision per offer using parser `e2-v11`. Dry-run by default;
`--apply` persists changed values only.

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | none (unbounded) | Max **offers** to process in this run (after dedupe) |
| `--apply` | off | Persist changed `property_type` values |

**Output (JSON):** aggregate counts only — no raw source text.

| Field | Meaning |
|-------|---------|
| `total` | Distinct offers with a primary source revision processed |
| `apartment` / `house` / `semi_detached` / `unknown` | Extracted classification buckets |
| `conflicts` | Offers where property-type evidence conflicted → `unknown` |
| `failures` | Offers where listing extraction failed |
| `changed` | Offers whose stored value would differ (dry-run) or did differ (apply) |
| `unchanged` | Offers already matching extracted value |
| `parser_version` | Classifier version used for replay |

**Idempotent:** safe to rerun; a second dry-run after `--apply` should report
`changed: 0`.

**Review guardrails before `--apply`:**

- `total` should approximate `SELECT count(*) FROM offers` minus offers without
  any primary source (typically a small gap).
- Investigate non-zero `failures` — often non-listing primary sources or missing
  replayable payload.
- Investigate `conflicts` — conflicting multilingual category phrases; stored as
  `unknown` by design.
- Spot-check a few `changed` offers in admin or offer detail after apply.

**Recommended workflow:**

```bash
# 1. Dry-run after deploy (migration 20260902_0019 must be at head)
$COMPOSE exec -T api wef-backfill-property-type | tee /tmp/property-type-backfill-dry-run.json

# 2. Optional bounded trial
$COMPOSE exec -T api wef-backfill-property-type --limit 500

# 3. Apply when counts look reasonable
$COMPOSE exec -T api wef-backfill-property-type --apply | tee /tmp/property-type-backfill-apply.json

# 4. Confirm idempotency
$COMPOSE exec -T api wef-backfill-property-type
# expect "changed": 0

# 5. Smoke public API/UI
curl -sS "$WEF_PUBLIC_HTTPS_BASE_URL/api/v1/filter-facets" | jq '.property_types'
curl -sS "$WEF_PUBLIC_HTTPS_BASE_URL/api/v1/map/locations?bbox=20.9,52.1,21.2,52.4&property_type=apartment" | jq '.features | length'
```

See [E22 implementation plan](../epics/E22-property-type-filter/IMPLEMENTATION_PLAN.md).

### `wef-backfill-location-display-name`

**Container:** `api` (database access only; no provider calls).

**Purpose:** Recompute `locations.display_name` and `display_address` for
**non-operator-verified** locations from the newest primary `offer_sources`
revision per location using E23-T1 Polish-forward templates. Dry-run by default;
`--apply` persists changed display fields only. Never changes
`normalized_address_hash`.

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | none (unbounded) | Max **locations** to process in this run (after dedupe) |
| `--apply` | off | Persist changed `display_name` / `display_address` values |

**Output (JSON):** aggregate counts only — no raw source text.

| Field | Meaning |
|-------|---------|
| `total` | Distinct non-verified locations with replayable primary source evidence |
| `changed` | Locations whose stored display fields would differ (dry-run) or did differ (apply) |
| `unchanged` | Locations already matching the normalized template |
| `skipped_verified` | Locations with operator geocode lineage (`actor_type=operator`) — owner-curated |
| `failures` | Locations where listing/location extraction failed or row processing errored |

**Idempotent:** safe to rerun; a second dry-run after `--apply` should report
`changed: 0`.

**Review guardrails before `--apply`:**

- `skipped_verified` should match locations the owner placed or corrected in
  `/admin/places`.
- Investigate non-zero `failures` — often missing location lines in archived
  source text.
- Spot-check a few `changed` locations on the map and in offer detail.
- Fragment-only names that remain unusable after apply stay E18 curation cases.

**Recommended workflow:**

```bash
# 1. Dry-run full cohort (requires E23-T1 deployed)
$COMPOSE exec -T api wef-backfill-location-display-name | tee /tmp/location-display-backfill-dry-run.json

# 2. Optional bounded trial
$COMPOSE exec -T api wef-backfill-location-display-name --limit 200

# 3. Apply when counts look reasonable
$COMPOSE exec -T api wef-backfill-location-display-name --apply | tee /tmp/location-display-backfill-apply.json

# 4. Confirm idempotency
$COMPOSE exec -T api wef-backfill-location-display-name
# expect "changed": 0

# 5. Smoke map/list labels
curl -sS "$WEF_PUBLIC_HTTPS_BASE_URL/api/v1/map/locations?bbox=20.9,52.1,21.2,52.4" | jq '.features[0].properties.display_name'
```

See [E23 implementation plan](../epics/E23-location-display-name-normalization/IMPLEMENTATION_PLAN.md).

### `wef-batch-ingestion-ai-parse`

**Container:** **`api` only** (Groq).

**Purpose:** Operator batch alternative to `/admin/ingestion-issues` **Generate** /
**Apply**. Selects distinct current source revisions with an open, recovery-eligible evaluation and no primary offer, calls the same application
interactors as the admin UI, and prints redacted success/skip counts.

| Flag | Default | Description |
|------|---------|-------------|
| `--owner-id` | auto | Owner UUID; if omitted, uses `WEF_BOOTSTRAP_OWNER_USERNAME` when set (matched against `users.username_normalized`), otherwise the owner with the most `ingestion_ai_parse_runs` history (ties: oldest `created_at`) |
| `--limit` | `10` | Max **distinct** candidates (deduped by source-text hash) |
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
  "groq_batch_jobs": 1,
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

# 2. Generate + apply up to daily budget (one Groq Batch job per run)
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

**After a backend release that changes geocoding behavior**, recreate the worker so
it runs the new image (ordinary `compose up -d` may leave the old container running):

```bash
$COMPOSE up -d --force-recreate telegram-worker
```

On releases **before** the geocode-claim cleanup fix (#280, `2bebdfeb+`), completed
`geocode_miss_claims` rows could block cycles with `CacheWaitExpiredError`. On those
releases only, clear completed claims (safe once results are in `geocode_results`):

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

Current releases (`2bebdfeb+`) delete completed claims automatically in
`complete_miss`; `miss_claims` should stay near **0** when recurring geocode is healthy.

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
| `wef-backfill-property-type` | E22 property-type dry-run/apply backfill |
| `wef-backfill-location-display-name` | E23 location display-name dry-run/apply backfill |
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
- [E22 epic](../epics/E22-property-type-filter/README.md) — property type classification and filter
- [E23 epic](../epics/E23-location-display-name-normalization/README.md) — location display name normalization

## E25 automatic parser exception recovery

Migration `20260905_0023` adds provider reservations and recovery checkpoints. It
performs no provider requests or canonical backfill. Stop old AI writers before
activation; the first reservation includes that day's pre-ledger owner usage.

Release-owned settings default off: `WEF_AI_RECOVERY_ENABLED`,
`WEF_AI_RECOVERY_ACTIVATION_VERIFIED`, `WEF_AI_RECOVERY_AUTO_APPLY`, and
`WEF_AI_RECOVERY_OWNER_ID` (an active existing owner UUID). Activation verification
means recorded ZDR, permission for masked descriptions, credentials, exact model
and free-allocation evidence. Set enabled plus verified for generation/validation
observation; leave auto-apply false until calibration and canary evidence is accepted.
The existing `WEF_AI_CURATION_ENABLED` and `WEF_GROQ_ZDR_VERIFIED` must also be true.
These settings are delivered through the existing release workflow; no new service
or scheduler is needed. No provider configuration was activated by E25 development.

The worker yields to live ingestion, selects at most 100 eligible identities in
ten-record transactions and performs at most one scheduled generation per minute.
Classification maintenance evaluates ten sources per tick. Claims last 120 seconds.
Quota and rate-limit deferrals resume automatically; three local systemic failures
produce one terminal reason. An uncertain submission consumes quota and is never
resent automatically. Pausing submissions retains work and proposals; pausing apply
retains observations and prevents scheduled canonical writes. Existing owner cohorts
use the same allocation and single-item transport.

Inspect aggregate state in the restricted database session (no source text needed):

```sql
SELECT state, reason, count(*) FROM ai_recovery_work GROUP BY state, reason;
SELECT state, reason, count(*), sum(token_input), sum(token_output)
FROM ai_provider_attempts
WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
GROUP BY state, reason;
SELECT budget_day, sum(used) FROM ai_provider_accounts GROUP BY budget_day;
```

Keep work counts mutually exclusive; compare queued, deferred, observed, applied,
terminal and superseded totals against considered unique identities. Report the
observation-only and unsupported families separately. Provider spend is unavailable
unless independently verified from the authorized account; token counts are not a
billing statement. Record human interventions from actual operator/audit actions
during the representative 24-hour acceptance window. That live evidence remains
outstanding; fake-provider tests do not establish it.

Runtime rollback first disables scheduling/application and retains additive metadata.
Do not erase reservations to regain quota or reset uncertain work for automatic retry.
Existing field-origin guarded rollback remains authoritative for enrichment fills.
T4 historical parser convergence has separate dependency and rollout gates.

## Historical parser replay (E25-T4)

Deploy migration 0024 before the worker. Release-owned `WEF_PARSER_REPLAY_ENABLED`
and `WEF_PARSER_REPLAY_AUTO_APPLY` default to false and work independently of Groq
configuration. Enable scheduling for read-only observation; the separate application
flag permits guarded application only after automatic canary promotion. Accepted
parser/policy identity is a reviewed code artifact beside the regression benchmark.
Do not relabel an unvalidated parser version as accepted to drain the queue.

The existing live worker checks once per 60 seconds. It selects at most 100 records
in transactions of at most 10, claims one record globally at a time, yields to
unhealthy/busy live ingestion and stops its processing loop after five seconds.
Claims last 120 seconds. Local failures release claims with 60/120-second backoff;
a third failure is terminal. Source edits create independent work identities.
No geocoding, media or inference provider is called by parser replay.

Read-only aggregate diagnostics:

```sql
SELECT version, phase, reason FROM parser_replay_releases ORDER BY created_at;
SELECT release_version, state, reason, count(*)
FROM parser_replay_work GROUP BY release_version, state, reason;
SELECT w.release_version, count(*) AS field_events,
       count(*) FILTER (WHERE e.before_value IS DISTINCT FROM e.after_value) AS changed_fields,
       count(*) FILTER (WHERE e.reverted_at IS NOT NULL) AS reverted_fields
FROM parser_replay_field_events e JOIN parser_replay_work w ON w.id=e.work_id
GROUP BY w.release_version;
```

`parser_replay_progress` logs balanced populations only when they change. Deferred
includes queued, claimed and observed records; protected-conflict includes partial
safe repairs. Check field-event aggregates separately. A second completed pass for
the same source/release must create zero canonical writes and zero new lineage.
Keep the deployment acceptance denominator, source exclusions, conflicts and actual
production version distribution separate from synthetic test counts.

Pause scheduling/application with the two release flags while preserving metadata.
For exceptional reversal, the bounded `rollback_parser_work(session_factory,
work_uuid, utc_now)` service in `ingestion/infrastructure/parser_replay_rollback.py`
reverses one reviewed job. It pauses that release and uses value/origin/source guards;
it reports reverted and protected-conflict field counts and records the outcome.
It is never called by the automatic worker. Repeat interrupted reversal safely;
do not replace it with bulk updates or dropping tables. Restarting a previous
runtime must retain the release ledger so version downgrade protection can operate.

No production replay or provider activation was performed while implementing T4.
