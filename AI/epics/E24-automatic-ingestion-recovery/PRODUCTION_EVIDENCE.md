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
