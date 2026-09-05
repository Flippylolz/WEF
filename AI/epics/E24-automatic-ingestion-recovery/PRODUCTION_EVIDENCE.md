# E24 production recovery evidence

## Authorization and release

The owner approved the named E24 merge and rollout sequence under
[AD-050](../../workflow/AUTONOMOUS_DECISIONS.md#ad-050-approve-the-e24-merge-and-recovery-rollout-sequence).
Planning PR #325 merged as `5d0afd8396b98f95c5d003c6392b057d7faa5003`.
T1 PR #331 merged as `64da1bd9dd00e64be4e5ddbfce32e53f19c8f2af` after every
required check passed. Its deployment [33967260852](https://github.com/Flippylolz/WEF/actions/runs/33967260852)
completed successfully. The old Telegram worker was stopped before that merge;
public readiness returned HTTP 200 during the planned pause. The new worker and
public application containers were healthy after activation.

## Fixed original cohort

A read-only aggregate snapshot at `2026-09-05T12:51:37.892863Z`, after stopping
the old worker, contained 28,831 raw events for the configured channel:

- 27,866 pending originals: 27,656 below the previous attempt limit and 210 exhausted.
- 965 previously terminal rows, with 1,522,346 total recorded attempts.
- Pending rows with recorded failures had only the safe category `RunLockHeldError`.

The observation query fixes the received-at boundary to that snapshot, separates
new arrivals, and counts completions after the boundary. Previously terminal row
counts/attempt sums and an aggregate original-ID/checksum fingerprint are compared
to the baseline. No source payload, UUID list, contact, credential, or checksum
export is included in this document.

## Initial T1 observation

At `2026-09-05T12:58:09.278009Z`:

- Migration `20260905_0020` was active.
- All 100 canary originals were verified; recovery had expanded to `running` with no pause reason.
- 312 fixed-cohort originals had completed; 27,554 remained pending.
- There were zero receipt checksum mismatches and zero newly terminal cohort rows without receipts.
- All 965 previously terminal rows retained the same 1,522,346 total attempts.
- The original archive fingerprint matched the baseline.

## Completed T1 acceptance window

The fixed-cohort observation ran from `2026-09-05T12:58:09.278009Z` through
`2026-09-05T13:13:10.271109Z`, exceeding 15 minutes after activation.

| Observation | Completed originals since baseline | Pending originals |
| --- | ---: | ---: |
| First post-release sample | 312 | 27,554 |
| 13:04:37Z | 1,900 | 25,966 |
| 13:08:41Z | 2,950 | 24,916 |
| Final sample | 4,050 | 23,816 |

The window completed another 3,738 originals. Every sampled observation retained
zero receipt checksum mismatches and zero newly terminal cohort rows without a
receipt. All 965 prior terminal rows kept exactly 1,522,346 attempts, and the
original archive fingerprint stayed unchanged. The 100-record canary remained
verified, with recovery in `running` and no pause reason. The final global receipt
counts were 3,520 already canonical, 569 applied, and one superseded; the fixed
cohort excludes newly archived observations.

The operator preflight after the window still excluded 210 exhausted lock retries;
T2 owns their automatic rescheduling. At 13:09:51Z the worker reported connected
transport, a running consumer/reconciliation loop, checkpoint and remote head both
29,713, and no error category. Public readiness returned HTTP 200.

T1 acceptance is complete. Recovery continues automatically for the remaining
originals. T2's dependency gate is satisfied by this measured evidence and merged
PR #331; this does not claim T2/T3/T4 production acceptance.

## T2 release and incomplete production acceptance

PR [#334](https://github.com/Flippylolz/WEF/pull/334) passed every required check
on `acc7fda7e55f315f6f49c0b5f329c0896d69da97` and merged as
`5fd175f95893155260c9da2ab92d334c1b7e9554`. Deployment
[33968987579](https://github.com/Flippylolz/WEF/actions/runs/33968987579)
completed successfully at `2026-09-05T13:33:16Z`. Additive migration
`20260905_0021` retained all prior receipts, source evidence, and attempt history.

| UTC observation | Applied high-water | Polled through | Sweep after | Resolved exhausted lock retries |
| --- | ---: | ---: | ---: | ---: |
| 13:33:31 | 29,713 | 0 | 0 | 90 |
| 13:35:03 | 29,713 | 466 | 101 | 210 |
| 13:37:59 | 29,713 | 898 | 201 | 210 |
| 13:40:34 | 29,713 | 1,311 | 332 | 210 |

The sweep retained its fixed upper bound of 29,713. Polling bootstrapped from zero
rather than treating the applied maximum as traversed history. All 210 historical
lock-exhausted records completed automatically with their deferral history
retained; no pending `RunLockHeldError` remained. Runtime diagnostics subsequently
reported the same applied/polled values as the database, with `history_limited`
true, connected transport, running consumer/reconciliation, and no error category.
The integration suite separately verifies the operator projection of these same
committed meanings.

One worker restart occurred at `13:38:23Z` during diagnostics; the operator-status
subprocess exited 137. Its cause was not established: subsequent inspect reported
OOMKilled false and current cgroup memory-event counters were zero. The container
became healthy, its restart count remained one at the following check, and durable
polling/sweep progress resumed beyond 898/201 to 1,311/332 without a cursor reset.
No restart was deliberately injected and no resource setting was changed.

At `2026-09-05T13:41:39.912824Z`, the fixed original cohort had 9,750 completions
and 18,116 pending records. Receipt checksum mismatches and newly terminal cohort
rows without receipts remained zero; prior terminal attempts and the original
fingerprint still matched the baseline. Recovery remained running with no pause
reason, and public readiness returned HTTP 200.

### Remaining source-evidence limitation

Bootstrap and recovery encounter equal-timestamp revisions that cannot be proven
equivalent. At 13:40:34Z, 1,457 pending observations had recorded data failures and
none had yet reached quarantine. A bounded read-only sample of 100 failed
observations found `conflicting source revisions at equal source time` in all 100;
this is a sample, not a classification of every failure. Canonical records were
preserved, and healthy originals continued completing. The five-failure policy
and one-exception quarantine/re-evaluation behavior are covered by integration
tests; no production budget reset or source-conflict override was performed.

This residual ambiguity requires separately reviewed source-equivalence evidence
before any repair. It does not certify the backlog or source history as complete.
T1 is done. T2 production acceptance remains open because of the repeated
heartbeat failures below. T3/T4 remain proposed and the epic stays in progress.

### Acceptance failure and containment

Later checks found repeated restarts, not a single isolated diagnostic interruption.
The worker logged `telegram_worker_stage_failed` with stage `health` and category
`OSError` at 13:38:21Z, 13:41:57Z, and 13:45:23Z. The earlier exit-137 diagnostic
therefore does not establish an OOM cause. The 64 MiB `/tmp` tmpfs grew from 21 MiB
to 41 MiB after a restart while the host filesystem retained ample free capacity.
The code downloads bootstrap media into `/tmp/wef-telegram-media` without a total
staging budget or successful-file cleanup, sharing capacity with the heartbeat.
Temporary-space exhaustion is the leading explanation; the retained safe event
category alone does not establish the precise OS errno.

The last pre-pause sample at 13:44:21Z counted 9,875 completed fixed-cohort originals
and 17,991 pending, with all original/receipt invariants unchanged. Polling had
reached 1,756 and the older-ID sweep 466 while applied high-water stayed 29,713.
All 210 historical lock-exhausted events remained resolved.

Following the approved systemic-failure procedure, the operator persisted recovery
pause and stopped only the Telegram worker. Source records, receipts, retry budgets,
cursors, and application services were retained. T2 must not be marked done until
a bounded staging correction passes regression tests and stable production
observation. Neither larger temporary storage nor repeated restarts is acceptance.

### Corrected staging activation and probe startup

PR #340 merged as `5e8913a3747f34ae29902fb0994b91352ef8da96` and deployment
[33972300534](https://github.com/Flippylolz/WEF/actions/runs/33972300534) succeeded.
Recovery resumed, temporary use fell to a few KiB, and worker restart count stayed
zero. The initial acceptance window nevertheless failed on repeated health-probe
timeouts: Docker recorded `Health check exceeded timeout (3s)` during polling,
while runtime heartbeats and canonical progress remained fresh. This is distinct
from the earlier heartbeat-write OSError/restart failure.

The file-only liveness entry point imported SQLAlchemy and persistence models
before selecting its mode. A dedicated follow-up defers those imports until full
operator status is requested. It preserves the existing heartbeat freshness,
consumer/transport checks, failure exit codes, CPU limit and 3-second probe timeout.
No broader E24-T4 health-policy change is introduced. T2 acceptance remains open
until the full observation passes on the corrected probe.

The probe follow-up's fresh-process healthy/stale tests pass with ORM imports
blocked. A Docker proof using the exact source, 0.5 CPU and a busy background
process measured five healthy probes at 0.710, 0.699, 0.701, 0.801 and 0.807
seconds, all within the unchanged 3-second timeout. The proof supplies fresh
reconciliation evidence as required by the existing policy.


### T2 final acceptance — passed

The owner explicitly approved publication/deployment of the liveness follow-up
and its completion evidence in Codex task `01a0710e-adaa-76f2-8bcd-07784c03e9b2`.
[PR #341](https://github.com/Flippylolz/WEF/pull/341) passed every required check
and merged as `f700ee3b9b4488b99e71de40d078a490a0361e80` at 15:30:25Z.
[Deployment 33975004167](https://github.com/Flippylolz/WEF/actions/runs/33975004167)
succeeded. The corrected worker became healthy and completed reconciliation before
acceptance began. Concurrent approved E25 migrations through `20260905_0023`
were retained; E24 performed no cursor reset or schema downgrade.

A 900-second observation passed on this exact release, with 20 successful samples
from 2026-09-05T15:38:19Z through 15:53:18Z:

| Measure | First sample | Final sample |
| --- | ---: | ---: |
| Completed originals from the initially pending cohort | 15,750 | 17,144 |
| Pending originals from that cohort | 12,116 | 10,722 |
| Durable applied high-water | 29,713 | 29,713 |
| Durable forward polling boundary | 11,472 | 13,559 |
| Older-known-ID sweep continuation | 3,050 | 3,616 |
| Historical lock-exhausted originals recovered | 210 | 210 |
| Worker restarts | 0 | 0 |
| Receipt checksum mismatches | 0 | 0 |
| Newly terminal originals without receipts | 0 | 0 |

Recovery remained running, transport/consumer/reconciliation stayed healthy,
and no applied or polling boundary decreased. The 965 previously terminal records
retained all 1,522,346 attempts and the frozen original-cohort fingerprint matched
at every sample. Temporary usage peaked at 8,261,632 bytes (about 7.9 MiB); minimum
free space was 58,847,232 bytes, comfortably above the required 8 MiB headroom.
The window completed another 1,394 original records and advanced both forward
polling and older-known-ID reconciliation without operator intervention.

The final release passed `make lint`, `make format-check`, `make typecheck`,
`make contract-check`, and `make test` with the isolated `wef-e24` Compose project:
1,062 backend tests passed with 90.25% coverage, and 169 frontend tests passed.
The completion branch repeated these checks successfully. Relative Markdown links
and whitespace checks also pass.

T2 acceptance is complete. This does not certify complete source-history coverage
or a drained archive: 10,722 original records remain pending, and `history_limited`
remains true. Across all observations, the final aggregate included 15,563 pending
records with data-failure accounting and 497 quarantined records; those counts are
not restricted to the original cohort and must not be added to its pending total.
The earlier bounded sample identified equal-source-time conflicts, but it does
not classify every remaining failure. Source equivalence still requires reviewed
evidence; no retry-budget reset, conflict override, or false completion was used.
T3/T4 remain proposed, so E24 remains in progress.


## T3 durable media recovery rollout — 2026-09-05

Owner approval of implementation-plan revision 3 covers implementation and the
bounded green-CI rollout. [PR #346](https://github.com/Flippylolz/WEF/pull/346)
merged as `abc4a5673f8a67dbf47a4567485b0048a58e928b` after all protected checks
passed. [Release 33981634057](https://github.com/Flippylolz/WEF/actions/runs/33981634057)
succeeded; production retained prior schemas and added `20260905_0024`.

The pre-release aggregate at 17:36:07Z contained 28,117 media assets, 56,078
derivatives, 23,947 public associations, zero derivative failure attempts and
zero duplicate offer/asset associations. These totals do not prove every intended
asset is complete; the new ledger discovers intended work separately.

At 17:48:12Z the durable canary stopped at exactly 100 completed assets, with
1,969 pending, 249 quarantined for unproven source-media equivalence and 1,577
unsupported for unassociated source evidence. Discovery had reached source ID
4,452 against frozen upper bound 29,713. Existing source ambiguity was preserved.
The canary generated zero new derivative attempts: all 100 completions reconciled
already-complete assets. The private `media_recovery_command resume` then enabled
the approved bounded drain, preserving the canary count and all evidence.

Only safe aggregates are recorded here. Raw source records, media, identities,
credentials and database exports were not published.

### T3 runtime observation — passed; repair evidence gate open

Twenty samples over 919 seconds ran on the exact implementation release, from
2026-09-05T17:45:16.512015+00:00 through 2026-09-05T18:00:33.023594+00:00. The observer
started after worker startup became healthy; an earlier startup-state attempt
was discarded and is not counted as acceptance.

| Measure | First sample | Final sample |
| --- | ---: | ---: |
| Completed media work | 0 | 852 |
| Completed work with newly generated variants | 0 | 0 |
| Media discovery continuation | 1,606 | 15,315 |
| Forward polling boundary | 28,921 | 29,713 |
| Older-known-ID sweep continuation | 7,944 | 9,211 |
| Completed original archive cohort | 27,836 | 27,836 |
| Pending original archive cohort | 30 | 30 |
| Worker restarts | 0 | 0 |
| Receipt checksum mismatches | 0 | 0 |
| Duplicate public associations | 0 | 0 |

Transport, consumer and reconciliation stayed healthy on the expected release.
Applied and polling boundaries never decreased. Temporary usage peaked at
4,096 bytes; minimum free space was
67,104,768 bytes, above the required 8 MiB. All 965
previously terminal archive records retained 1,522,346 attempts, the frozen
original fingerprint matched, and no newly terminal original lacked a receipt.

The final media ledger held 852 completed, 11,006 pending, 497 quarantined for
unproven source equivalence and 1,766 unsupported for unassociated source evidence.
Twelve intentions awaited revised-source discovery; the initial frozen range
remained 29,713. Automatic bounded recovery remains running.

The 30 pending original archive records were retry-eligible with one data failure
each, not exhausted; a bounded diagnostic found 4,030 older eligible records ahead
of their earliest deadline. They had no persisted exception classification, so
this evidence does not label them as source conflicts or certify their recovery.

The global media totals remained at the pre-release baseline, with zero derivative
failure attempts. The observation proves safe reuse and continued ingestion, but
provides **no actual production derivative-repair evidence**. Under the approved
plan, T3 remains `in_progress`; the missing repair gate must not be replaced by
synthetic fault injection or an unsupported completion claim. Synthetic crash,
restart and failed/partial-variant recovery tests pass separately. T4 remains
proposed, and E24 remains in progress.

The evidence branch passed `make lint`, `make format-check`, `make typecheck`,
`make contract-check`, and `make test` with the isolated `wef-e24` Compose project:
1,097 backend and 169 frontend tests passed. Relative Markdown links and
`git diff --check` passed. Changed files are this evidence document and the
[E24-T3 task record](tasks/E24-T3-recover-media-after-message-commit.md).
