---
schema: ai-workflow/task@1
id: E1-T3
epic: E1
title: "Add local Docker Compose"
status: in_progress
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
  status: stacked
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:22:02Z"
  evidence:
    - "E1-T2 dependency | branch feature/E1-T2-application-scaffold | PR https://github.com/Flippylolz/WEF/pull/7 | head 127f00c"
    - "Direct parent/sequencing only: E1-T4 | branch ci/E1-T4-baseline | PR https://github.com/Flippylolz/WEF/pull/8 | head 0016b7b"
branch:
  required: true
  name: feature/E1-T3-local-compose
  task_id: E1-T3
  one_task_only: true
  created_at: "2026-08-12T22:22:02Z"
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

- Add `infra/compose.yaml` with PostGIS, API, web, Caddy edge, and a profile-gated on-demand importer.
- Use project-scoped resources, an internal application network plus an edge-only network for Caddy, named database/media volumes, health conditions, and no `container_name`.
- Publish only the configurable edge port in same-origin mode; direct debug ports require explicit profiles/overrides.
- Extend Make with real Compose build/up/down/logs/config and importer dry-run targets.

## Out of scope

- Production deployment/host changes, live Telegram, production data import, backups, authentication, or additional infrastructure.

## Acceptance criteria

- [x] `docker compose config` resolves from safe explicit local values without a production secret.
- [x] Same-origin web/API starts through the edge and only `127.0.0.1:${WEF_PUBLIC_PORT:-3100}` is published.
- [x] PostGIS/API/web/edge health gates pass; database and media state survive service recreation.
- [x] Source export is absent from public services and read-only in explicit importer runs.
- [x] Compose uses no conflicting `container_name` or non-WEF host resource.

## Test plan

- Render/config-lint the topology and inspect published ports/mounts/networks/volumes.
- Build/up, smoke edge web/API, recreate services, and verify seeded synthetic database persistence.
- Run an importer probe that cannot write its source mount, then clean up only WEF-owned local resources.

## Rollout and rollback

Local Docker only. `down` removes WEF containers/network while preserving named data by default; volume deletion requires an explicit local test cleanup. No production host action is part of E1-T3.

## Ready checklist

- [x] Promotion and approval artifacts are recorded.
- [x] E1-T2 ancestor evidence is recorded by a valid `stacked` dependency gate.
- [x] Scope and acceptance match implementation-plan revision 4.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch `feature/E1-T3-local-compose` is created and recorded.
- [x] Branch contains E1-T3 only; its PR opens after verification.

## Verification evidence

- Static/contract suite: 20 backend tests passed, one explicit PostGIS integration test skipped without `TEST_DATABASE_URL`, 95.17% branch coverage; frontend lint/type/tests, OpenAPI generation/lint/static docs, architecture contracts, Markdown links, and Compose config passed.
- Runtime: local PostGIS, API, web, and Caddy services reached healthy state from a clean image build.
- Same origin: `/` and `/api/v1/health/live` succeeded through `127.0.0.1:3100`.
- Isolation: API/web/PostGIS had no host port bindings; Caddy alone bound `127.0.0.1:3100`.
- Persistence: temporary database and media markers survived ordinary owning-container recreation and were removed after verification.
- Importer safety: the operator profile ran `wef-importer-dry-run` from `wef-backend:local`, observed a read-only `/source`, and emitted bounded JSON without reading source contents.
- Operational decision: [AD-010](../../../workflow/AUTONOMOUS_DECISIONS.md#ad-010-use-a-two-network-local-edge-topology-and-a-bounded-importer-probe).

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
