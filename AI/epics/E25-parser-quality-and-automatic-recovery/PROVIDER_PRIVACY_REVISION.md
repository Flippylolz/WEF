# E25 revision 2: preserve Zero Data Retention during automatic recovery

## Approved decision

Approve spike revision 2 and implementation plan revision 2 to use durable local
cohorts of single-item Groq Chat Completions requests for scheduled recovery and
existing owner cohorts under the same ZDR configuration. Amend ADR-022's bulk
transport requirement accordingly. Keep `openai/gpt-oss-20b`, contact masking,
strict schema/evidence validation, missing-only field authority, no paid-spend
authorization, and the shared maximum of 20 reserved generation items per UTC day.

This is a transport/privacy compatibility correction. T1/T2 behavior, T4's E24-T1
dependency and all existing protected-data boundaries remain unchanged. No merge,
production activation or external data transmission is requested by this revision.

## Evidence checked on 2026-09-05

Groq's [data controls](https://console.groq.com/docs/your-data) distinguish
ordinary inference from application-state retention. Batch input/output files
are retained for up to 30 days unless deleted earlier; disabling retention also
disables the features requiring that state. The
[Batch documentation](https://console.groq.com/docs/batch) confirms retained input,
intermediate and output files and a separate batch pricing/rate-limit model.

Consequently, the revision 1 combination of required provider Batch transport and
Zero Data Retention cannot operate as specified. Contact masking and deletion
after download do not remove the intervening retained application state. These
are public provider statements, not verification of this account's controls or
free allocation. No authenticated provider request was made for this review.

Local review also found `_complete_many_sequentially` retries 429 responses in
memory in `groq_provider.py`. Reusing that helper unchanged would violate the
approved next-window retry policy and fail durable shared quota accounting.

## Alternatives

| Option | Consequence | Decision |
| --- | --- | --- |
| Required provider Batch plus global ZDR | The provider disables a required endpoint | Cannot implement the approved combination |
| Permit retained Batch application state and delete files promptly | Changes privacy authority and still needs plan/spend verification | Not proposed |
| Durable single-item inference with ZDR | Preserves privacy, uses existing provider/model; lower throughput | Recommended |
| Keep AI recovery disabled indefinitely | Deterministic fixes remain useful but routine exception recovery is unfinished | Temporary state until approval/activation |

## Exact implementation changes

T3 retains the approved durable work identity of source revision, parser version,
policy version and prompt/schema version. Store local cohort/item IDs, attempt ID,
lease/claim, missing-field set, next-eligible time, quota reservation, minimized
outcome, proposal/apply reference and returned provider request ID. New metadata
never copies source text, prompts or provider response bodies.

Reserve each generation attempt transactionally under the same owner allocation
across place review, offer enrichment, ingestion recovery and scheduled work.
Count failed and uncertain attempts. Also account for requests already made in the
UTC day before deployment, so migration cannot reset the allowance. Lower configured
limits win. Permit one provider generation in flight globally for that allocation;
persist a 60-second minimum interval between starts. Local cohorts contain at most
ten items, but only one item is submitted at each eligible maintenance tick.

Persist `submitting` before network I/O and save the validated result durably before
application. Restart resumes queued work and applies already saved proposals
idempotently. An expired submitting attempt without a saved result becomes one
`uncertain_submission` exception; synchronous inference has no job-poll endpoint
for recovering that result, so do not resend it automatically. An uncertain attempt
continues to consume quota. A process crash cannot cause duplicate generation or
a second offer. This unavoidable uncertainty is reported separately from routine
success in the acceptance denominator.

A received 429 defers until the later of Retry-After and the next UTC day. Persist
backoff and release the claim; never use in-memory same-window retries. A known
safe 5xx or proven pre-submission timeout may retry once with another durable quota
reservation. Ambiguous post-submission timeout/network failure is uncertain, not
safe to retry. No network wait holds canonical source/offer locks.

Keep the 30-second HTTP timeout, 5,500 input/1,500 output preflight, 60-second
maintenance cadence, canary of ten eligible revisions, field-family calibration,
revision/snapshot guards and pause controls. Source classification can select up
to 100 records in ten-record transactions, yielding after five seconds and giving
live ingestion priority. Paused application may save an already running request's
validated proposal, but cannot write canonical fields.

For ZDR-enabled configuration, owner and scheduled cohort entry points must use
this same paced, reserved single-item path and must not upload Batch files. Existing
remote Batch jobs, if any, are not reclassified as local requests or resubmitted;
report them for previously authorized reconciliation. Keep the legacy adapter
isolated from the ZDR path; do not claim that retaining its code grants permission
to activate it. Place review remains separately owner-confirmed.

Update ADR-022's Required API boundary and scheduled-authorization wording during
T3, plus security, pipeline and operator docs. ADR-022 is amended by the T3 implementation under this approval. No new production dependency is needed.

## Required additional validation

- Concurrent manual/scheduled reservations and restarts never exceed 20 items/day,
  including requests preceding the new ledger's deployment.
- A claim lost before submission can resume; a claim lost after entering submitting
  becomes uncertain without another provider call.
- A saved proposal resumes through the existing guarded application path without
  duplicate proposal/offer/origin events.
- 429 Retry-After and next-day rollover survive restart without same-window retries.
- The ZDR path never calls Batch/Files endpoints; it enforces shared durable pacing.
- Existing masking, fabricated-span, semantics, stale snapshot, protected-value and
  calibration tests still pass; no field is auto-enabled without required evidence.

The real-provider calibration and representative 24-hour acceptance window remain
activation gates, using authorized credentials and verified live ZDR/free allocation.
Fake providers cannot satisfy those gates. Paid capacity is not authorized.

## Approval history and outstanding dependencies

AD-047 and AD-048 record the approvals of revision 1. Publication was subsequently
authorized in the same Codex task; PRs 327, 328 and 330 are open. The provider
compatibility finding invalidates non-done gates under the repository workflow;
it does not retract prior test results or claim an implemented parser regression.

T3 readiness commit `a9f24f1` was created before this discovery. Its implementation
has not begun and its gate must be restored only after explicit revision 2 approval.
T4 remains blocked on E24-T1/T2/T3. There is no merge authorization.
