# Historical import command coverage

The owner's repository-wide coverage request includes operator composition.
This pass adds 19 cases for `wef_backend/import_command.py` and enforces a 100%
combined line/branch floor for all 223 statements and 50 branch paths in the
[critical policy](../../.github/critical-coverage.json). It closes the previous
101 missing lines and 26 missing branch paths without changing runtime behavior
or adding coverage exceptions.

## Behavior evidence

| Boundary | Assertions |
| --- | --- |
| Source preparation | The configured source is inspected, scanned under its expected identity and counted completely; progress does not expose its path |
| Dry-run planning | Anchored media with completed replay keys is excluded from new work without claiming or mutating a run |
| Persistence | A fresh lease claims the immutable source/pipeline; an existing lease is reused; each acknowledged batch is checkpointed; entirely unchanged input launches no persistence batch |
| Empty geocoding | An empty stage checkpoints zero remaining work without requiring an API key or constructing a resolver |
| Geocoding prerequisites | Pending work refuses both absent and blank credentials before constructing a resolver or checkpointing progress |
| Geocode batches | Every pending location retains its address/district/identity; checkpoints occur at the batch boundary and final count; durable budgets use the configured local/daily/rate bounds |
| Provider pauses | Local cap, daily quota and transient errors preserve exactly the completed progress and produce distinct reasons/eligibility times; a pause cannot become successful completion |
| Media ownership | Bounded batches retain source/revision/ordinal provenance; listing association is optional; missing anchors and terminal replay keys launch no work |
| Final verification | Unpersisted source messages refuse terminal success; verified counts and the success checkpoint agree |
| Python module entry | `--help` exits successfully with the documented operator options before any database/provider work |

The new [stage command tests](../../apps/backend/tests/test_import_stage_commands.py)
use the existing sanitized fixture, real extraction/preparation and persistence
interactor, in-memory ports, temporary storage paths and a fixed UTC clock.
Provider/storage adapters are replaced at their outer composition boundaries;
existing real PostGIS and media tests continue to own their persistence and byte
behavior. The command's original argument, stage-sequence, pause and redaction
tests remain active. No provider account, production source or secret is used.

Run `make coverage-backend` for the complete locked Python/PostGIS result and
independent floors. The combined run passes 1,665 backend tests at 93.14% coverage,
with all 50 completed implementation floors passing. Another 1,014 lines and 507
branch paths remain uncovered. Remaining backend and operational gaps stay in
scope. All applicable global, per-file and badge thresholds must require 100% before the
repository-wide goal is complete.
