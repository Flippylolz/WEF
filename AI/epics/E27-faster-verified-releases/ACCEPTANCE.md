# E27-T3 release acceptance evidence

Status: local implementation checks passed; operational acceptance pending.
This record does not claim a measured speedup or completed epic.

## Observed baseline and current availability

On 2026-09-05 the read-only collector inspected the latest 50 main release runs:
8 manual dispatches, 12 unmatched pushes and 30 exact merged-PR source SHAs.
Among the 30 ordinary runs, 24 succeeded and six were cancelled. Successful
deploy-job completion was p50 580 seconds (9m40s), p95 831 seconds (13m51s).
Initial event-to-first-job delay for those 24 was p50 10 seconds, p95 316 seconds.
These reproduce the [T1 baseline](BASELINE.md).

None had the new run-specific outcome artifact, first-health timestamps or cache
counters. All 30 therefore have unknown deployment observations/cache state;
workflow success is retained separately. At that baseline collection no optimization merge SHA existed,
so the collector labeled the cohort unclassified and the target `awaiting_cutoff`.
Replaying that sanitized evidence with `--require-budget` correctly returned 1.
No raw API responses, logs or configuration are committed here.

## Measurement contract

The collector `scripts/deploy/release_cohort.py` reads at most 100 recent main
runs, verifies exact source/run/attempt identities for outcome artifacts, and
classifies ancestry against a full merged optimization SHA. It never writes to
GitHub or deploys. `--input` replays a sanitized snapshot; it cannot reclassify
ancestry by changing the cutoff. Offline data is supplied evidence, not a new
verification of the remote run.

The latency gate requires 20 distinct healthy ordinary source SHAs, p50 <= 300
seconds and p95 <= 420 seconds including queues. Retries do not inflate the
sample. Health, deploy-job completion, missing observations, cancellations,
failures, manual dispatches and unmatched pushes are reported separately.
Nearest-rank percentiles and sample counts are explicit. Provider incidents
remain included; attribution and human intervention counts need separate evidence.

Cache telemetry selects only completed/cached step counts from the exact Buildx
record and the backend dependency restore hit. `warm` means some measured reuse;
it does not claim a fully cached build. Missing data remains unknown. See the
[Buildx history inspection reference](https://docs.docker.com/reference/cli/docker/buildx/history/inspect/)
for the counter contract and the
[pinned setup-uv action](https://github.com/astral-sh/setup-uv/blob/20cfd1bf945f4377ade1205e4dbc17946fc9a30d/action.yml)
for `cache-hit`. The local frontend install has no independent restore cache.

## Acceptance still required after merge

- Collect at least 20 eligible ordinary observed releases against the merged
  optimization cutoff and publish the measured budget result, including misses.
- Represent observed cold/warm cases and queued consecutive merges; correlate
  candidate/healthy SHA, immutable digests, ordering and cancellations.
- Retain health-failure/automatic-rollback evidence and shared-host
  non-interference results. Local synthetic proofs are identified as local.
- Record actual operator interventions and provider/runner incidents; do not
  infer zero from a successful workflow.
- Finish dependency completion and review gates before task completion/merge.

Use the documented collector command in [deployment operations](../../operations/DEPLOYMENT.md#release-budget-and-cache-evidence-e27-t3).
No production fault injection, artificial release cohort, repeated manual
activation, or unattended scheduling has been authorized by this implementation.

## Local validation on 2026-09-05

- `UV_PYTHON=3.13.2 make lint`: passed.
- `COMPOSE_PROJECT_NAME=wef-e27-proof UV_PYTHON=3.13.2 make test`: passed,
  803 backend and 169 frontend tests; isolated local test database.
- `UV_PYTHON=3.13.2 make format-check typecheck contract-check`: passed.
- `apps/backend/.venv/bin/python -m unittest discover -s scripts -p 'test_*.py'`:
  175 tests passed, including 29 release report/order/cohort cases.
- From `apps/backend`, `.venv/bin/ruff format --check ../../scripts`,
  `.venv/bin/ruff check ../../scripts`, and `.venv/bin/mypy --strict ../../scripts`:
  passed across the repository scripts.
- `actionlint .github/workflows/*.yml`: passed.
- `UV_PYTHON=3.13.2 make production-proof`: passed, including local workflow,
  rollback, shared-edge runtime/non-interference and configuration proofs.
- Read-only local `docker buildx history inspect --format json` produced a
  completed record with 8 cached steps of 14. Only those selected counters were
  printed. This validates the CLI counter format, not production cache coverage.

The first sandboxed make attempts could not access the installed uv cache or
Docker socket; reruns with local tool access passed. No source fix or skipped
check was used to hide those environment restrictions.

## Ordered rollout on 2026-09-05

The owner authorized PRs #324/#326/#329 in dependency order. All merged after
required checks passed. A concurrent documentation change (#333) required one
additional clean T2 rebase and new local/CI validation under strict main checks.
No required check or dependency gate was bypassed.

T1 production run [33963661845](https://github.com/Flippylolz/WEF/actions/runs/33963661845)
completed automatically with verified/eligible `deployed` outcome and healthy SHA
`1700f0491ad8d40c0c2fd8e822b7341f472dba91`. Observed health was
2026-09-05T11:45:06.115256Z and activation 11:45:06.216708Z. Both immutable image
digests and previous SHA were present in the sanitized report. No operator SSH,
manual dispatch, configuration edit, or extra per-release approval was needed.

The merged optimization cutoff is
`8e3548ea0533d9d3f762ca760f74c90d70b78dde` (PR #329).
Its first release is [33964655697](https://github.com/Flippylolz/WEF/actions/runs/33964655697).
The backend/web image builds and all three verification jobs started between
11:56:34Z and 11:56:36Z, proving the intended concurrent job graph in Actions.
The T3 cache-counter changes remain draft code and are not deployed by T2;
production cache-state coverage remains outstanding.

The first optimized release completed successfully. Its exact healthy SHA matches
the optimization cutoff. Merge-to-observed-health was **348.379957 seconds
(5m48s)**, with health at 2026-09-05T12:02:09.379957Z and activation at
12:02:09.477130Z. Both image digests were present:

- Backend: `sha256:a497294bf646c0ddc79e2e738bd649cf26d25a2c724d7b88fd02b73203de4eec`.
- Web: `sha256:d8a87311cbb42bfa0b83f6655bf4f39cb01db7c8d8d7a543ec9f3438c5905c8c`.

The public HTTPS page independently showed version `8e3548e` and API readiness
`ready`. An initial independent check assumed the internal release header was
also exposed at the public edge; that header was absent, so the documented HTML
version marker and readiness endpoint were used instead. No deployment failed.
The automatic deployment's local/public health and shared-host checks passed.
No operator dispatch, SSH, configuration edit or extra approval was needed for
this release. No provider incident was diagnosed during this rollout; that is
not a claim that the longer cohort has zero incidents.

A read-only four-run snapshot collected against the merged cutoff contains one
optimized healthy source and reports `insufficient_observations`. The observed
5m48s is above the proposed five-minute median budget and below seven minutes;
one sample cannot establish either accepted percentile. T1/T2 are complete,
while T3 remains draft/in progress. Cache counters are still not deployed, and
cold/warm/consecutive-merge coverage remains outstanding.

After the final rebase, local lint, 803 backend tests, 169 frontend tests, all
175 script tests and actionlint passed again. The earlier production/rollback
proofs remain applicable; no executable changes were introduced during rollout
bookkeeping. Required draft-PR CI reruns on its rebased head.

## Measurement rollout decision

PR #332 is ready to deliver measurement code after green CI under the existing
approved implementation scope and current standing merge authorization. Keeping
its code in draft until the cohort is complete would prevent production cache
counters from being collected. The plan requires performance acceptance to stay
open with insufficient data, not instrumentation to remain undeployed. Earlier
draft statements above describe the rollout history and are superseded by this
sequencing decision. T3 remains `in_progress`, with all unproven acceptance
criteria and completion fields unchanged. No latency target or sample threshold
is waived. A future scoped evidence follow-up records acceptance once actual
ordinary releases provide it; this instrumentation PR does not close the epic.
