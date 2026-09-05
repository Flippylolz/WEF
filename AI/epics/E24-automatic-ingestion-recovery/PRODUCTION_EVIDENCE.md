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
