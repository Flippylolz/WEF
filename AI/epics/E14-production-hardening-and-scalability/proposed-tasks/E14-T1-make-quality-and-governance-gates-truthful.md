---
schema: ai-workflow/proposed-task@1
id: E14-T1
epic: E14
title: "Make quality and governance gates truthful"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: [ADR-009, ADR-012, ADR-013, ADR-017]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E14-T1: Make quality and governance gates truthful

## Outcome

One documented local command and the required CI jobs enforce the same warning-free,
fail-closed quality baseline, while executable checks prove that required-check names,
coverage floors, generated contracts, and governance claims cannot silently diverge.

## Scope

- Define one canonical aggregate verification target and keep focused targets for fast feedback.
- Make frontend lint warnings and unexpected backend/frontend test warnings fail where actionable.
- Reconcile CI job names, Dependabot required checks, repository rules, Makefile help, and release verification.
- Add negative probes for missing/renamed checks, lowered/omitted coverage floors, skipped contract checks, and architecture-check bypass.
- Correct implemented-state documentation encountered within this boundary.

## Out of scope

- Refactoring product/ingestion modules, adding tests solely for coverage, branch-protection plan changes, or selecting security/observability services.

## Acceptance criteria and checks

- [ ] A fresh locked install can run the canonical verification command with no hidden prerequisites.
- [ ] Format, lint, strict types, architecture contracts plus violation probe, backend/frontend tests, contract drift/compatibility, production build, and Markdown links are included or explicitly delegated to an identically named required job.
- [ ] Lint warnings and an approved list of test warnings are zero; any temporary exception is exact, owned, dated, and tested.
- [ ] Executable tests fail when a required CI name is missing/renamed, the Dependabot allowlist drifts, or a coverage/contract/architecture gate is removed.
- [ ] Local, pull-request, main, and release workflows document their differences and do not report partial success as the complete gate.
- [ ] `make format-check`, `make lint`, `make typecheck`, `make test`, `make contract-check`, relevant negative probes, and `python3 scripts/check_markdown_links.py` pass.

## Dependencies and gates

No task dependency. Spike and implementation-plan approval remain mandatory.

## Risks and notes

Avoid one monolithic slow job that harms feedback time; canonical truth can orchestrate
parallel focused jobs as long as missing jobs fail closed.

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
