# Complete runtime shell coverage

The owner's repository-wide goal requires 100% of included code, with documentation
and non-runtime test/build infrastructure excluded. `make quality-gates` now runs
`make coverage-shell` alongside operational Python measurement. Every runtime shell
file independently requires 100% line coverage in Repository safety CI.

## Measured inventory

The pinned Kcov collector measures 390 executable lines across all eleven runtime
shell files. It reports line coverage; no shell branch metric is claimed.

| Source | Covered / executable lines |
| --- | --- |
| `scripts/deploy/deploy.sh` | 77 / 77 |
| `scripts/deploy/preflight.sh` | 27 / 27 |
| `scripts/deploy/production-common.sh` | 97 / 97 |
| `scripts/deploy/provision_server.sh` | 25 / 25 |
| `scripts/deploy/reconnect-wef-upstreams.sh` | 24 / 24 |
| `scripts/deploy/rollback.sh` | 24 / 24 |
| `scripts/deploy/server_inventory.sh` | 3 / 3 |
| `scripts/deploy/shared_edge_renew.sh` | 37 / 37 |
| `scripts/deploy/smoke.sh` | 40 / 40 |
| `scripts/deploy/verify_current.sh` | 10 / 10 |
| `infra/nginx/deploy-hook.sh` | 26 / 26 |

The proof checks Git's tracked and non-ignored new shell inventory against the
reviewed policy. Its only shell-driver exclusion is
`scripts/check_openapi_compatibility.sh`, which generates and tests deliberate
contract failures. Each runtime entrypoint is collected directly; sourced common
functions use temporary callers. Nested `sh` execution alone is not treated as
measurement of child scripts. Parsing every source directory retains unexecuted
scripts at zero, and the gate rejects missing, duplicate, ambiguous or unexpected
files, invalid/zero counters, inconsistent totals and weakened floors. Rounded
percentage labels cannot authorize success.

No shell coverage line or region exclusions are used. Four empty `case`
alternatives place their terminators on separate lines so non-executable syntax
is not counted as behavior. Six quoted script invocations and one command
substitution use single logical lines to align the collector's parser and Bash
trace locations. Their arguments and behavior are unchanged; the existing native
POSIX deployment/rollback proof still passes.

## Behavioral evidence

Seventeen synthetic cases assert:

- Healthy activation and current-release verification, exact release pointers,
  forward-migration refusal, reviewed rollback rehearsal and previous-release
  restoration/failure records.
- Host lock, identity, path/symlink, disk, memory, occupied port, production pull
  and provider-readiness refusals before unsafe activation.
- Application and worker startup failures, with and without the shared-edge
  overlay, returning failure to the caller instead of activating a candidate.
- Optional observation failure remaining non-fatal, rollback failure remaining
  explicit and first-release failure stopping only the WEF application services.
- Public HTTPS retries, transport refusal and temporary cleanup; the
  [measured Python payload helpers](EMBEDDED_DEPLOYMENT_COVERAGE.md) independently
  enforce response semantics and exact release/public-data contracts.
- Exact upstream container/network aliases, missing-network/container skips,
  idempotent attachment and scoped HUP reloads.
- Renewal exit propagation, stale-marker removal, no-marker skip, configuration
  validation before reload and failed-validation/reload refusal.
- Provisioned directory modes, certificate traversal/public/private-key modes,
  private-key group ownership, preserved account permissions, live-symlink refusal,
  temporary dry-run lineages and atomic mode-0600 reload markers. Traversal failure
  preserves an existing marker.

Two new regression assertions first reproduced candidate activation after failed
application or worker startup: deployment invokes the startup function inside an
`if`/`&&` condition, disabling implicit shell `errexit` within that function. Its
application and worker commands now explicitly return their failing status.
The regressions verify that the caller restores the previous healthy SHA and
records both the failed and restored identities. This corrects existing E7-T4
health-gated delivery behavior, without changing service topology or configuration.

## Reproducible isolation and reports

Run `make coverage-shell`, or the complete `make quality-gates` mapping. The proof
builds the test-only `infra/shell-coverage/Dockerfile` from its small context, using
immutable Python 3.13.16 and Kcov image digests. The Kcov digest reports
`v44-pre-test3-2-gf65e`; it is pinned explicitly. Dependabot covers this tooling
directory. No production dependency is added.

The container runs as the host's unprivileged UID/GID with all capabilities dropped,
no network, no Docker socket and a read-only root filesystem. It receives only an
explicit source allowlist and dedicated report output. Docker/HTTP/socket/account
observers are temporary fakes. `/home/nuc` and `/etc/letsencrypt` are disposable
container memory filesystems containing invented text, never real services,
certificates, keys, credentials or repository environment files.

`tmp/coverage/shell/coverage.json` is the stable report; raw collector and merged
reports remain under the same ignored directory for diagnosis. CI publishes the
JSON as `shell-coverage-<source-sha>`. The badge downloads its two application
reports by exact artifact names so operational reports cannot overwrite each other
in its download directory. Its display remains the combined application result;
all four inventories independently gate the repository.

The complete operational Python suite also passes all 376 tests at 100% across
4,901 statements and 1,520 branch paths in 56 executable files. Eight new gate tests
exercise malformed evidence and the real CLI; deliberate policy faults cover
source/floor removal, added exclusions, missing reports and disabled/commented-out
local gates. Existing Python/frontend exclusions are unchanged.

This is unplanned maintenance under the owner's coverage instruction. The
[canonical scope](COVERAGE.md), [E14 verification mapping](../epics/E14-production-hardening-and-scalability/T1_VERIFICATION.md)
and [deployment operations](../operations/DEPLOYMENT.md) describe the enforced goal.
