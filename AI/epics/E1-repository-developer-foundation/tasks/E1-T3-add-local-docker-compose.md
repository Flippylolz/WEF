---
schema: ai-workflow/task@1
id: E1-T3
epic: E1
title: "Add local Docker Compose"
status: draft
revision: 2
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: []
decision_ids: [ADR-005, ADR-008, ADR-010, ADR-018]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T3-add-local-docker-compose.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T22:07:21Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:07:21Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:07:21Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E1-T3
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E1-T3: Add local Docker Compose

## Outcome

Provide an isolated local PostGIS/API/web topology with persistent database state and importer-only read-only source access.

## Scope

- Add `infra/compose.yaml` with PostGIS, API, web, optional Caddy edge, and on-demand importer.
- Use project-scoped resources, one internal network, named database/media volumes, health conditions, and no `container_name`.
- Publish only the configurable edge port in same-origin mode; direct debug ports require explicit profiles/overrides.
- Extend Make with real Compose build/up/down/logs/config and importer dry-run targets.

## Out of scope

- Production deployment/host changes, live Telegram, production data import, backups, authentication, or additional infrastructure.

## Acceptance criteria

- [ ] `docker compose config` resolves from safe explicit local values without a production secret.
- [ ] Same-origin web/API starts through the edge and only the intended edge port is published.
- [ ] PostGIS/API/web health gates pass; database state survives service recreation.
- [ ] Source export is absent from public services and read-only in explicit importer runs.
- [ ] Compose uses no conflicting `container_name` or non-WEF host resource.

## Test plan

- Render/config-lint the topology and inspect published ports/mounts/networks/volumes.
- Build/up, smoke edge web/API, recreate services, and verify seeded synthetic database persistence.
- Run an importer probe that cannot write its source mount, then clean up only WEF-owned local resources.

## Rollout and rollback

Local Docker only. `down` removes WEF containers/network while preserving named data by default; volume deletion requires an explicit local test cleanup. No production host action is part of E1-T3.

## Ready checklist

- [x] Promotion and approval artifacts are recorded.
- [ ] E1-T2 ancestor evidence is recorded by a valid dependency gate.
- [x] Scope and acceptance match implementation-plan revision 4.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated branch is created and recorded.
- [ ] Branch/PR contain E1-T3 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
