---
schema: ai-workflow/proposed-implementation-plan@1
epic: E6
title: "Automated test pyramid critical path"
status: proposed
revision: 8
owner: owner
spike_revision: 2
supersedes: 7
task_sequence:
  - id: E6-T1
    revision: 1
---

# Proposed Implementation Plan: Automated test pyramid (revision 8)

> **Awaiting approval.** Follows completed E6-T3 operational diagnostics.

## Context

- E6-T2/T3/T4/T5/T6/T7 are `done`; E4-T3 and E5-T3 dependencies for E6-T1 are `done`.
- Spike revision 2 confirmed the remaining gap: no browser/e2e tests (Playwright/Cypress absent).
- Unit, contract, PostGIS integration, vitest-axe a11y, and deploy smoke already exist; this revision closes the browser critical-path layer only.

## Goal

Promote and execute **E6-T1 revision 1**: add Chromium Playwright coverage for the grouped pin → offer list → offer detail critical path (plus API error/missing-link states) using synthetic fixtures with no personal data, wired into CI.

## Ordered sequence

### 1. E6-T1 (revision 1) — Complete automated test pyramid

- Scope: Playwright `@playwright/test` (web devDependency), route-mocked `/api/v1/*` fixtures, critical-path e2e specs, CI install Chromium + run, Makefile/`package.json` targets.
- Out of scope: full multi-browser matrix, load testing, Dependabot (E1-T6/T7), Prometheus, new product features, live NUC e2e against historical content.

## Owner decision request

1. Approve **this revision 8** under AD-009 continue authority after E6-T3.
2. Promote E6-T1 and implement on `feat/E6-T1-automated-test-pyramid`.
