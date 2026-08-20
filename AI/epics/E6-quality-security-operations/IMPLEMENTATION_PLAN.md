---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Automated test pyramid critical path"
status: approved
revision: 8
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T1
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T17:16:12Z"
  approved_revision: 8
  evidence: "Owner continue after E6-T3; AD-009 bounded plan revision; E6 spike revision 2; E6-T1 dependencies E4-T3/E5-T3 done"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Automated test pyramid (revision 8)

> Revision 8 authorizes only E6-T1 revision 1 after E6-T3.

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: ADR-012/013/016; existing vitest/pytest/contract CI remain authoritative lower layers.
- E6-T3 is `done`; E4-T3 and E5-T3 are `done`.

## Scope and outcome

Close the spike-confirmed browser/e2e gap with Chromium Playwright critical-path coverage for map explorer location selection, offer list, offer detail (verified and missing source links), and API error states — using synthetic fixtures only.

## Ordered task sequence

### 1. E6-T1 (revision 1) — Complete automated test pyramid

- Task: [E6-T1](tasks/E6-T1-complete-automated-test-pyramid.md).
- Independently reviewable: Playwright config + synthetic API mocks + critical-path specs + CI Chromium job.
- Dependencies: E4-T3, E5-T3 — both `done`.
- Affected modules: `apps/web` Playwright tooling/specs, CI frontend job, Makefile/`package.json` scripts, E6 indexes.
- Tests: e2e critical path; negative fixtures for API failure and missing verified links; no unreviewed personal data.
- Out of scope: Firefox/WebKit matrix, load tests, Dependabot, metrics backends, live historical content assertions.

## Security and privacy

- Fixtures reuse invented M1 synthetic IDs/names only.
- Do not scrape or assert live production historical source text.

## Operations, rollout, and rollback

- CI installs Chromium only; local `pnpm --filter web test:e2e`.
- Rollback: remove Playwright job/deps; unit/contract layers remain.

## Owner decision

Flippylolz authorized continuation after E6-T3 (chat continue 2026-08-20). Revision 8 sequences E6-T1 revision 1 only.
