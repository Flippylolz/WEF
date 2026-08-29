# Epics

Epics are approval-gated workspaces. Each epic owns `README.md`, a documentation/research-only `SPIKE.md`, an `IMPLEMENTATION_PLAN.md`, and non-actionable `proposed-tasks/`. After spike approval, promotion moves a candidate into `tasks/` so no duplicate authoritative task definition remains.

## Priority and size

- **P0**: required for the historical-map MVP.
- **P1**: required for a safe public production launch.
- **P2**: post-launch/future integration.
- **S**: isolated, well-understood change.
- **M**: multi-file feature with tests.
- **L**: cross-component slice or data operation needing review.

Priority, size, roadmap order, milestone assignment, and epic selection never grant implementation permission.

## Linked epic registry

- [E0 — Architecture and dependency spike](E0-architecture-dependency-spike/README.md) — `done`; spike revision 2/plan revision 3 approved, E0-T1 and E0-T2 done; milestones M1.
- [E1 — Repository and developer foundation](E1-repository-developer-foundation/README.md) — `done`; spike revision 2; E1-T1–T4, E1-T6, E1-T7 done; E1-T5 cancelled; milestones M1.
- [E2 — Historical export parser and audit](E2-historical-export-parser-audit/README.md) — `done`; spike/plan revision 3 approved and E2-T1–T5 done with a reconciled complete-export audit; milestones M1, M2.
- [E3 — Database, geocoding, and media pipeline](E3-database-geocoding-media/README.md) — `done`; spike/plan revision 4 approved; E3-T1–T5 done with E3-T5's terminal local reconciliation on PRs #65/#66; milestones M1, M2.
- [E4 — Read API and filter contracts](E4-read-api-filter-contracts/README.md) — `done`; spike/plan revision 2; E4-T1/T2 done through PRs #12/#13, 2 proposed (unactionable M2 candidates); milestones M1, M2.
- [E5 — Interactive map frontend](E5-interactive-map-frontend/README.md) — `done`; spike/plan revision 3; E5-T1–T5 done; milestones M1, M3.
- [E6 — Quality, security, and operations](E6-quality-security-operations/README.md) — `done`; spike revision 2 / plan revision 8; E6-T1–T7 done; milestones M3.
- [E7 — Docker/GitHub production delivery](E7-production-delivery/README.md) — `done`; spike revision 4 / plan revision 9; E7-T1–T4 and E7-T6–T11 done, E7-T5 deferred; milestone M3.
- [E8 — Future Telegram live ingestion](E8-telegram-live-ingestion/README.md) — `in_progress`; spike revision 2 and plan revision 5 approved; E8-T4 done, E8-T1/T2/T3/T5 in operational acceptance; D-002 resolved and D-003/B-003 retains live-evidence work; milestone M4.
- [E9 — Account registration modal](E9-account-registration-modal/README.md) — `done`; E9-T1 done; milestone M3.
- [E10 — Property favorites](E10-property-favorites/README.md) — `done`; E10-T1 done; milestone M3.
- [E11 — Scalable quick filters](E11-scalable-quick-filters/README.md) — `done`; E11-T1 done; milestone M3.
- [E12 — Database index audit](E12-database-index-audit/README.md) — `done`; E12-T1 done; milestone M3.
- [E13 — Dark map-first listing explorer](E13-dark-map-explorer/README.md) — `done`; spike/plan revision 1 approved (AD-038); E13-T1–T3 done through PRs #176/#179/#180; milestones M4.
- [E14 — Production hardening and scalability](E14-production-hardening-and-scalability/README.md) — `selected`; spike revision 1 awaits owner approval; E14-T1–T9 proposed/non-actionable; milestone M5.
- [E15 — Telegram ingestion reliability recovery](E15-telegram-ingestion-reliability/README.md) — `done`; spike/plan revision 1 approved under AD-039/AD-040; E15-T1–T3 completed through green-CI PRs #189/#190/#191 with production recovery evidence; milestone M4 remains open only for residual E8 acceptance.

The original E0–E7 MVP stack and M3 add-ons E9–E12 are complete on `main`. E8 live Telegram ingestion is on `main` with an authorized production worker. E15 completed the blocker-priority source-completeness, health, gap-repair, and outage-recovery work under AD-039/AD-040; E8/M4 honestly retain real passive new/edit/delete and live-media acceptance. E13's dark map-first redesign is done. E14 remains selected for broader post-launch research/planning and its candidates retain their own approval gates. New work must pass its dedicated pull-request CI before merge.

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

The synthetic map sequence deliberately excludes historical import, the complete export, network geocoding, media, auth/contacts, and Telegram credentials. E2-T1 separately begins the read-only historical source boundary and safe fixture corpus without replacing the persisted M1 seed. E1-T5 is cancelled because GitHub-enforced branch protection is out of scope; procedural branch/PR/CI rules remain mandatory.

## Task dependency and traceability registry

YAML `dependencies` contains task IDs only, as required by the workflow. Original roadmap dependencies on `D-*` are preserved in `deferred_decision_ids`; E8-T1's M3 prerequisite is preserved as an explicit milestone gate in its body and this registry. Each ID below links to exactly one authoritative workflow definition under `proposed-tasks/` or, after valid promotion, `tasks/`. The `legacy-roadmap:*` source values record non-path provenance and do not create a second workflow definition.

### E0

- [E0-T1](E0-architecture-dependency-spike/tasks/E0-T1-review-architecture-and-dependency-proposal.md): promoted/done revision 2; satisfied dependency `E1-T1`; M1; requirements `none`; decisions `ADR-012, ADR-013, ADR-018`.
- [E0-T2](E0-architecture-dependency-spike/tasks/E0-T2-execute-and-lock-the-architecture-proof.md): promoted/done revision 2; satisfied dependencies `E0-T1, E1-T1`; M1; requirements `none`; decisions `ADR-001, ADR-005, ADR-012, ADR-013, ADR-018`.
### E1

- [E1-T1](E1-repository-developer-foundation/tasks/E1-T1-initialize-repository-safety.md): promoted/done; task dependencies `none`; M1; requirements `none`; decisions `ADR-009, ADR-017`.
- [E1-T2](E1-repository-developer-foundation/tasks/E1-T2-scaffold-web-and-backend-applications.md): promoted/done revision 2; satisfied dependency `E0-T2`; M1; requirements `none`; decisions `ADR-001, ADR-012, ADR-018`.
- [E1-T4](E1-repository-developer-foundation/tasks/E1-T4-establish-ci-baseline.md): promoted/done revision 1; satisfied dependency `E1-T2`; M1; requirements `none`; decisions `ADR-009, ADR-012, ADR-013, ADR-017, ADR-018`.
- [E1-T3](E1-repository-developer-foundation/tasks/E1-T3-add-local-docker-compose.md): promoted/done revision 2; satisfied dependency `E1-T2`; M1; requirements `none`; decisions `ADR-005, ADR-008, ADR-010, ADR-018`.
- [E1-T5](E1-repository-developer-foundation/proposed-tasks/E1-T5-configure-protected-main-governance.md): task dependencies `none`; deferred gates D-007; M1; requirements `none`; decisions `ADR-009, ADR-017`.
- [E1-T6](E1-repository-developer-foundation/tasks/E1-T6-configure-dependabot-update-pull-requests.md): task dependencies `E1-T1, E1-T4`; M1; requirements `none`; decisions `ADR-017`.
- [E1-T7](E1-repository-developer-foundation/tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md): task dependencies `E1-T4, E1-T6`; M1; requirements `none`; decisions `ADR-017`.
### E2

- [E2-T1](E2-historical-export-parser-audit/tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md): promoted/done revision 2 through [PR #33](https://github.com/Flippylolz/WEF/pull/33); satisfied dependency `E1-T2` and approved spike/implementation gates; M1; requirements `P-006, P-007`; decisions `ADR-006, ADR-012`.
- [E2-T2](E2-historical-export-parser-audit/tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md): promoted/done revision 2 through [PR #36](https://github.com/Flippylolz/WEF/pull/36); satisfied dependency `E2-T1` and approved revision 3 gates; M1; requirements `P-002, P-003, P-007`; decisions `ADR-003, ADR-006, ADR-012`.
- [E2-T3](E2-historical-export-parser-audit/tasks/E2-T3-implement-media-grouping.md): promoted/done revision 2 through [PR #37](https://github.com/Flippylolz/WEF/pull/37); satisfied dependencies `E2-T1, E2-T2`; M2; requirements `P-005`; decisions `ADR-006, ADR-007`.
- [E2-T4](E2-historical-export-parser-audit/tasks/E2-T4-implement-dry-run-reports.md): promoted/done revision 2 through [PR #40](https://github.com/Flippylolz/WEF/pull/40); satisfied dependencies `E2-T2, E2-T3`; M2; requirements `P-007`; decisions `ADR-006`.
- [E2-T5](E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md): promoted/done revision 2 through [PR #42](https://github.com/Flippylolz/WEF/pull/42); satisfied dependency `E2-T4`; M2; requirements `P-007`; decisions `ADR-006`.
### E3

- [E3-T1](E3-database-geocoding-media/tasks/E3-T1-create-schema-and-migrations.md): promoted/done revision 2; satisfied dependency `E1-T3`; M1; requirements `P-001, P-002, P-007`; decisions `ADR-003, ADR-005, ADR-012`.
- [E3-T2](E3-database-geocoding-media/tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md): promoted/done revision 2 through [PR #53](https://github.com/Flippylolz/WEF/pull/53); satisfied dependencies `E2-T2, E3-T1` and approved revision 3 spike/plan gates; M1; requirements `P-002, P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-012`.
- [E3-T3](E3-database-geocoding-media/tasks/E3-T3-implement-geocoder-abstraction-and-cache.md): promoted/`done` revision 3 through PR #59 after revision-4 gate revalidation on 2026-08-15; task dependencies `E2-T2, E3-T1, E3-T2`; historical Geoapify selected by accepted ADR-021; D-002 remains only for recurring E8-T4; M1; requirements `P-001, P-007`; decisions `ADR-005, ADR-012, ADR-021`.
- [E3-T4](E3-database-geocoding-media/tasks/E3-T4-implement-media-storage-and-derivatives.md): `done` revision 2 through PR #60; task dependencies `E2-T3, E3-T1, E3-T2`; deliberately independent of E3-T3; M2; requirements `P-005, P-007`; decisions `ADR-005, ADR-007, ADR-012`.
- [E3-T5](E3-database-geocoding-media/tasks/E3-T5-import-and-review-the-complete-dataset.md): promoted/`done` revision 3 through PRs #65/#66 with owner-directed completion recorded 2026-08-17; terminal local reconciliation (27,170 unchanged, zero pending work) and the materialized snapshot feed E7-T6; task dependencies `E2-T5, E3-T2, E3-T3, E3-T4`; durable quota-aware multi-day Geoapify batches and review; M2; requirements `P-001, P-002, P-005, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007, ADR-021`.
### E4

- [E4-T1](E4-read-api-filter-contracts/tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md): promoted/done revision 2; satisfied dependency `E3-T1`; M1; requirements `P-001, P-003`; decisions `ADR-002, ADR-003, ADR-005, ADR-012, ADR-013`.
- [E4-T2](E4-read-api-filter-contracts/tasks/E4-T2-implement-facets-and-location-offer-collection.md): promoted/done revision 2; satisfied dependency `E4-T1`; M1; requirements `P-001, P-002, P-003`; decisions `ADR-002, ADR-003, ADR-012, ADR-013`.
- [E4-T3](E4-read-api-filter-contracts/tasks/E4-T3-implement-offer-detail.md): promoted/`done` revision 1 through PR #78; task dependencies `E3-T4, E4-T2` satisfied; M2; requirements `P-002, P-005, P-006, P-007, P-008`; decisions `ADR-003, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016`.
- [E4-T4](E4-read-api-filter-contracts/tasks/E4-T4-harden-api-behavior-and-performance.md): promoted/`done` through PR #83; task dependencies `E4-T1, E4-T2, E4-T3, E3-T5` satisfied; M2; requirements `P-001, P-002, P-003`; decisions `ADR-012, ADR-013`.
### E5

- [E5-T1](E5-interactive-map-frontend/tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md): promoted/done revision 2; satisfied dependencies `E1-T2, E4-T2`; M1; requirements `P-001, P-004, P-007`; decisions `ADR-002, ADR-004, ADR-012`.
- [E5-T2](E5-interactive-map-frontend/tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md): promoted/done revision 2 through [PR #43](https://github.com/Flippylolz/WEF/pull/43) with deployed-regression fix [PR #47](https://github.com/Flippylolz/WEF/pull/47); satisfied dependencies `E5-T1, E4-T2`; M1; requirements `P-001, P-003, P-004`; decisions `ADR-002, ADR-003, ADR-012`.
- [E5-T3](E5-interactive-map-frontend/tasks/E5-T3-build-offer-detail-and-media-gallery.md): promoted/`done` revision 2 through PR #80; dependencies `E4-T3, E5-T1` satisfied; M3; requirements `P-002, P-005, P-006, P-007`; decisions `ADR-003, ADR-004, ADR-007, ADR-012`.
- [E5-T4](E5-interactive-map-frontend/tasks/E5-T4-complete-responsive-list-map-accessibility.md): promoted/`done` revision 2 through PR #82; dependencies `E5-T2, E5-T3` satisfied; M3; requirements `P-001, P-002, P-003, P-004, P-005`; decisions `ADR-002, ADR-004, ADR-012`.
- [E5-T5](E5-interactive-map-frontend/tasks/E5-T5-performance-and-production-ux-pass.md): promoted/`done` revision 2 through PR #85; dependencies `E5-T4, E4-T4` satisfied; M3; requirements `P-001, P-004, P-005`; decisions `ADR-004, ADR-007, ADR-012`.
### E6

- [E6-T1](E6-quality-security-operations/tasks/E6-T1-complete-automated-test-pyramid.md): promoted/done under plan revision 8; task dependencies `E4-T3, E5-T3`; M3; requirements `P-001, P-002, P-003, P-004, P-005, P-006, P-007, P-008`; decisions `ADR-012, ADR-013, ADR-016`.
- [E6-T2](E6-quality-security-operations/tasks/E6-T2-perform-privacy-and-security-hardening.md): `done` through PRs #130/#131; task dependencies `E3-T4, E4-T3, E5-T3`; M3; requirements `P-002, P-005, P-006, P-007, P-008`; decisions `ADR-007, ADR-011, ADR-013, ADR-016`.
- [E6-T3](E6-quality-security-operations/tasks/E6-T3-add-operational-diagnostics.md): promoted/done under plan revision 7; task dependencies `E3-T2, E4-T4`; M3; requirements `P-007`; decisions `ADR-008, ADR-010, ADR-014, ADR-015`.
- [E6-T4](E6-quality-security-operations/tasks/E6-T4-implement-in-house-registration-and-sessions.md): promoted/done revision 1 through [PR #51](https://github.com/Flippylolz/WEF/pull/51); satisfied dependencies `E1-T2, E3-T1` and approved revision 2 spike/plan gates; M3; requirements `P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T5](E6-quality-security-operations/tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md): promoted/`done` revision 1 through [PR #110](https://github.com/Flippylolz/WEF/pull/110); satisfied dependencies `E2-T2, E3-T1, E4-T3, E6-T4` and approved plan revision 3; M3; requirements `P-002, P-007, P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T6](E6-quality-security-operations/tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md): `done` revision 1; merged via PR #113; satisfied dependencies `E5-T3, E6-T4, E6-T5` and approved plan revision 4; M3; requirements `P-002, P-008`; decisions `ADR-011, ADR-012, ADR-016`.
- [E6-T7](E6-quality-security-operations/tasks/E6-T7-implement-owner-administration-console.md): promoted/`done` revision 1 through PR #116 with completion record #117; satisfied dependencies `E6-T4, E6-T5` and approved plan revision 5; M3; requirements `P-008`; decisions `ADR-011, ADR-012, ADR-016`.
### E7

- [E7-T1](E7-production-delivery/tasks/E7-T1-build-production-compose-topology.md): `done`, satisfied dependencies `E1-T3, E5-T1`; M3; requirements `none`; decisions `ADR-005, ADR-008, ADR-010, ADR-014, ADR-015, ADR-019`.
- [E7-T2](E7-production-delivery/tasks/E7-T2-provision-and-verify-supplied-server.md): `done`, satisfied dependency `E7-T1`; resolved deferred gate D-001; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-015, ADR-019`.
- [E7-T3](E7-production-delivery/tasks/E7-T3-implement-github-image-and-deployment-workflows.md): `done`, satisfied dependencies `E1-T4, E7-T1, E7-T2`; M3; requirements `none`; decisions `ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-019`.
- [E7-T4](E7-production-delivery/tasks/E7-T4-implement-health-verification-and-rollback.md): `done`, satisfied dependency `E7-T3`; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-015, ADR-019`.
- [E7-T5](E7-production-delivery/proposed-tasks/E7-T5-future-backup-and-restore-capability.md): task dependencies `none`; M3; requirements `none`; decisions `ADR-015`.
- [E7-T6](E7-production-delivery/tasks/E7-T6-transfer-and-import-the-historical-dataset.md): `done` through PRs #88–#104; verified non-public candidate on NUC; task dependencies `E3-T5, E7-T2, E7-T4`; M3; requirements `P-001, P-002, P-005, P-007`; decisions `ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-014, ADR-015, ADR-019`.
- [E7-T7](E7-production-delivery/tasks/E7-T7-enable-production-registration-and-contact-reveal.md): `done` under plan revision 8 after E7-T10 HTTPS; M3; requirements `P-008`; decisions `ADR-010, ADR-011, ADR-014, ADR-016, ADR-019, ADR-020`; PRs #123/#124/#125.
- [E7-T8](E7-production-delivery/tasks/E7-T8-build-shared-nginx-tls-ingress.md): `done` through [PR #69](https://github.com/Flippylolz/WEF/pull/69) — the 2026-08-15 invalidation was an accidental touch by another agent's E7-T6 priority work and the owner restored the gates on 2026-08-16; satisfied dependency `E7-T4`; inert topology proven with fixtures only (`.test` hostnames, local Pebble ACME); M3; requirements `none`; decisions `ADR-010, ADR-014, ADR-019, ADR-020`.
- [E7-T9](E7-production-delivery/tasks/E7-T9-implement-reversible-shared-edge-cutover.md): `done` through PRs #106/#107; inert cutover automation with fixture proofs; live NUC execution is E7-T10 behind D-009; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-019, ADR-020`.
- [E7-T10](E7-production-delivery/tasks/E7-T10-roll-out-and-verify-shared-tls.md): `done` through PR #121 and live WEF HTTPS on `2fa54e2405.duckdns.org`; Forecast remains on `:3000`; M3; requirements `none`; decisions `ADR-008, ADR-010, ADR-014, ADR-019, ADR-020`.
- [E7-T11](E7-production-delivery/tasks/E7-T11-activate-the-verified-historical-candidate.md): `done` through PRs #127/#128 + live activation 2026-08-20; ADR-019 public-activation boundary; task dependencies `E7-T6, E7-T7, E7-T10`; M3; requirements `P-001, P-002, P-005, P-007`; decisions `ADR-008, ADR-010, ADR-014, ADR-015, ADR-019, ADR-020`.
### E8

- [E8-T1](E8-telegram-live-ingestion/tasks/E8-T1-confirm-channel-identity-and-access.md): promoted/`in_progress` revision 1; task dependencies `none`; deferred gate D-003 (public identity and deploy credentials/session provisioned; real live acceptance open); milestone prerequisite M3; M4; requirements `P-006`; decisions `ADR-006`.
- [E8-T2](E8-telegram-live-ingestion/tasks/E8-T2-implement-secure-telethon-session-and-backfill.md): promoted/`in_progress`; restartable Telethon backfill delivered through PR #167, with live acceptance/media download still open; task dependencies `E8-T1, E3-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-005, ADR-006, ADR-007`.
- [E8-T3](E8-telegram-live-ingestion/tasks/E8-T3-implement-live-new-edit-delete-processing.md): promoted/`in_progress`; serialized new/edit/delete processing delivered through PR #168, with real subscription evidence still open; task dependencies `E8-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007`.
- [E8-T4](E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): promoted/`done` revision 1 through PR #162; task dependencies `E3-T3`; D-002 resolved (retain Geoapify); M4; requirements `P-001, P-007`; decisions `ADR-005, ADR-006, ADR-021`.
- [E8-T5](E8-telegram-live-ingestion/tasks/E8-T5-production-reconciliation-and-worker-alerting.md): promoted/`in_progress` revision 1; worker ops shipped through PR #169 and production service start through PR #173/release `3ee56a5`; verified live event/gap/outage evidence remains B-003; task dependencies `E8-T3, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-006, ADR-010, ADR-015`.

### E13

- [E13-T1](E13-dark-map-explorer/tasks/E13-T1-dark-shell-compact-filters.md): promoted/`done` revision 1; task dependencies `none`; M4; requirements `P-004`; decisions `ADR-002, ADR-003, ADR-004, ADR-012, ADR-013`.
- [E13-T2](E13-dark-map-explorer/tasks/E13-T2-viewport-listing-summary-projection.md): promoted/`done` revision 1; task dependencies `none`; M4; requirements `P-001, P-003`; decisions `ADR-002, ADR-003, ADR-012, ADR-013`.
- [E13-T3](E13-dark-map-explorer/tasks/E13-T3-selectable-listing-rail.md): promoted/`done` revision 1; satisfied dependencies `E13-T1, E13-T2`; M4; requirements `P-004`; decisions `ADR-002, ADR-003, ADR-004, ADR-012`.

### E14

- [E14-T1](E14-production-hardening-and-scalability/proposed-tasks/E14-T1-make-quality-and-governance-gates-truthful.md): proposed/non-actionable; task dependencies `none`; M5; requirements `none`; decisions `ADR-009, ADR-012, ADR-013, ADR-017`.
- [E14-T2](E14-production-hardening-and-scalability/proposed-tasks/E14-T2-strengthen-critical-path-test-confidence.md): proposed/non-actionable; task dependency `E14-T1`; M5; requirements `P-001` through `P-008`; risk-weighted confidence and failure probes.
- [E14-T3](E14-production-hardening-and-scalability/proposed-tasks/E14-T3-refactor-frontend-orchestration-hotspots.md): proposed/non-actionable; task dependencies `E13-T3, E14-T2`; M5; requirements `P-001, P-002, P-003, P-004, P-005, P-008`.
- [E14-T4](E14-production-hardening-and-scalability/proposed-tasks/E14-T4-refactor-backend-ingestion-and-operator-seams.md): proposed/non-actionable; task dependency `E14-T2`; M5; requirements `P-001, P-002, P-005, P-006, P-007, P-008`.
- [E14-T5](E14-production-hardening-and-scalability/proposed-tasks/E14-T5-add-full-stack-cross-browser-and-accessibility-journeys.md): proposed/non-actionable; task dependencies `E14-T3, E14-T4`; M5; requirements `P-001` through `P-008`.
- [E14-T6](E14-production-hardening-and-scalability/proposed-tasks/E14-T6-define-slos-and-ship-privacy-safe-observability.md): proposed/non-actionable; task dependencies `E8-T5, E14-T1`; M5; requirements `P-001, P-006, P-007, P-008`.
- [E14-T7](E14-production-hardening-and-scalability/proposed-tasks/E14-T7-prove-capacity-and-enforce-performance-budgets.md): proposed/non-actionable; task dependencies `E14-T3, E14-T4, E14-T6`; M5; requirements `P-001, P-002, P-003, P-004, P-005, P-006, P-007`.
- [E14-T8](E14-production-hardening-and-scalability/proposed-tasks/E14-T8-harden-supply-chain-and-release-integrity.md): proposed/non-actionable; task dependency `E14-T1`; M5; requirements `P-007, P-008`.
- [E14-T9](E14-production-hardening-and-scalability/proposed-tasks/E14-T9-rehearse-operational-resilience-and-disaster-recovery.md): proposed/non-actionable and blocked while E7-T5/ADR-015 remain deferred; task dependencies `E7-T5, E14-T6, E14-T7, E14-T8`; M5; requirements `P-006, P-007, P-008`.

### E15

- [E15-T1](E15-telegram-ingestion-reliability/tasks/E15-T1-supervise-and-observe-event-pipeline.md): P0 promoted/`done` through green-CI PR #189; task dependencies `none`; M4; requirements `P-006, P-007`; decisions `ADR-006, ADR-008, ADR-010`; fail-fast worker task supervision and privacy-safe listener diagnostics.
- [E15-T2](E15-telegram-ingestion-reliability/tasks/E15-T2-add-checkpoint-driven-reconciliation.md): P0 promoted/`done` through green-CI PR #190; satisfied task dependency `E15-T1`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007, ADR-010`; startup/reconnect/periodic checkpoint polling makes passive events a latency optimization rather than the completeness boundary.
- [E15-T3](E15-telegram-ingestion-reliability/tasks/E15-T3-recover-gap-and-prove-outage-recovery.md): P0 promoted/`done` through green-CI PR #191; satisfied task dependencies `E15-T1, E15-T2`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-015`; bounded production recovery and outage/alert evidence narrowed B-003 to residual E8 acceptance.

### E16

- [E16-T1](E16-cluster-expansion-reliability/tasks/E16-T1-prevent-cluster-expansion-freeze.md): P0 promoted/`ready`; task dependencies `none`; M4; requirement `P-004`; decisions `ADR-002, ADR-004`; spike and implementation plan revision 1 approved; guarded non-interpolated numbered-cluster expansion and real-browser regression verification.

Bootstrap and production gates are preserved: E0-T1 depends on E1-T1 so its dedicated branch can exist; E0-T2 depends on E0-T1 and E1-T1; E1-T2 depends on E0-T2; E7-T1 depends on E1-T3/E5-T1 for the anonymous rehearsal, E7-T2 retains resolved D-001 plus E7-T1, and E7-T3 retains E1-T4/E7-T1/E7-T2. Promoted E7-T6 revision 3 retains E3-T5/E7-T2/E7-T4 and no longer depends on D-002 because it transfers materialized results without provider calls; it stages a non-public candidate and leaves activation to proposed E7-T11 behind the ADR-019 gates. Shared TLS proceeds E7-T4 → E7-T8 → E7-T9 → E7-T10, with D-009 gating only E7-T10; E7-T7 retains E6-T4/E6-T5/E6-T6/E6-T7/E7-T4/E7-T10. E8-T5 depends only on E8-T3 and E8-T4—it does not depend on deferred E7-T5.

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
- Shared Nginx/Certbot TLS for WEF while preserving AI Forecast on `:3000`: E7-T8 through E7-T10.
- Anonymous browsing plus username/password registration, owner administration, and audited contact reveal: E6-T4 through E6-T7, E7-T10, E7-T7.
- English-first i18n-keyed interface: E6-T6.
- Verified Telegram links: E4-T3, E5-T3, then E8-T1 for live data.
- Import traceability and failure accounting: E2-T4, E3-T2, E3-T5.
- Geocoding accuracy/review: E3-T3, E3-T5.
- Procedural feature branches/hotfix ownership plus required CI workflows: E1-T4 and [repository and change rules](../governance/REPOSITORY_RULES.md); enforced `main` protection is out of scope.
- Dependabot update pull requests: E1-T6.
- Scheduled owner-label/check/bot-commit-gated Dependabot merge workaround: E1-T7.
- Persistent PostgreSQL/media/checkpoint data outside Git: E3-T1, E3-T2, E3-T4, E7-T1; backups are deferred in E7-T5.
- Dockerized GitHub deployment: E7-T1 through E7-T4.
- Resumable verified materialized-snapshot transfer into a non-public production candidate: E7-T6; HTTPS/sensitive-feature-gated public activation: E7-T11.
- Monitoring, contact-data minimization, and accessibility: E5-T4, E6-T2, E6-T3, E6-T5; backups are deferred in E7-T5 and a formal privacy notice is out of scope.
- Live channel ingestion implementation: E8-T1 through E8-T5; blocker-priority source-completeness recovery and operational acceptance: E15-T1 through E15-T3.
- Post-launch maintainability, test confidence, SLOs, capacity, release integrity, and disaster-recovery evidence: E14-T1 through E14-T9, with existing E7-T5 as E14-T9's non-duplicated recovery prerequisite.
