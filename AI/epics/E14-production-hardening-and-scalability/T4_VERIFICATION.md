# E14-T4 backend seam verification

## Preserved behavior and owners

The baseline is main `7367402ff76abe78c414c023d2f0c66254cedc2f` (E14-T2), whose
canonical gate and production release passed. All 1,218 existing backend tests
passed after extraction at 90.67% global branch-aware coverage, without warnings.

| Responsibility | Owner after extraction | Preserved contract |
| --- | --- | --- |
| Numeric/currency/room parsing | `application/extraction_numbers.py` | Same regexes, ranges, alternative quotes and refusal rules; `extraction.py` still assembles spans, warnings and candidates |
| Contact-free persisted fields | `application/persistence_projection.py` | Same minor-unit rounding, masking, fingerprint, location key and provenance JSON; compatibility exports remain in `persistence.py` |
| Provider daily ledger | `infrastructure/provider_budget.py` | Same reserve and completion transactions; complete-import repository explicitly delegates its unchanged inward port |
| Terminal progress | `import_progress.py` | Same bounded updates, noninteractive cadence, carriage returns and completion behavior |
| Import stage resources | `ImportStageContext` at outer CLI composition root | Same prepared input, repository, persistence, database and settings; no new application dependency on frameworks |
| Release configuration proof | `scripts/prove_release_configuration.py` | Same environment restoration, defaults, validation and private-file round trip; workflow/gate/manifest assertions remain in workflow proof |

An AST comparison against the exact baseline verified unchanged implementations for
nine numeric functions, ten projection functions, both ledger methods and three
progress methods. It ignores source positions and substitutes the newly named
constant `2` only for the existing two-quote limit. This supports, but does not
replace, the behavioral tests. Parser and pipeline versions are unchanged.

## Transaction, retry and cancellation ownership

- Historical persistence retains the complete-run lock and bounded `persist_batch`
  port calls. The SQL adapter still atomically commits messages, revisions, offers,
  provenance, run counts and checkpoint. It was not moved or rewritten.
- The complete-import repository retains exact-source claim/pause/release/fencing
  and checkpoint transactions. Five-minute lease timing and stale-owner behavior
  are unchanged. The CLI still disposes its engine in `finally`.
- Each budget reservation opens exactly one session and transaction, inserts the
  daily row if absent, locks it, checks quota, increments it and writes the attempt.
  The delegate introduces no outer transaction or commit. Completion still updates
  only a reserved attempt. Failed insertions roll back the quota increment.
- The geocode stage still pauses at operator/daily/transient limits with the same
  eligibility times. A paused full run stops before media/verification. No retry,
  checkpoint, exception handling or cancellation boundary moved.
- Error summaries remain category-only. New CLI boundary tests assert exact exits
  2 and 130 and exact redacted stderr, plus sorted JSON and unchanged batch defaults.

New tests cover all explicit stage sequences, paused short-circuit, context identity
and disposal. A real PostGIS test adds three concurrent reservation attempts against
a two-request cap, one-second spacing, rollback after a failed attempt FK and
idempotent completion. Existing golden extraction, revision/replay, live new/edit/
delete, cancellation and architecture tests remain authoritative.

## Confidence and complexity

The 97% independent persistence floor now applies separately to the orchestration
module and the extracted projection module, so moving code does not evade the gate.
Measured after extraction: orchestration 98.61%, projection 98.06%. Numeric parsing
and the ledger remain under global coverage plus explicit behavior assertions.

Selected hotspot line counts: extraction 1298→1145, persistence 556→435,
complete-import repository 604→552, import command 685→636, release workflow proof
333→212. Four argument/magic-value suppression sites disappear from extraction and
CLI. The unchanged inward provider port still justifies its argument-count
suppression in adapter and delegate. The workflow proof no longer globally
suppresses magic values or wildcard bind addresses; the inert configuration fixture
has one exact bind-literal suppression and a named private-file mode. Executable
proof assertions and one bounded output line remain intentional suppressions.
These are maintainability signals; line counts are not acceptance by themselves.

Final `make verify`, required CI and release evidence are recorded in the PR/task.
No migrations, parser semantics, public/persisted contracts, runtime dependencies,
production data changes or transaction movement. Rollback uses the prior image.
