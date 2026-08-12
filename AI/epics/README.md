# Epics

Epics are approval-gated workspaces. Each epic owns `README.md`, a documentation/research-only `SPIKE.md`, an `IMPLEMENTATION_PLAN.md`, and non-actionable `proposed-tasks/`. After spike approval, promotion moves a candidate into `tasks/` so no duplicate authoritative task definition remains. E0 currently has the only promoted task files; they remain `draft` until its implementation plan and task gates pass.

## Priority and size

- **P0**: required for the historical-map MVP.
- **P1**: required for a safe public production launch.
- **P2**: post-launch/future integration.
- **S**: isolated, well-understood change.
- **M**: multi-file feature with tests.
- **L**: cross-component slice or data operation needing review.

Priority, size, roadmap order, milestone assignment, and epic selection never grant implementation permission.

## Linked epic registry

- [E0 — Architecture and dependency spike](E0-architecture-dependency-spike/README.md) — `in_progress`; spike revision 2/plan revision 3 approved, E0-T1 and E0-T2 in progress in the ordered stack; milestones M1.
- [E1 — Repository and developer foundation](E1-repository-developer-foundation/README.md) — `in_progress`; spike revision 2/plan revision 4 approved; E1-T1/E1-T2/E1-T4/E1-T3 in progress, 2 proposed, 1 cancelled; milestones M1.
- [E2 — Historical export parser and audit](E2-historical-export-parser-audit/README.md) — `draft`; 5 tasks (5 proposed); milestones M1, M2.
- [E3 — Database, geocoding, and media pipeline](E3-database-geocoding-media/README.md) — `in_progress`; spike/plan revision 2; E3-T1 in progress, 4 proposed; milestones M1, M2.
- [E4 — Read API and filter contracts](E4-read-api-filter-contracts/README.md) — `approved`; spike/plan revision 2; E4-T1/T2 promoted draft, 2 proposed; milestones M1, M2.
- [E5 — Interactive map frontend](E5-interactive-map-frontend/README.md) — `approved`; spike/plan revision 2; E5-T1/T2 promoted draft, 3 proposed; milestones M1, M3.
- [E6 — Quality, security, and operations](E6-quality-security-operations/README.md) — `draft`; 7 tasks (7 proposed); milestones M3.
- [E7 — Docker/GitHub production delivery](E7-production-delivery/README.md) — `draft`; 7 tasks (6 proposed, 1 deferred); milestones M3.
- [E8 — Future Telegram live ingestion](E8-telegram-live-ingestion/README.md) — `draft`; 5 tasks (5 proposed); milestones M4.

E1/E0 implementation remains in ordered stack layers. E3–E5 M1 spike/plans are approved; E3-T1 is ready and E4/E5 promoted tasks remain dependency-blocked until their parent PRs exist. E2 and E6–E8 remain draft. Reviews and CI still gate base-first merge/completion.

## Global lifecycle

Follow the [approval-gated workflow](../workflow/README.md), [spike template](../workflow/templates/SPIKE.md), [proposed-task template](../workflow/templates/PROPOSED_TASK.md), [implementation-plan template](../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../workflow/DEFINITION_OF_DONE.md):

1. select an epic;
2. complete documentation/research-only spike work;
3. obtain explicit owner approval of that spike revision;
4. refine and move approved candidates from `proposed-tasks/` to `tasks/`;
5. write an implementation plan containing only promoted tasks;
6. obtain explicit owner approval of that plan revision; and
7. satisfy task dependencies/state gates and use one dedicated branch/PR per task.

No production code, generated scaffold, migration, infrastructure/configuration change, executable experiment, prototype, or disposable proof is allowed before the current implementation plan is approved.

## Canonical M1 order

After the relevant epic gates are approved:

1. E1-T1 — repository safety/bootstrap only, establishing the repository required for all dedicated task branches.
2. E0-T1 — review/accept the architecture and dependency proposal on its dedicated branch.
3. E0-T2 — execute the architecture/dependency proof on its dedicated task branch.
4. E1-T2 — web/backend scaffolds from the accepted proof.
5. E1-T4 — establish the full CI baseline before product feature work.
6. E1-T3 — local Docker/PostGIS stack.
7. E3-T1 — M1 location/offer schema, migrations, and explicit deterministic seed.
8. E4-T1 — filtered grouped-GeoJSON endpoint.
9. E4-T2 — canonical facets and selected-location dated offers.
10. E5-T1 — grouped map/list selection and dated result panel.
11. E5-T2 — all URL-backed M1 filters and debounced viewport querying.
12. E1-T6 — enable Dependabot update pull requests without auto-merge.
13. E1-T7 — add the scheduled owner-label/check/bot-commit merge controller.

M1 deliberately excludes historical parsing/import, the complete export, network geocoding, media, auth/contacts, production deployment, and Telegram credentials. Those remain separate tasks/milestones. E1-T5 is cancelled because GitHub-enforced branch protection is out of scope; procedural branch/PR/CI rules remain mandatory.

## Task dependency and traceability registry

YAML `dependencies` contains task IDs only, as required by the workflow. Original roadmap dependencies on `D-*` are preserved in `deferred_decision_ids`; E8-T1's M3 prerequisite is preserved as an explicit milestone gate in its body and this registry. Each ID below links to exactly one authoritative workflow definition under `proposed-tasks/` or, after valid promotion, `tasks/`. The `legacy-roadmap:*` source values record non-path provenance and do not create a second workflow definition.

### E0

- [E0-T1](E0-architecture-dependency-spike/tasks/E0-T1-review-architecture-and-dependency-proposal.md): promoted/in-progress revision 2; stacked dependency `E1-T1`; M1; requirements `none`; decisions `ADR-012, ADR-013, ADR-018`.
- [E0-T2](E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md): promoted/in-progress revision 2; stacked dependencies `E0-T1, E1-T1`; M1; requirements `none`; decisions `ADR-001, ADR-005, ADR-012, ADR-013, ADR-018`.
### E1

- [E1-T1](E1-repository-developer-foundation/tasks/E1-T1-initialize-repository-safety.md): promoted/in-progress; task dependencies `none`; M1; requirements `none`; decisions `ADR-009, ADR-017`.
- [E1-T2](E1-repository-developer-foundation/tasks/E1-T2-scaffold-web-and-backend-applications.md): promoted/in-progress revision 2; stacked dependency `E0-T2`; M1; requirements `none`; decisions `ADR-001, ADR-012, ADR-018`.
- [E1-T4](E1-repository-developer-foundation/tasks/E1-T4-establish-ci-baseline.md): promoted/in-progress revision 1; stacked dependency `E1-T2`; M1; requirements `none`; decisions `ADR-009, ADR-012, ADR-013, ADR-017, ADR-018`.
- [E1-T3](E1-repository-developer-foundation/tasks/E1-T3-add-local-docker-compose.md): promoted/in-progress revision 2; stacked dependency `E1-T2`; M1; requirements `none`; decisions `ADR-005, ADR-008, ADR-010, ADR-018`.
- [E1-T5](E1-repository-developer-foundation/proposed-tasks/E1-T5-configure-protected-main-governance.md): task dependencies `none`; deferred gates D-007; M1; requirements `none`; decisions `ADR-009, ADR-017`.
- [E1-T6](E1-repository-developer-foundation/proposed-tasks/E1-T6-configure-dependabot-update-pull-requests.md): task dependencies `E1-T1, E1-T4`; M1; requirements `none`; decisions `ADR-017`.
- [E1-T7](E1-repository-developer-foundation/proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md): task dependencies `E1-T4, E1-T6`; M1; requirements `none`; decisions `ADR-017`.
### E2

- [E2-T1](E2-historical-export-parser-audit/proposed-tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md): task dependencies `E1-T2`; M1; requirements `P-006, P-007`; decisions `ADR-006`.
- [E2-T2](E2-historical-export-parser-audit/proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md): task dependencies `E2-T1`; M1; requirements `P-002, P-003, P-007`; decisions `ADR-003, ADR-006, ADR-012`.
- [E2-T3](E2-historical-export-parser-audit/proposed-tasks/E2-T3-implement-media-grouping.md): task dependencies `E2-T1`; M2; requirements `P-005`; decisions `ADR-006, ADR-007`.
- [E2-T4](E2-historical-export-parser-audit/proposed-tasks/E2-T4-implement-dry-run-reports.md): task dependencies `E2-T2, E2-T3`; M2; requirements `P-007`; decisions `ADR-006`.
- [E2-T5](E2-historical-export-parser-audit/proposed-tasks/E2-T5-audit-the-complete-export.md): task dependencies `E2-T4`; M2; requirements `P-007`; decisions `ADR-006`.
### E3

- [E3-T1](E3-database-geocoding-media/tasks/E3-T1-create-schema-and-migrations.md): promoted/in-progress revision 2; stacked dependency `E1-T3`; M1; requirements `P-001, P-002, P-007`; decisions `ADR-003, ADR-005, ADR-012`.
- [E3-T2](E3-database-geocoding-media/proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md): task dependencies `E2-T2, E3-T1`; M1; requirements `P-002, P-006, P-007`; decisions `ADR-005, ADR-006, ADR-012`.
- [E3-T3](E3-database-geocoding-media/proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md): task dependencies `E3-T1, E2-T2`; deferred gates D-002; M1; requirements `P-001, P-007`; decisions `ADR-005, ADR-012`.
- [E3-T4](E3-database-geocoding-media/proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md): task dependencies `E2-T3, E3-T1`; M2; requirements `P-005, P-007`; decisions `ADR-007`.
- [E3-T5](E3-database-geocoding-media/proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md): task dependencies `E2-T5, E3-T2, E3-T3, E3-T4`; M2; requirements `P-001, P-002, P-005, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007`.
### E4

- [E4-T1](E4-read-api-filter-contracts/tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md): promoted/draft revision 2; task dependency `E3-T1`; M1; requirements `P-001, P-003`; decisions `ADR-002, ADR-003, ADR-005, ADR-012, ADR-013`.
- [E4-T2](E4-read-api-filter-contracts/tasks/E4-T2-implement-facets-and-location-offer-collection.md): promoted/draft revision 2; task dependency `E4-T1`; M1; requirements `P-001, P-002, P-003`; decisions `ADR-002, ADR-003, ADR-012, ADR-013`.
- [E4-T3](E4-read-api-filter-contracts/proposed-tasks/E4-T3-implement-offer-detail.md): task dependencies `E3-T4, E4-T2`; M2; requirements `P-002, P-005, P-006, P-007, P-008`; decisions `ADR-003, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016`.
- [E4-T4](E4-read-api-filter-contracts/proposed-tasks/E4-T4-harden-api-behavior-and-performance.md): task dependencies `E4-T1, E4-T2, E4-T3, E3-T5`; M2; requirements `P-001, P-002, P-003`; decisions `ADR-012, ADR-013`.
### E5

- [E5-T1](E5-interactive-map-frontend/tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md): promoted/draft revision 2; task dependencies `E1-T2, E4-T2`; M1; requirements `P-001, P-004, P-007`; decisions `ADR-002, ADR-004, ADR-012`.
- [E5-T2](E5-interactive-map-frontend/tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md): promoted/draft revision 2; task dependencies `E5-T1, E4-T2`; M1; requirements `P-001, P-003, P-004`; decisions `ADR-002, ADR-003, ADR-012`.
- [E5-T3](E5-interactive-map-frontend/proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md): task dependencies `E4-T3, E5-T1`; M3; requirements `P-002, P-005, P-006, P-007`; decisions `ADR-003, ADR-004, ADR-007, ADR-012`.
- [E5-T4](E5-interactive-map-frontend/proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md): task dependencies `E5-T2, E5-T3`; M3; requirements `P-001, P-002, P-003, P-004, P-005`; decisions `ADR-002, ADR-004, ADR-012`.
- [E5-T5](E5-interactive-map-frontend/proposed-tasks/E5-T5-performance-and-production-ux-pass.md): task dependencies `E5-T4, E4-T4`; M3; requirements `P-001, P-004, P-005`; decisions `ADR-004, ADR-007, ADR-012`.
### E6

- [E6-T1](E6-quality-security-operations/proposed-tasks/E6-T1-complete-automated-test-pyramid.md): task dependencies `E4-T3, E5-T3`; M3; requirements `P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008`; decisions `ADR-012, ADR-013, ADR-016`.
- [E6-T2](E6-quality-security-operations/proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md): task dependencies `E3-T4, E4-T3, E5-T3`; M3; requirements `P-002, P-005, P-006, P-007, P-008`; decisions `ADR-007, ADR-011, ADR-013, ADR-016`.
- [E6-T3](E6-quality-security-operations/proposed-tasks/E6-T3-add-operational-diagnostics.md): task dependencies `E3-T2, E4-T4`; M3; requirements `P-007`; decisions `ADR-008, ADR-010, ADR-014, ADR-015`.
- [E6-T4](E6-quality-security-operations/proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md): task dependencies `E1-T2, E3-T1`; M3; requirements `P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T5](E6-quality-security-operations/proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md): task dependencies `E2-T2, E3-T1, E4-T3, E6-T4`; M3; requirements `P-002, P-007, P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T6](E6-quality-security-operations/proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md): task dependencies `E5-T3, E6-T4, E6-T5`; M3; requirements `P-002, P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T7](E6-quality-security-operations/proposed-tasks/E6-T7-implement-owner-administration-console.md): task dependencies `E6-T4, E6-T5`; M3; requirements `P-008`; decisions `ADR-011, ADR-012, ADR-016`.
### E7

- [E7-T1](E7-production-delivery/proposed-tasks/E7-T1-build-production-compose-topology.md): task dependencies `E1-T3, E6-T2, E6-T3`; M3; requirements `none`; decisions `ADR-005, ADR-008, ADR-010, ADR-014, ADR-015`.
- [E7-T2](E7-production-delivery/proposed-tasks/E7-T2-provision-and-verify-supplied-server.md): task dependencies `E7-T1`; deferred gates D-001; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-015`.
- [E7-T3](E7-production-delivery/proposed-tasks/E7-T3-implement-github-image-and-deployment-workflows.md): task dependencies `E1-T4, E7-T1, E7-T2`; M3; requirements `none`; decisions `ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017`.
- [E7-T4](E7-production-delivery/proposed-tasks/E7-T4-implement-health-verification-and-rollback.md): task dependencies `E7-T3`; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-015`.
- [E7-T5](E7-production-delivery/proposed-tasks/E7-T5-future-backup-and-restore-capability.md): task dependencies `none`; M3; requirements `none`; decisions `ADR-015`.
- [E7-T6](E7-production-delivery/proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md): task dependencies `E3-T5, E7-T2, E7-T4`; deferred gates D-002; M3; requirements `P-001, P-002, P-005, P-007`; decisions `ADR-005, ADR-006, ADR-007, ADR-010, ADR-015`.
- [E7-T7](E7-production-delivery/proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md): task dependencies `E6-T4, E6-T5, E6-T6, E6-T7, E7-T4`; M3; requirements `P-008`; decisions `ADR-010, ADR-011, ADR-014, ADR-016`.
### E8

- [E8-T1](E8-telegram-live-ingestion/proposed-tasks/E8-T1-confirm-channel-identity-and-access.md): task dependencies `none`; deferred gates D-003; milestone prerequisite M3; M4; requirements `P-006`; decisions `ADR-006`.
- [E8-T2](E8-telegram-live-ingestion/proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md): task dependencies `E8-T1, E3-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-005, ADR-006, ADR-007`.
- [E8-T3](E8-telegram-live-ingestion/proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md): task dependencies `E8-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007`.
- [E8-T4](E8-telegram-live-ingestion/proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): task dependencies `E3-T3`; deferred gates D-002; M4; requirements `P-001, P-007`; decisions `ADR-005, ADR-006`.
- [E8-T5](E8-telegram-live-ingestion/proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md): task dependencies `E8-T3, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-006, ADR-010, ADR-015`.

Bootstrap and production gates are preserved: E0-T1 depends on E1-T1 so its dedicated branch can exist; E0-T2 depends on E0-T1 and E1-T1; E1-T2 depends on E0-T2; E7-T2 retains D-001 plus E7-T1; E7-T3 retains E1-T4/E7-T1/E7-T2; E7-T6 retains E3-T5/E7-T2/E7-T4 plus D-002; and E7-T7 retains E6-T4/E6-T5/E6-T6/E6-T7/E7-T4. E8-T5 depends only on E8-T3 and E8-T4—it does not depend on deferred E7-T5.

## Global definition of done

A task is complete only when:

- Acceptance criteria and affected requirements pass.
- Unit/integration/end-to-end coverage is proportionate to risk.
- Format, lint, type, migration, contract, and production build checks pass as applicable.
- Backend architecture/import contracts pass; domain/application rules are not duplicated in routes, presenters, ORM models, or frontend code.
- User-visible/error/empty/loading states are handled.
- Logs and fixtures contain no secrets or unreviewed personal data.
- Relevant documents in this directory are updated.
- Operational changes include rollback/recovery instructions.
- No raw export/media is added to Git or image layers.

The workflow's [expanded definition of done](../workflow/DEFINITION_OF_DONE.md) adds mandatory approval, promotion, dependency, branch, evidence, security, operational, and completion-record gates and cannot be weakened by this summary.

## Product-requirement coverage

- Grouped map pins and clusters: E4-T1, E5-T1.
- Dated, non-availability offer presentation: E4-T3, E5-T3.
- All MVP filters and shareable URLs: E4-T1, E4-T2, E5-T2.
- Map/list coordination, viewport loading/errors, and filter preservation: E5-T2, E5-T4, E5-T5.
- Responsive detail, accessible image/video media, and missing-media states: E3-T4, E5-T3, E5-T4.
- Attribution, source traceability, and confidence indicators: E4-T3, E5-T1, E5-T3, E6-T2.
- WCAG 2.2 AA public flows: E5-T4, E6-T1.
- Matching/non-matching related-offer disclosure: E4-T2, E5-T3.
- Anonymous browsing plus username/password registration, owner administration, and audited contact reveal: E6-T4 through E6-T7, E7-T7.
- English-first i18n-keyed interface: E6-T6.
- Verified Telegram links: E4-T3, E5-T3, then E8-T1 for live data.
- Import traceability and failure accounting: E2-T4, E3-T2, E3-T5.
- Geocoding accuracy/review: E3-T3, E3-T5.
- Procedural feature branches/hotfix ownership plus required CI workflows: E1-T4 and [repository and change rules](../governance/REPOSITORY_RULES.md); enforced `main` protection is out of scope.
- Dependabot update pull requests: E1-T6.
- Scheduled owner-label/check/bot-commit-gated Dependabot merge workaround: E1-T7.
- Persistent PostgreSQL/media/checkpoint data outside Git: E3-T1, E3-T2, E3-T4, E7-T1; backups are deferred in E7-T5.
- Dockerized GitHub deployment: E7-T1 through E7-T4.
- Resumable verified source transfer and production import: E7-T6.
- Monitoring, contact-data minimization, and accessibility: E5-T4, E6-T2, E6-T3, E6-T5; backups are deferred in E7-T5 and a formal privacy notice is out of scope.
- Future live channel ingestion: E8-T1 through E8-T5.
