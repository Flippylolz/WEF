# Measured deployment payloads and truthful HTTPS health

The host inventory collector and seven deployment smoke contracts formerly lived
inside shell heredocs, outside Python measurement. They now live in standalone
`server_inventory.py` and `smoke_contracts.py` helpers called by the same shell
entrypoints. All 150 statements and 36 branch paths in these helpers are covered
at 100%, with independent floors and zero exclusions. Shell command arguments,
`wef-server-inventory@1` fields, JSON formatting, selected-location output and valid
payload behavior retain their existing contracts.

## Conditional health correction

Two synthetic regressions reproduced a false-success condition in
`smoke_public_https_origin`: deployment calls the function inside an `if`/`&&`
condition, where shell `errexit` does not stop its body after the embedded Python
assertion fails. The function then printed success and returned zero despite a
wrong liveness payload or product root.

Both HTTP requests and their semantic validation now form the success condition.
Malformed bodies consume the existing twelve-attempt retry budget, clean up their
temporary files and refuse success; valid bodies still succeed immediately. Tests
use shell functions that write invented responses and skip delays, checking both
exit status and bounded request counts. No real origin or Docker daemon is contacted.
An additional full deployment regression reproduced the exhausted probe calling
`exit` before its caller could restore the previous release. Exhaustion now returns
failure to that caller. The synthetic deployment test verifies previous-release
service restoration, current-state identity and candidate/restored failure evidence.
Its Docker, HTTP, socket and delay tools are temporary fakes.

## Assertions and scope

Thirteen new cases cover the two helpers and conditional shell integration:

- Collector output preserves sorted/redacted projects and containers, exact public
  fields, protocol/address listener identity and duplicate socket counts. Malformed
  short listener rows retain their existing skip behavior.
- HTTP samples read at most one byte with the existing timeout, record HTTP errors
  as status codes and keep unavailable services explicit. Resource and path tests
  use invented memory/disk data and temporary directories/files/dangling symlinks.
- Root release identity, liveness/readiness, ranked map selection, UUIDs, eighteen
  named polygon districts, public offer/facet fields, raw-source refusal and style
  version/source/layer checks retain their existing requirements and failure cases.
- Every helper CLI contract is exercised against temporary files, including paths
  with spaces, exact selected-location output, wrong argument counts and malformed
  JSON. The collector entrypoint uses fake host observers through `runpy`.

The global measured operations inventory expands to 56 executable files, all 4,844
statements and 1,492 branch paths at 100%. All 368 operational tests pass locally.
No runtime source exclusion, coverage pragma or production dependency is added.
The existing release-directory copy includes both helpers in packaged deployments.

This is unplanned maintenance under the owner's coverage request, correcting the
existing [E7-T4 health-gated rollback](../epics/E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md)
and retaining [E7-T2 inventory non-interference](../epics/E7-production-delivery/tasks/E7-T2-provision-and-verify-supplied-server.md).

## Remaining coverage boundary

Runtime shell remains required before completing the repository-wide goal,
including sourced `production-common.sh` and `infra/nginx/deploy-hook.sh`.
Documentation, declarative configuration, generated assets and test/proof drivers
remain excluded. The source/exclusion allowlists are unchanged.

Workflow wiring and primitive output formatting are build/orchestration glue:
selecting a digest from already inspected output, formatting a validated snapshot
SHA and removing bytecode caches from a CI build artifact. Their actual deployment
identity/order rules remain in measured Python helpers. The badge SVG keyword check
and deliberate OpenAPI-breaking fixture are verification drivers. They remain
subject to workflow/contract proofs, without inventing runtime coverage for test
infrastructure or changing historical workflow CLI compatibility.
