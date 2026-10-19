# Activation and cutover preflight coverage

This unplanned maintenance continues the owner's repository-wide 100% coverage
goal. It adds 25 regression cases for host activation and shared-edge admission,
using only invented temporary files and controlled process results. Only tests,
coverage-policy enforcement and evidence change.

## Behavior and assertions

`activate_historical_candidate.py` covers all 308 statements and 90 branch paths.
The tests verify:

- Unsupported database URLs, unsafe names, optional credential redaction, missing
  or empty media trees, occupied backup paths and symlink verification failures.
- Atomic environment replacement, mode 0600 and temporary-file cleanup on failure;
  absent current media roots and restoration from both retained backups.
- psql command diagnostics, bounded identity/session fingerprints, failed identity
  import, mismatched fingerprints and migration/Compose fallback selection.
- Application/media-edge recreation, shared-edge reconnect selection, unhealthy
  health/map/media bodies, derivative extension fallback and bounded smoke retries.
- Dry-run without writes, lock refusal, already-active database refusal, successful
  pointer/state updates and environment/media restoration after recreation fails.
  Saved evidence must redact the synthetic database password.
- CLI mode exclusivity, refusal diagnostics and the real subprocess entrypoint.

`shared_edge_preflight.py` covers all 120 statements and 42 branch paths. Assertions
require the dedicated root and subdirectories, mode-0700 certificate directory,
free planned listeners, retained Forecast listener when required, rollback
material, external network and safe command fragments. They also verify missing
Docker/ss tools, process diagnostics, IPv4/IPv6 listener parsing, upstream validation
and wrapped release errors before mutation. Its CLI tests exercise the explicit
fixture listener option, refusal diagnostics and a real subprocess entrypoint.

The focused suite passes 40 tests, including the 15 existing cases for these two
modules. The new tests never execute Docker, contact an HTTPS endpoint, write a
host deployment path or restore a live database. Real deployment/runtime proofs
remain independently required; their source helpers remain measured.

## Enforcement and remaining scope

Both implementations join the independent 100% operational file floors enforced
by `make quality-gates` through `make coverage-operations`. Missing floors,
weakened counters and omitted source fail the policy checks. The denominator still
includes all other operational Python, and no coverage pragma or runtime omission
is added. Documentation, test/proof drivers and other nonbehavioral files retain
the documented exclusions in [coverage scope](COVERAGE.md).

Remaining deployment helpers, shell scripts and substantive Python embedded in
shell/workflow entrypoints must be accounted for before the repository-wide goal
is complete. The final operational global threshold must require 100% when that
remaining behavior is covered.

## Validation

The full locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes. All 2,266 backend and 355 frontend tests retain their 100%
coverage, and all 258 operational tests pass with 27 independent 100% file floors.
The 40 focused cases, strict Ruff/mypy, Markdown links and Git whitespace checks
also pass.

The comparable native operational diagnostic, measuring the unittest suite plus
existing release/topology/rollback proof drivers, rises from 72.54% to 77.84%.
It retains all 4,671 statements and 1,448 branch paths; 961 lines and 395 branch
paths remain uncovered. Its report stays ignored under `tmp/coverage/`, and shell
and embedded-Python scope remain required separately.
