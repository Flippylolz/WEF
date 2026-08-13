---
schema: ai-workflow/task@1
id: E2-T5
epic: E2
title: "Audit the complete export"
status: done
revision: 2
priority: P0
size: L
milestone: M2
dependencies: [E2-T4]
requirement_ids: [P-007]
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E2-T5-audit-the-complete-export.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T18:58:46Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:58:46Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:46:00Z"
  evidence:
    - "E2-T4 | done | merged PR https://github.com/Flippylolz/WEF/pull/40 | merge 6cf1fec"
branch:
  required: true
  name: feature/E2-T5-complete-export-audit
  task_id: E2-T5
  one_task_only: true
  created_at: "2026-08-13T19:46:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/42"
completion:
  completed_by: "Cursor Agent (owner-authorized)"
  completed_at: "2026-08-13T20:03:40Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/42"
  evidence:
    - "Complete read-only e2-v2 audit succeeded: approved 21,634,277-byte source and SHA-256 verified; 27,082 records, 2,991 candidates plus 24,091 non-candidates, and 27,147 media descriptors fully reconciled"
    - "Material source-template gaps were fixed with sanitized regression cases: apartment price 2,049 to 2,881, room extraction 72 to 2,418, and invalid-range warnings 988 to 6; two post-fix runs had identical non-timing reports"
    - "Local gates passed: frozen install, format, Ruff, import-linter, strict mypy/TypeScript, branch-coverage backend/frontend tests, contracts/docs, Compose, production proofs, and backend/frontend runtime image builds"
    - "Initial PR https://github.com/Flippylolz/WEF/pull/42 CI run 31738741521 passed Backend, Frontend and contract, Repository safety, and Runtime images before completion evidence was recorded"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E2-T5: Audit the complete export

> Promoted under revision 3, but blocked until E2-T4 is merged and its dependency evidence is recorded.

## Outcome

Produce reproducible, non-sensitive evidence that the approved parser accounts for the complete historical Telegram export and explicitly explains uncertainty, gap categories, and differences from exploratory planning estimates.

## Scope

- Verify the ignored source file is exactly 21,634,277 bytes with SHA-256 `d349e27003058f470fa53e5cd9004fe6759e8db466bc690f132398e038816249`.
- Run the E2-T4 pipeline read-only across all 27,082 records.
- Review candidate/reason/template/extraction/media buckets, unknowns, conflicts, boundary cases, false positives/negatives, and unassociated media.
- Explain differences from the exploratory roughly 3,000-candidate estimate and reproducible token counters.
- Add only irreversibly sanitized fixtures and deterministic rule fixes for material gaps; bump parser version when behavior changes.
- Commit a non-sensitive `AUDIT.md` with parser/source identity, aggregate counts, uncertainty, reviewed categories, and reproducibility commands.

## Out of scope

- Raw/private source samples, contact values, source media, generated detailed reports, or internal paths in Git/CI/logs.
- Database persistence/import, migration, geocoding, media copy, public API changes, map-seed replacement, or production promotion.

## Acceptance criteria

- [ ] Approved source size and SHA-256 are verified before accepting audit results.
- [ ] All 27,082 records reconcile through source, candidate, extraction, and media stages with no unexplained count gap.
- [ ] Candidate/rule/template/conflict/unassociated-media categories are reviewed with documented uncertainty.
- [ ] Differences from exploratory candidate/token counters are explained.
- [ ] Material fixes are deterministic, versioned, covered by sanitized fixtures, and followed by a complete rerun.
- [ ] `AUDIT.md` contains only aggregate/non-sensitive evidence and reproducibility commands.
- [ ] Detailed reports/raw samples/media/contacts remain outside Git, CI, and routine logs.
- [ ] Epic completion is recorded only after local audit evidence and all final required CI jobs pass.

## Test plan

- Run the complete ignored export with the approved parser/report versions and checksum precondition.
- Run full backend/repository gates after every material rule or fixture change.
- Scan committed audit/fixture artifacts for source identity, contacts, paths, payload/text samples, media references, and binary content.
- Re-run deterministic report generation and compare all non-timing fields/hashes.

## Rollout and rollback

This task publishes aggregate audit evidence and, only if required, bounded parser/fixture fixes. Revert the task PR to roll back code/evidence; no persisted source, canonical data, or media cleanup is required.

## Ready checklist

- [x] Promotion and current spike/implementation gates are recorded.
- [x] E2-T4 is `done`; dependency gate is satisfied.
- [x] Status passed through `ready` after the dependency completed.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E2-T5 branch is created from latest `main`.
- [x] Branch contains E2-T5 only; branch metadata is recorded.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
