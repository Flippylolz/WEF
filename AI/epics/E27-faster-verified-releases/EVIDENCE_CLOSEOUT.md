# E27 evidence closeout — 5 September 2026

Disposition: **closed for now at the owner's request; final performance acceptance deferred**.
T1/T2 and the T3 instrumentation are merged and deployed. E27 and T3 use the
workflow's `deferred` state, not `done`. The 20-release minimum and operational
acceptance criteria are unchanged.

## Delivered and verified

- [#324](https://github.com/Flippylolz/WEF/pull/324): approved design and task promotion.
- [#326](https://github.com/Flippylolz/WEF/pull/326): exact-SHA release outcomes, gate reasons and stage timing.
- [#329](https://github.com/Flippylolz/WEF/pull/329): shared verification, concurrent image preparation, complete deployment-job serialization and guarded reuse/ordering.
- [#332](https://github.com/Flippylolz/WEF/pull/332): cohort collector and cache measurement.
- [#336](https://github.com/Flippylolz/WEF/pull/336): corrected Buildx builder/reference lookup, verified against a real local record and production counters.

Required CI passed on the merged heads. Local release reporting/order/cohort
tests, production/rollback proofs, exact-digest runtime tests, and shared-edge
non-interference checks passed; [check parity](CHECK_PARITY.md) and the
[implementation evidence](ACCEPTANCE.md) retain the details. No production
failure was deliberately injected.

## Frozen ordinary-release cohort

Cutoff: `8e3548ea0533d9d3f762ca760f74c90d70b78dde` (T2 merge).
The six observations below were collected on 2026-09-05 and each has an exact
source/run/attempt outcome artifact confirming verified, eligible deployment and
observed health. All are ordinary main pushes associated with merged PRs;
all six deployment jobs succeeded. The cohort excludes the closeout PR itself
and is not silently updated by later releases.

| Run (attempt 1) | Source | Merge to observed health (s) | Initial queue (s) | Cache evidence |
| --- | --- | ---: | ---: | --- |
| [33964655697](https://github.com/Flippylolz/WEF/actions/runs/33964655697) | `8e3548ea0533d9d3f762ca760f74c90d70b78dde` | 348.379957 | 3 | unknown |
| [33965647303](https://github.com/Flippylolz/WEF/actions/runs/33965647303) | `ed10ca7befdbaef370eaf603793dbb8ca7f4d916` | 277.722518 | 4 | unknown |
| [33966608546](https://github.com/Flippylolz/WEF/actions/runs/33966608546) | `fd8090a871b3164acba5c3c9114846276589be48` | 277.468304 | 3 | warm |
| [33966923140](https://github.com/Flippylolz/WEF/actions/runs/33966923140) | `5d0afd8396b98f95c5d003c6392b057d7faa5003` | 287.501855 | 3 | warm |
| [33967260852](https://github.com/Flippylolz/WEF/actions/runs/33967260852) | `64da1bd9dd00e64be4e5ddbfce32e53f19c8f2af` | 284.282866 | 3 | warm |
| [33968987579](https://github.com/Flippylolz/WEF/actions/runs/33968987579) | `5fd175f95893155260c9da2ab92d334c1b7e9554` | 284.209944 | 3 | warm |

Provisional nearest-rank **p50 284.209944 seconds (4m44s)** and
**p95 348.379957 seconds (5m48s)** include queue time. The collector reports
`insufficient_observations`: **6 of at least 20** required distinct healthy
sources. These values are not an accepted production percentile or a population
speedup claim. The [T1 historical baseline](BASELINE.md) uses deploy-job end
where first-health evidence is absent and must not be substituted for health.

The five adjacent merge-to-health windows did not overlap. The next merge
occurred 953.620, 938.277, 124.532, 133.498 and 1888.717 seconds after the previous
observed health. This cohort therefore supplies no production contention proof;
a small runner delay alone does not establish deployment-lock contention.

## Production cache evidence and operational checks

Run 33966608546 reported healthy source
`fd8090a871b3164acba5c3c9114846276589be48`, a warm backend dependency cache,
**13/25 backend image steps cached**, and **7/20 web image steps cached**.
`warm` means at least one observed cached step, not a fully cached build.
Earlier missing counters remain unknown. Public HTTPS version and readiness
were independently checked after the instrumentation and corrective releases.
The sanitized release reports retain image digests, healthy/previous SHA and
activation times; raw logs and configuration are not part of this evidence file.

The E27 rollout needed no operator SSH, manual dispatch, configuration editing
or extra per-release approval. This direct observation of our rollout does not
establish zero interventions across every later release. Provider/runner incident
attribution and broader operator evidence remain incomplete. Local failure
proofs cover rollback reporting and restored SHA; no production rollback event
is fabricated from successful deployments.

## Isolated local cold/warm proof

Source: `5fd175f95893155260c9da2ab92d334c1b7e9554`.
Each component used its own fresh disposable `docker-container` builder, then
repeated the identical runtime Dockerfile build with the same source SHA and
warmed cache. The build supplied `--target runtime`, `--build-arg WEF_RELEASE_SHA`,
`--metadata-file`, and dedicated local `--load` tags; the production collector
read the exact Buildx record. No images were pushed or shared caches cleared.

| Component | Case | Cached / total steps | Local elapsed (s) |
| --- | --- | ---: | ---: |
| Backend | Cold | 0 / 23 | 22.74 |
| Backend | Warm | 14 / 23 | 1.53 |
| Web | Cold | 0 / 18 | 36.94 |
| Web | Warm | 12 / 18 | 1.50 |

These are local functional observations, **not production latency samples**.
A preliminary web build shared the backend proof builder and reused one step;
it was excluded from the cold table and repeated in its own empty builder.

Locked backend third-party dependencies were installed with
`uv sync --project apps/backend --frozen --no-install-project`, using an initially
empty temporary `UV_CACHE_DIR` and new `UV_PROJECT_ENVIRONMENT` (2.36 local
seconds). A second new environment succeeded with `--offline` against the warmed
cache (0.37 seconds). This proves dependency reuse without network access; it
does not claim an application installation or a production cache restore.

Temporary dependency environments, dedicated builders, image tags and the clean
detached proof worktree were removed. No production releases were created to
fill the sample.

## Deferred acceptance and resumption

The owner asked: "merge evidence and we can close this for now".
The [decision transcript](OWNER_DECISIONS.md) records that disposition.
Resume only when the owner reopens E27, on a fresh branch from current main.
Then revalidate the original gates and gather:

1. At least 20 distinct ordinary post-change releases with exact observed health;
   report any p50 > 300s or p95 > 420s transparently, without dropping slow runs.
2. Production cache diversity and queued consecutive-merge/ordering evidence.
3. Provider/runner incident attribution and operator intervention evidence, with
   explicit unknowns rather than assumed zeros.
4. Final current rollback/shared-host/check-parity evidence and acceptance review.

Use `python3 -m scripts.deploy.release_cohort --optimized-from
8e3548ea0533d9d3f762ca760f74c90d70b78dde --limit 100 --output /private/tmp/e27-cohort.json
--require-budget` as one command. Existing per-release reporting continues as
part of the deployed workflow. No recurring agent follow-up is scheduled by this
closeout. Do not manufacture deployments, weaken gates, or declare `done` from
this six-run snapshot.
