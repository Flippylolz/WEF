# Ungeocoded backlog and AI-assisted recovery

This runbook records production enablement for Groq place review, the first
AI-assisted geocode recovery pass (2026-08-31), and how operators should clear
the remaining `ungeocoded` locations without confusing the two AI workflows.

## Two different AI tools

| Tool | Admin path | Purpose | Map pins? |
|------|------------|---------|-----------|
| **Place review** | `/admin/places` → **Review with AI** | Read masked Telegram source text; propose corrected display name, address, or canonical Warsaw district | Indirectly — apply address/district, then geocode |
| **Offer enrichment** | `/admin/offer-enrichment` | Fill **missing** offer fields (price, rooms, area, floor, etc.) from source text | No |

Place review does **not** invent coordinates. After an address apply the location
returns to `needs_review`; the recurring geocoder or an operator geocode pass must
still resolve and accept a pin.

## Production enablement checklist

All gates are required (`AiCurationRuntime.active` fails closed otherwise).

1. Store `WEF_GROQ_API_KEY` in GitHub Actions secrets (never in git).
2. Owner verifies **Zero Data Retention** in the [Groq Data Controls](https://console.groq.com/settings/data-controls).
3. Set GitHub Actions variables:
   - `WEF_GROQ_ZDR_VERIFIED=true`
   - `WEF_AI_CURATION_ENABLED=true`
   - `WEF_GROQ_MODEL=openai/gpt-oss-20b` (exact allowlist)
   - `WEF_GROQ_TIMEOUT_SECONDS=30` (optional)
4. Deploy so `build_release_config` transfers Groq keys into `production.env`.
5. Ensure **`api` is attached to `provider-egress`** in `compose.production.yaml`
   (same as `telegram-worker`). The internal-only `application` network blocks DNS
   and outbound HTTPS; Groq calls from `api` fail with `network` / DNS errors without
   `provider-egress`.
6. Restart `api` after secret or Compose network changes.

Verify inside the API container (redacted):

```bash
python -c "from wef_backend.settings import load_settings; from wef_backend.features.admin.application.ai_review import AiCurationRuntime; s=load_settings(); r=AiCurationRuntime(enabled=s.ai_curation_enabled, zdr_verified=s.groq_zdr_verified, model=s.groq_model, api_key_present=bool(s.groq_api_key)); print('active', r.active)"
```

Geocoding after AI address apply uses **Geoapify** on `telegram-worker` (or add
`WEF_GEOAPIFY_API_KEY` to the shared backend environment if geocoding from `api`).

See also [DEPLOYMENT.md](../operations/DEPLOYMENT.md) (Groq AI curation operations).

## Limits and failure modes

| Limit | Value | Notes |
|-------|-------|-------|
| Owner Groq requests / UTC day | **20** | Counts place-review runs **and** offer-enrichment provider calls |
| Groq free-plan rate | ~30 RPM | Batch scripts need **≥2 s** between generate calls |
| District apply | Canonical only | Non-canonical districts (e.g. `Śródmieście Północne`) reject apply — use **display_address only** or map to a canonical district manually |
| Failed review runs | Count toward daily cap | DNS/network failures before Groq was reachable consumed quota; delete only `failed` + `provider_outcome=network` rows that never reached Groq if retrying same UTC day |

`/api/v1/health/ready` must **not** depend on Groq.

## First production recovery (2026-08-31)

Context: after Geoapify Warsaw rect/bias (#237), **22** locations / **84** visible
offers remained `ungeocoded` (mostly `no_result` or non-address prose).

Shipped infrastructure:

- PR #238 — Groq settings in deploy `production.env`
- PR #240 — Groq env vars passed into API containers
- PR #241 — `api` on `provider-egress` for outbound Groq

Groq enabled with owner ZDR attestation. First automated batch lessons:

1. API without `provider-egress` → 20 failed `network` review runs (quota burn).
2. Groq rate limit when firing requests back-to-back.
3. **Unknown location** (43 offers): AI proposed
   `Śródmieście Północne | ал. Solidarności`; district apply failed (non-canonical);
   **display_address-only apply + worker geocode** → location **accepted**, **43**
   offers gained map pins.

### Metrics

| Metric | Before pass | After pass |
|--------|-------------|------------|
| Accepted locations | 1992 | 1993 |
| Ungeocoded offers (visible) | 84 | 41 |
| Map pins recovered | — | +43 offers |

## Remaining backlog (as of 2026-08-31)

**21** `ungeocoded` locations, **41** visible offers:

| Category | ~Offers | Examples | Recovery |
|----------|---------|----------|----------|
| Real Warsaw streets (Geoapify `no_result`) | ~13 | `ul. Ochocka 1AB`, `ul. Modlińska`, Cyrillic `Варшава, … ul. …` | **Place review** to normalize address → geocode; retry after normalizer bumps |
| Train / distance prose | ~16 | `Warszawa Jeziorki - 2280 м` | Manual map pin (E18) or improved parser pin extraction |
| Marketing prose blocks | ~8 | Long Russian/Ukrainian amenity copy | Not geocodable; manual pin or leave off map |
| Out of Warsaw | ~1 | `Pruszków` | Correctly off map / reject |

Direct Geoapify retry without AI did **not** resolve the street-name bucket after
`forward-geocode-v2`; normalization via place review is the next step.

## Recommended operator workflow

### Per location (UI)

1. Owner → `/admin/places` → filter **ungeocoded**.
2. **Review with AI** → inspect proposed address/district and source coverage.
3. Apply **only** fields with `correct` + medium/high confidence.
   - If district is non-canonical, apply **display_address** only.
4. Verify pin on map (E18) or wait for recurring geocode + accept-pending cycle.
5. Confirm offer stays **visible** and appears on the public map.

### Batch catch-up (after UTC quota reset)

Prioritize by linked offer count. Respect **20/day** and **~2 s** spacing.

1. **Generate** place review (Groq via `api`).
2. **Apply** address (and district only when canonical).
3. **Geocode** via `telegram-worker` (Geoapify) — not from `api` unless
   `WEF_GEOAPIFY_API_KEY` is on the shared backend environment.
4. Run `wef-accept-pending-geocode-pins` from `telegram-worker`, then promote
   **map-ready offers only** (the worker uses `promote_map_ready_offers`; avoid
   bulk `wef-promote-public-catalog` for live recovery — it publishes every
   `needs_review` offer, including listings still without pins).

Do not bulk-generate merely to demo the feature.

### E21 ingestion AI parse recovery (2026-09-01)

Owner **generate/apply** on `/admin/ingestion-issues` creates offers with
`parser_version=ai-parse-v1`. Apply now links `source_message_parse_issues.offer_id`
so recovered rows drop the Review link (PR #267).

Production smoke/recovery on `wef_hist_candidate`:

| Message | Outcome | Map |
|---------|---------|-----|
| 29435 | Warsaw apt — geocoded, **visible** | yes |
| 29425 | Józefosław townhome — geocoded, **visible** | yes |
| 29159 | Warsaw apt (repost) — geocoded, **visible** | yes |
| 29445 | Dosin/Serock house — **ungeocoded** (outside Warsaw Geoapify scope) | no — stays `needs_review` until manual pin (E18) or rejection |

Groq apply hardening shipped in #268–#271 (currency/market aliases, evidence
whitespace/reorder/ambiguity).

Operator geocode catch-up for AI-created locations (Geoapify key is on
**`telegram-worker` only**, not `api` — by design):

```bash
COMPOSE="docker compose --project-name wef-production \
  --env-file /home/nuc/wef/secrets/current/production.env \
  --file /home/nuc/wef/releases/current/compose.production.yaml"
$COMPOSE exec -T telegram-worker wef-accept-pending-geocode-pins
# Worker promotes map-ready offers each recurring_geocode cycle; do not run
# wef-promote-public-catalog unless doing a historical bulk promotion pass.
```

### Offer enrichment (separate)

Use `/admin/offer-enrichment` only for listings missing structured fields (price,
rooms, area). It does not fix `ungeocoded` locations.

## Related PRs and docs

- Geoapify Warsaw bias: #237 (`forward-geocode-v2`)
- Groq deploy wiring: #238, #240
- API provider egress: #241
- [GEOCODING.md](GEOCODING.md) — provider request shape
- E21 parse-issue offer link + AI apply hardening: #267–#271
- [PIPELINE.md](PIPELINE.md) — E21-T2 ingestion AI parse; recurring geocode policy
- [ADR-022](../decisions/adr/ADR-022-use-groq-gpt-oss-for-place-review-and-offer-enrichment.md)

## Security

- Rotate Groq API keys if exposed in chat or logs; update `WEF_GROQ_API_KEY` secret only.
- Never commit keys; never log prompts, source bodies, or provider payloads.
