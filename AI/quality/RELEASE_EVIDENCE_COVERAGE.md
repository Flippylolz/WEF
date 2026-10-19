# Release state and evidence coverage

This unplanned maintenance continues the owner's repository-wide 100% coverage
request. Twenty new cases complete execution and refusal coverage for the six
release cache, cohort, observation, ordering, report and state implementations.
All 622 statements and 218 branch paths measure 100%, with independent file floors.

## Assertions and safety boundaries

The tests use invented metadata and temporary files. API, ancestry and artifact
process boundaries are controlled doubles; they never access GitHub or a production
host. Actual Python subprocess entrypoints exercise only synthetic local state or
explicitly unavailable metadata.

- State reads reject invalid primitive shapes; writes and release/secret links
  preserve ownership boundaries, atomic replacement and mode-0600 state. Every
  CLI field round-trips, including optional restored-source evidence.
- Ordering rejects orphaned links, bad source identities, inconsistent config or
  manifests, missing source history and ancestry-command failures. Snapshot,
  guarded activation, pending mutation and no-op observation CLIs are exercised.
- Observations reject bad identities/timestamps and export only their allowlisted
  fields. Cache capture preserves unknown state after unavailable or invalid build
  metadata and never exports the synthetic private input.
- Reporting distinguishes already-current health from fresh deployment, escapes
  stage text, excludes skipped intervals and retries metadata reads within the
  existing bound. Missing Actions metadata remains explicit rather than becoming
  a successful deployment.
- Cohort artifact downloads reject missing/expired runs, process failure, foreign
  attempts, symlinks to otherwise-valid evidence and oversized valid JSON. Evidence
  exactly at the byte limit remains accepted. Source ancestry, timestamp ordering,
  saved schema/cutoff and same-run health must match before latency is attributed.
  Failed runs stay visible, and insufficient independent health observations do
  not meet the budget. Saved evidence can be summarized without API access.

The focused suite passes 51 tests, including existing release cases. Two equivalent
simplifications remove unreachable checks: argparse's final ordering command is
exhaustive, and a valid duration already proves its deterministic normalized
timestamps exist. No runtime exclusion, coverage pragma or dependency is added.

## Gates and remaining scope

The six files join `make coverage-operations`' independent 100% floors, invoked by
required Repository safety CI through `make quality-gates`. Deliberate policy faults
reject dropping any completed file. The source inventory still includes untested
operational helpers; test/proof/browser-runner drivers alone remain omitted.
Application coverage and badge thresholds stay at 100%.

Other operational helpers, shell behavior and substantive Python embedded in
shell/workflow entrypoints remain within the active owner request. The goal for the
repository cannot be declared complete while they remain unaccounted for. The final
global operational threshold must require 100% once the remaining behavior is covered.

## Validation

The locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes: 2,266 backend tests and 355 frontend tests retain 100%, and
all 278 operational tests pass with 33 independent 100% file floors. The 51 focused
cases, strict Ruff/mypy, Markdown links and Git whitespace checks also pass.

The comparable native diagnostic with the same release/topology/rollback proof
drivers rises from 77.84% to 81.89%. It measures all 4,668 statements and 1,444
branch paths after the two equivalent simplifications; 793 lines and 314 branch
paths remain uncovered. Reports stay ignored under `tmp/coverage/`; remaining
Python, shell and substantive embedded-runtime scope still prevent declaring the
overall goal complete.
