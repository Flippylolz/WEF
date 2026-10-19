# Transfer operations coverage

The owner requested repository-wide 100% coverage, excluding documentation and
other nonbehavioral files. This unplanned maintenance extends measurement to
handwritten operational Python without changing the application coverage gates.

## Measured behavior

Thirty-one new transfer cases supplement the existing 38 transfer tests. Every
executable transfer implementation and all four CLI entrypoints measure exactly
100%: 1,231 statements and 328 branch paths across 23 files. Assertions cover:

- Missing metadata, unsupported/excluded tables, unsafe media paths, symlinks,
  manifest identifiers and forbidden sensitive manifest fields.
- Missing, resized and tampered bundle components, including a component changed
  after initial verification; SSH host verification, identity paths and ports.
- Independent capacity, path, database-name and incoming-directory collision
  refusals; candidate table/media/pipeline/migration drift.
- SQL scalar/composite keys, escaped literals, invalid schemas and table names;
  exported snapshots, psql failure diagnostics and restrictive checkpoint modes.
- Dry-run without writes, interruption without advancing the failed batch,
  checkpoint resume and actual subprocess module entrypoints.

Fixtures contain only invented rows and bytes in temporary directories. Process
and live export boundaries use controlled doubles; these tests never contact a
server or restore a database. Existing PostGIS and deployment runtime proofs
remain independently required.

Four equivalent control-flow cleanups remove branches with no valid input:
`PurePosixPath` normalizes dot segments, JSON object keys are strings, a valid JSON
value beginning with `[` is an array, and argparse admits only the declared
subcommands. Traversal checks, invalid JSON, unknown commands and runtime failures
still fail through their existing boundaries. No runtime coverage pragma or
production dependency is added.

## Measurement and enforcement

`coverage.operations.toml` measures branches across all of `scripts`, including
files not imported by tests. Its only omitted Python files are `test_*.py`,
`prove_*.py` and `run_full_stack_e2e.py`: test cases, deliberate-fault/runtime proof
drivers and the browser test runner. Their operational helper imports remain
measured. Documentation, generated data, configuration and shell files do not
match this Python inventory; shell behavior remains required in the overall goal.

`make coverage-operations` runs the operational unittest suite under the locked
coverage tool, instruments subprocess entrypoints, combines the data and writes
`tmp/coverage/operations/coverage.json`. `make quality-gates` invokes this target,
so required Repository safety CI enforces the completed transfer floors. CI also
uploads the operational report. Independent 100% floors cover all 23 transfer files
and both coverage/quality policy checkers; missing files and invalid counters fail
closed. Additional CLI tests verify report selection and refusal diagnostics.
Deliberate policy faults reject a narrowed inventory, expanded omissions,
subprocess instrumentation removal, dropped floors and weakened thresholds.

The operational report also exposes remaining deployment Python. Its aggregate
is diagnostic until every operational implementation reaches 100%; the existing
backend/frontend badge gates still each require 100%. Neither untested deployment
helpers nor shell scripts are excluded to declare completion. Their remaining
cases and a final global operational gate stay within the active owner request.

## Validation

The full locked `make format-check lint typecheck test contract-check quality-gates
compose-config` passes: 2,266 backend tests and 355 frontend tests retain 100%, and
all 233 operational tests pass with every completed floor at 100%. The locked
release-workflow proof also passes. Scoped strict Ruff/mypy, Markdown links and
Git whitespace checks pass.

A comparable native diagnostic measuring the unittest suite plus the existing
release, production-topology, deploy-rollback and shared-edge-topology proofs
improves the operational aggregate from 65.10% to 72.54%. All 4,671 operational
statements and 1,448 branch paths remain in that inventory; 1,198 lines and 482
branch paths still need cases. The shared-edge runtime TLS proof is not part of
this diagnostic; Linux required CI retains that independent runtime proof.
