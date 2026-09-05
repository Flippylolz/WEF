---
schema: ai-workflow/spike@1
epic: E25
title: "Parser quality and automatic recovery"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-006, ADR-012]
domain_docs:
  - AI/ingestion/PIPELINE.md
  - AI/data/QUALITY_AND_READINESS.md
  - AI/operations/OPERATOR_COMMANDS.md
proposed_task_ids: [E25-T1, E25-T2, E25-T3, E25-T4]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-09-05T11:17:46Z"
  approved_revision: 2
  evidence: "Owner replied continue I approve directly to the explicit request to approve E25 spike revision 2 and implementation plan revision 2 in Codex task 01a0710e-e877-7ab2-ad03-c6008aaf16e9."
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null

---

# Spike: Parser quality and automatic recovery

## Revision 2 decision

Revision 1 approval is retained in AD-050 and Git history. New official provider
evidence invalidates its Batch/ZDR premise for T3. Approve the narrowly scoped
[provider amendment](PROVIDER_PRIVACY_REVISION.md): keep Groq GPT-OSS 20B and Zero
Data Retention, process automatic cohorts as durable single-item Chat Completions
requests, and block provider Batch/Files submission for this ZDR configuration.
T1/T2 behavior and the T4 dependencies are unchanged. All non-done gates require
revalidation under the workflow; completed validation remains evidence.

## Question

Which source-evidenced parsing failures matter most, and how can deterministic extraction, issue classification, and safe automatic recovery improve completeness without inventing facts?

## Context and constraints

Structured offer fields reflect source evidence, parser improvements converge existing records automatically, and AI handles bounded validated exceptions without routine owner review.

The owner selected this audit and requested minimal manual operation on 2026-09-05. Routine human approvals/actions are not the product recovery mechanism. Existing [repository governance](../../governance/REPOSITORY_RULES.md) and [delivery workflow](../../workflow/README.md) still govern implementation revisions and releases. No new production dependency, provider spend increase, destructive data repair, or topology change is implicitly approved.

Affected domain documentation:
- [AI/ingestion/PIPELINE.md](../../../AI/ingestion/PIPELINE.md)
- [AI/data/QUALITY_AND_READINESS.md](../../../AI/data/QUALITY_AND_READINESS.md)
- [AI/operations/OPERATOR_COMMANDS.md](../../../AI/operations/OPERATOR_COMMANDS.md)

## Research method and evidence

Reviewed current `main` at `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`, existing tests, and repository workflow/architecture documentation. Ran locked validation suites and inspected bounded read-only production/GitHub evidence. The [audit](../../audits/2026-09-05-system-audit.md) records command results and separates confirmed behavior from hypotheses.

Audit P1 reproduces the Ostrzycka missing price and included-storage fields with current e2-v13. P2 shows non-candidates are all labeled parser_miss, while some silent omissions are not classified. P3 records 3,294 e2-v11 offers versus five e2-v13 offers and owner-triggered AI recovery. Visible-field absence is a baseline, not an accuracy score.

Primary implementation seams:
- [apps/backend/src/wef_backend/features/ingestion/application/extraction.py](../../../apps/backend/src/wef_backend/features/ingestion/application/extraction.py)
- [apps/backend/src/wef_backend/features/ingestion/application/parse_issue_serialization.py](../../../apps/backend/src/wef_backend/features/ingestion/application/parse_issue_serialization.py)
- [apps/backend/src/wef_backend/features/ingestion/application/raw_replay.py](../../../apps/backend/src/wef_backend/features/ingestion/application/raw_replay.py)
- [apps/backend/src/wef_backend/features/admin/application/ingestion_ai_parse.py](../../../apps/backend/src/wef_backend/features/admin/application/ingestion_ai_parse.py)
- [apps/backend/src/wef_backend/batch_ingestion_ai_parse_command.py](../../../apps/backend/src/wef_backend/batch_ingestion_ai_parse_command.py)

## Options considered

Broadening regular expressions without a negative corpus risks false positives and wrong currency units. Sending every parser_miss row to AI would waste quota on expected non-offers. Manual generate/apply preserves an emergency route but conflicts with the owner's routine automation requirement.

## Recommendation

Build a stratified source-evidence benchmark and truthful issue taxonomy, fix deterministic template/semantic gaps, then automatically schedule only eligible AI exceptions with evidence validation, quotas, and current-revision guards. Add version-aware replay so improvements reach history without operator dispatch.

The task files define proposed acceptance and rollout boundaries, not approval to implement. Policy, contract, migration, retry, and budget choices must be locked in the implementation plan after this spike is approved.

## Proposed task boundaries

- [E25-T1: Benchmark source evidence and classify repairable gaps](tasks/E25-T1-benchmark-source-evidence-and-triage.md) — P1/M; dependencies: none.
- [E25-T2: Repair deterministic field extraction and money semantics](tasks/E25-T2-repair-deterministic-extraction.md) — P1/M; dependencies: E25-T1.
- [E25-T3: Automate validated AI exceptions under durable budgets](tasks/E25-T3-automate-validated-ai-exceptions.md) — P1/L; dependencies: E25-T1.
- [E25-T4: Converge parser versions and field provenance automatically](tasks/E25-T4-converge-parser-versions-automatically.md) — P1/L; dependencies: E24-T1, E25-T2, E25-T3.

## Risks and open questions

Raw text may contain contacts and must remain restricted. Alternate prices are not ranges or exchange-rate evidence. Model confidence is not correctness. Existing owner corrections, AI provenance, visible offer identities, filters, and minor-unit values must survive automatic replay.

The implementer must resolve concrete schema/contract and accepted numeric budgets in the promoted task/plan revisions. Irreducible ambiguity, access loss, protected-field conflict, and destructive recovery are exceptional manual cases; transient errors and routine backlog work must resume automatically. Existing ADR-015 backup deferral remains unchanged.

## Invalidation triggers

Material changes to source semantics, geospatial confidence/precision claims, automatic write authority, schema/contracts, provider choice or cost, release trust boundaries, or the evidence supporting this recommendation return the spike to review. Task sequencing, test, rollout, or rollback changes follow implementation-plan revision rules after approval.

## Exit checklist

- [x] Bounded question answered with one recommendation.
- [x] Evidence and uncertainty distinguishable in the linked audit.
- [x] Affected modules/domain documents and decisions identified.
- [x] Proposed task scope, acceptance, dependencies, and exception handling recorded.
- [x] Outputs are documentation only; no production or disposable proof artifacts created.
- [x] Historical revision 1 approval is retained in AD-051.
- [x] Owner approved revision 2 and its provider transport amendment.

## Historical owner decision for revision 1

The owner replied **“yes I approve”** to the explicit request to approve E25 spike revision 1, promote its four tasks, and prepare the implementation plan. The YAML approval object records that session decision; [AD-051](../../workflow/AUTONOMOUS_DECISIONS.md#ad-051-approve-e25-spike-revision-1-and-prepare-the-implementation-plan) preserves its scope. Implementation plan revision 1 was subsequently approved under AD-052. Revision 2 is explicitly approved on 2026-09-05.

## Revision 2 approval

The owner explicitly approved both spike revision 2 and implementation plan
revision 2 on 2026-09-05. The provider amendment is now the binding transport
baseline. Merge and production activation are not authorized by this approval.
