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
- [E8 — Future Telegram live ingestion](E8-telegram-live-ingestion/README.md) — `in_progress`; spike revision 2 and plan revision 5 approved; E8-T1/T2/T4 done, E8-T3/T5 in operational acceptance; B-003 retains passive edit/delete evidence; milestone M4.
- [E9 — Account registration modal](E9-account-registration-modal/README.md) — `done`; E9-T1 done; milestone M3.
- [E10 — Property favorites](E10-property-favorites/README.md) — `done`; E10-T1 done; milestone M3.
- [E11 — Scalable quick filters](E11-scalable-quick-filters/README.md) — `done`; E11-T1 done; milestone M3.
- [E12 — Database index audit](E12-database-index-audit/README.md) — `done`; E12-T1 done; milestone M3.
- [E13 — Dark map-first listing explorer](E13-dark-map-explorer/README.md) — `done`; spike/plan revision 1 approved (AD-038); E13-T1–T3 done through PRs #176/#179/#180; milestones M4.
- [E14 — Production hardening and scalability](E14-production-hardening-and-scalability/README.md) — `planning`; spike revision 1 approved under AD-041; implementation plan revision 1 awaits owner approval; E14-T1–T8 promoted/`draft`, E14-T9 proposed/blocked; milestone M5.
- [E15 — Telegram ingestion reliability recovery](E15-telegram-ingestion-reliability/README.md) — `done`; spike/plan revision 1 approved under AD-039/AD-040; E15-T1–T3 completed through green-CI PRs #189/#190/#191 with production recovery evidence; milestone M4 remains open only for residual E8 acceptance.
- [E16 — Reliable numbered map-cluster expansion](E16-cluster-expansion-reliability/README.md) — `done`; spike/plan revision 1 approved 2026-08-29; E16-T1 done through green-CI PR #194 with production version `b09314d`; milestone M4.
- [E17 — Raw archive replay and filter integrity](E17-raw-archive-replay-and-filter-integrity/README.md) — `done`; spike/plan revision 1 approved 2026-08-29; E17-T1–T6 done through green-CI PRs #203/#208/#200/#201/#209/#211 with owner backup replay and production promotion (release `7a3e927`, deploy run 33280067325); milestone M5.
- [E18 — Owner location management and verification](E18-owner-location-verification/README.md) — `done`; spike/plan revision 1 approved 2026-08-30; E18-T1/T2 done through green-CI PRs #217/#218 with verified deploys; milestone M5.
- [E19 — AI-assisted owner catalog curation](E19-ai-assisted-place-curation/README.md) — `done`; spike revision 4 approved under AD-042 and plan revision 1 approved under AD-043; E19-T1–T4 done through PRs #226–#230; milestone M5.
- [E20 — Admin console visual refresh](E20-admin-console-visual-refresh/README.md) — `done`; spike/plan revision 1 approved under AD-044/AD-045 on 2026-08-31; E20-T1/T2 done through green-CI PRs #247/#254 with production deploy verification (run 33429448184); milestone M5.
- [E21 — Ingestion AI fallback on parse miss](E21-ingestion-ai-fallback/README.md) — `done`; E21-T1–T3 and Groq apply hardening done through PRs #259/#263/#267/#268–#271 with production recovery on `wef_hist_candidate` (2026-09-01); operator runbook in [UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md](../ingestion/UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md); milestone M5.
- [E22 — Property type classification and filter](E22-property-type-filter/README.md) — `done`; E22-T1–T3 done through green-CI PR #302 with follow-up #304 (backfill dedupe) and production backfill on `wef_hist_candidate` (deploy run 33659894308); milestone M5.
- [E23 — Location display name normalization](E23-location-display-name-normalization/README.md) — `done`; E23-T1/T2 shipped through PRs #316/#317; production backfill applied 2026-09-02 (`adcdb10`); milestone M5.
- [E24 — Automatic ingestion recovery](E24-automatic-ingestion-recovery/README.md) — `ready`; spike revision 2 and implementation plan revision 1 approved under AD-048/AD-049 for T1/T2 revision 2 in that order; T3/T4 remain proposed; milestone M5.
- [E25 — Parser quality and automatic recovery](E25-parser-quality-and-automatic-recovery/README.md) — `in_progress`; spike and implementation plan revision 1 approved; T1 implemented/validated locally, publication approval pending; T2–T4 dependency-gated; milestone M5.
- [E26 — Automatic location validation and repair](E26-automatic-location-validation/README.md) — `selected`; audit-backed spike revision 1 awaiting owner approval; 3 proposed, non-actionable tasks; milestone M5.
- [E27 — Faster verified releases](E27-faster-verified-releases/README.md) — `ready`; spike and plan revision 1 approved 2026-09-05; T1 ready, T2/T3 awaiting dependencies; milestone M5.

The original E0–E7 MVP stack and M3 add-ons E9–E12 are complete on `main`. E8 live Telegram ingestion is on `main` with an authorized production worker, verified live media acquisition, and active passive-event monitoring. E15 completed the blocker-priority source-completeness, health, gap-repair, and outage-recovery work under AD-039/AD-040; E8/M4 retain only passive edit/delete callback evidence under B-003. E13's dark map-first redesign, E16's numbered-cluster expansion fix, E17's raw-archive replay and canonical filter integrity, and E18's owner location management are done. E19 delivered guarded Groq GPT-OSS 20B place review, missing-only batch offer autofill, AI provenance labels, and parser-gap reporting through PRs #226–#230. E20 delivered the owner `/admin` console alignment with the public dark design and repaired the overlapping filters, forms, and tables through PRs #247/#254 with a verified production deploy. E21 added owner-triggered ingestion AI parse generate/apply from `/admin/ingestion-issues`, parse-issue offer linking, and production recovery of four parse misses through PRs #259–#271 with completion docs in PR #272. E22 delivered backend-owned Apartment/House/Semi-detached classification, a URL-backed public filter, and production backfill through PRs #302/#304 with evidence in [E22 PRODUCTION_EVIDENCE.md](E22-property-type-filter/PRODUCTION_EVIDENCE.md). E14 spike revision 1 is approved and plan revision 1 awaits its separate owner decision; promoted tasks remain non-actionable until that gate clears. New work must pass its dedicated pull-request CI before merge.

## Global lifecycle

The [5 September 2026 system audit](../audits/2026-09-05-system-audit.md) adds E24–E27 for automatic ingestion recovery, parser improvement, map accuracy, and release latency. It maps test confidence and code maintainability to existing E14 tasks rather than duplicating them. E24 spike revision 2 and implementation plan revision 1 are approved; promoted T1/T2 proceed in that order under AD-048/AD-049. E24's remaining two tasks and E25–E26's seven tasks remain proposed. E27 spike and implementation plan revision 1 are approved; its three promoted tasks follow their dependency gates. Routine operation must minimize manual work, with escalation reserved for exceptional unresolved cases.

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

The synthetic map sequence deliberately excludes historical import, the complete export, network geocoding, media, auth/contacts, and Telegram credentials. E2-T1 separately begins the read-only historical source boundary and safe fixture corpus without replacing the persisted M1 seed. E1-T5 remains cancelled as historical traceability for the original private-repository constraint; ADR-023 records the later owner-directed protection of public-repository branch `main`.

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

- [E8-T1](E8-telegram-live-ingestion/tasks/E8-T1-confirm-channel-identity-and-access.md): promoted/`done` revision 1; task dependencies `none`; deferred gate D-003 (public identity and deploy credentials/session provisioned); milestone prerequisite M3; M4; requirements `P-006`; decisions `ADR-006`.
- [E8-T2](E8-telegram-live-ingestion/tasks/E8-T2-implement-secure-telethon-session-and-backfill.md): promoted/`done`; restartable Telethon backfill through PR #167 and live media acquisition through PR #243 deploy; task dependencies `E8-T1, E3-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-005, ADR-006, ADR-007`.
- [E8-T3](E8-telegram-live-ingestion/tasks/E8-T3-implement-live-new-edit-delete-processing.md): promoted/`in_progress`; serialized new/edit/delete processing through PR #168; passive edit/delete production evidence remains B-003 with NUC cron watch; task dependencies `E8-T2, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007`.
- [E8-T4](E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): promoted/`done` revision 1 through PR #162; task dependencies `E3-T3`; D-002 resolved (retain Geoapify); M4; requirements `P-001, P-007`; decisions `ADR-005, ADR-006, ADR-021`.
- [E8-T5](E8-telegram-live-ingestion/tasks/E8-T5-production-reconciliation-and-worker-alerting.md): promoted/`in_progress` revision 1; worker ops through PR #169/#173 and passive-event monitor through PR #250; passive edit/delete evidence remains B-003; task dependencies `E8-T3, E8-T4`; M4; requirements `P-006, P-007`; decisions `ADR-006, ADR-010, ADR-015`.

### E13

- [E13-T1](E13-dark-map-explorer/tasks/E13-T1-dark-shell-compact-filters.md): promoted/`done` revision 1; task dependencies `none`; M4; requirements `P-004`; decisions `ADR-002, ADR-003, ADR-004, ADR-012, ADR-013`.
- [E13-T2](E13-dark-map-explorer/tasks/E13-T2-viewport-listing-summary-projection.md): promoted/`done` revision 1; task dependencies `none`; M4; requirements `P-001, P-003`; decisions `ADR-002, ADR-003, ADR-012, ADR-013`.
- [E13-T3](E13-dark-map-explorer/tasks/E13-T3-selectable-listing-rail.md): promoted/`done` revision 1; satisfied dependencies `E13-T1, E13-T2`; M4; requirements `P-004`; decisions `ADR-002, ADR-003, ADR-004, ADR-012`.

### E14

- [E14-T1](E14-production-hardening-and-scalability/tasks/E14-T1-make-quality-and-governance-gates-truthful.md): promoted/`draft`; implementation gate pending; task dependencies `none`; M5; requirements `none`; decisions `ADR-009, ADR-012, ADR-013, ADR-017`.
- [E14-T2](E14-production-hardening-and-scalability/tasks/E14-T2-strengthen-critical-path-test-confidence.md): promoted/`draft`; implementation gate pending; task dependency `E14-T1`; M5; requirements `P-001` through `P-008`; risk-weighted confidence and failure probes.
- [E14-T3](E14-production-hardening-and-scalability/tasks/E14-T3-refactor-frontend-orchestration-hotspots.md): promoted/`draft`; implementation gate pending; task dependencies `E13-T3, E14-T2`; M5; requirements `P-001, P-002, P-003, P-004, P-005, P-008`.
- [E14-T4](E14-production-hardening-and-scalability/tasks/E14-T4-refactor-backend-ingestion-and-operator-seams.md): promoted/`draft`; implementation gate pending; task dependency `E14-T2`; M5; requirements `P-001, P-002, P-005, P-006, P-007, P-008`.
- [E14-T5](E14-production-hardening-and-scalability/tasks/E14-T5-add-full-stack-cross-browser-and-accessibility-journeys.md): promoted/`draft`; implementation gate pending; task dependencies `E14-T3, E14-T4`; M5; requirements `P-001` through `P-008`.
- [E14-T6](E14-production-hardening-and-scalability/tasks/E14-T6-define-slos-and-ship-privacy-safe-observability.md): promoted/`draft`; implementation gate pending and E8-T5 incomplete; task dependencies `E8-T5, E14-T1`; M5; requirements `P-001, P-006, P-007, P-008`.
- [E14-T7](E14-production-hardening-and-scalability/tasks/E14-T7-prove-capacity-and-enforce-performance-budgets.md): promoted/`draft`; implementation gate pending; task dependencies `E14-T3, E14-T4, E14-T6`; M5; requirements `P-001, P-002, P-003, P-004, P-005, P-006, P-007`.
- [E14-T8](E14-production-hardening-and-scalability/tasks/E14-T8-harden-supply-chain-and-release-integrity.md): promoted/`draft`; implementation gate pending; task dependency `E14-T1`; M5; requirements `P-007, P-008`.
- [E14-T9](E14-production-hardening-and-scalability/proposed-tasks/E14-T9-rehearse-operational-resilience-and-disaster-recovery.md): proposed/non-actionable and blocked while E7-T5/ADR-015 remain deferred; task dependencies `E7-T5, E14-T6, E14-T7, E14-T8`; M5; requirements `P-006, P-007, P-008`.

### E15

- [E15-T1](E15-telegram-ingestion-reliability/tasks/E15-T1-supervise-and-observe-event-pipeline.md): P0 promoted/`done` through green-CI PR #189; task dependencies `none`; M4; requirements `P-006, P-007`; decisions `ADR-006, ADR-008, ADR-010`; fail-fast worker task supervision and privacy-safe listener diagnostics.
- [E15-T2](E15-telegram-ingestion-reliability/tasks/E15-T2-add-checkpoint-driven-reconciliation.md): P0 promoted/`done` through green-CI PR #190; satisfied task dependency `E15-T1`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007, ADR-010`; startup/reconnect/periodic checkpoint polling makes passive events a latency optimization rather than the completeness boundary.
- [E15-T3](E15-telegram-ingestion-reliability/tasks/E15-T3-recover-gap-and-prove-outage-recovery.md): P0 promoted/`done` through green-CI PR #191; satisfied task dependencies `E15-T1, E15-T2`; M4; requirements `P-006, P-007`; decisions `ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-015`; bounded production recovery and outage/alert evidence narrowed B-003 to residual E8 acceptance.

### E16

- [E16-T1](E16-cluster-expansion-reliability/tasks/E16-T1-prevent-cluster-expansion-freeze.md): P0 promoted/`done` through green-CI PR #194 and production version `b09314d`; task dependencies `none`; M4; requirement `P-004`; decisions `ADR-002, ADR-004`; guarded non-interpolated numbered-cluster expansion with production real-browser regression verification.

### E17

- [E17-T1](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T1-raw-event-archive-and-background-processing.md): P1 promoted/`done` through green-CI PR #203; task dependencies `none`; M5; requirements `P-006, P-007`; decisions `ADR-006, ADR-012`; append-only raw-event archive with background draining.
- [E17-T2](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T2-parser-replay-reimport.md): P1 promoted/`done` through green-CI PR #208; satisfied dependency `E17-T1`; M5; requirements `P-006, P-007`; decisions `ADR-006, ADR-012`; operator replay over the raw archive.
- [E17-T3](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T3-currency-word-and-grouped-number-parser-hardening.md): P1 promoted/`done` through green-CI PR #200; task dependencies `none`; M5; requirements `P-002, P-007`; decisions `ADR-006`; currency-word and grouped-number price parsing.
- [E17-T4](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T4-canonical-filter-vocabulary-and-typo-rerouting.md): P1 promoted/`done` through green-CI PR #201; task dependencies `none`; M5; requirements `P-003`; decisions `ADR-012, ADR-013`; backend-owned canonical filter vocabulary with typo rerouting.
- [E17-T5](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T5-filter-determinism-and-test-coverage.md): P1 promoted/`done` through green-CI PR #209; satisfied dependency `E17-T4`; M5; requirements `P-001, P-003`; decisions `ADR-012, ADR-013`; filter determinism and contract coverage.
- [E17-T6](E17-raw-archive-replay-and-filter-integrity/tasks/E17-T6-owner-backup-replay-and-production-promotion.md): P1 promoted/`done` through green-CI PR #211; satisfied dependencies `E17-T1, E17-T2, E17-T3, E17-T4, E17-T5`; M5; requirements `P-001, P-002, P-006, P-007`; decisions `ADR-006, ADR-012, ADR-021`; owner backup replay, production promotion (release `7a3e927`, deploy run 33280067325), and epic completion gate.

### E19

- [E19-T1](E19-ai-assisted-place-curation/tasks/E19-T1-ai-place-review-backend.md): P0 `done` through https://github.com/Flippylolz/WEF/pull/226 (1120312); satisfied dependency `E18-T2`; approved spike revision 4 and plan revision 1; M5; requirement `P-009`; decisions `ADR-012, ADR-016, ADR-021, ADR-022`; Groq GPT-OSS adapter, minimized review persistence, contact-masked full-source reader, and guarded generate/apply backend.
- [E19-T2](E19-ai-assisted-place-curation/tasks/E19-T2-ai-place-review-console.md): P0 `done` through https://github.com/Flippylolz/WEF/pull/227 (d8673dc); task dependency `E19-T1`; M5; requirement `P-009`; decisions `ADR-012, ADR-016, ADR-022`; owner-only Review with AI diff/apply console and production controls.
- [E19-T3](E19-ai-assisted-place-curation/tasks/E19-T3-batch-offer-enrichment-provenance.md): P0 `done` through https://github.com/Flippylolz/WEF/pull/228 (45094ba); task dependency `E19-T1`; M5; requirement `P-009`; decisions `ADR-012, ADR-016, ADR-022`; checkpointed missing-only batch offer autofill, rollback, AI field origins, and parser-replay feedback.
- [E19-T4](E19-ai-assisted-place-curation/tasks/E19-T4-ai-enrichment-controls-and-reporting.md): P0 `done` through https://github.com/Flippylolz/WEF/pull/230 (d7afef6); task dependencies `E19-T2, E19-T3`; M5; requirement `P-009`; decisions `ADR-012, ADR-016, ADR-022`; owner batch controls, public/admin AI-assisted labels, parser-gap reports, and contract/UI tests.

### E20

- [E20-T1](E20-admin-console-visual-refresh/tasks/E20-T1-admin-dark-theme-alignment.md): P1 promoted/`done` through green-CI PR #247 (squash 1146d66); task dependencies `none`; M5; requirement `P-008`; decisions `ADR-012, ADR-016`; Tabler dark mode plus one shared admin stylesheet mapping the public Primer tokens, converting the Set-point, Review-with-AI, and enrichment pages.
- [E20-T2](E20-admin-console-visual-refresh/tasks/E20-T2-admin-filter-form-layout-fixes.md): P1 promoted/`done` through green-CI PR #254 (squash 1dce2e9); satisfied task dependency `E20-T1`; M5; requirement `P-008`; decisions `ADR-012, ADR-016`; per-view before/after screenshot catalogue and filter/form/table/action-cell layout repairs in the shared stylesheet.

### E21

- E21-T1–T3 and Groq apply hardening: `done` through PRs #259, #263 (`477d648`), #267, and #268–#271 (`89c940f`); completion docs PR #272; M5; requirement `P-009`; decisions `ADR-012, ADR-016, ADR-022`; parse-issue ledger, owner-triggered ingestion AI parse generate/apply (`parser_version=ai-parse-v1`), offer linking, and production recovery evidence — see [E21 README](E21-ingestion-ai-fallback/README.md).

### E22

- E22-T1–T3: `done` through green-CI PR #302 (`f78bfb9`), follow-up dedupe fix PR #304 (`b28c9bc`), and operator runbook PR #306; M5; requirements `P-001`–`P-004`, `P-007`, `P-010`; decisions `ADR-002, ADR-004, ADR-005, ADR-006, ADR-012, ADR-013`; parser `e2-v8`, migration `20260902_0019`, shared filter semantics, URL-backed UI, and production backfill evidence — see [E22 README](E22-property-type-filter/README.md) and [PRODUCTION_EVIDENCE.md](E22-property-type-filter/PRODUCTION_EVIDENCE.md).

### E23

- [E23-T1](E23-location-display-name-normalization/tasks/E23-T1-display-name-normalization.md): P1 `done`; PR #316; M5; Polish-forward display-name rules for new locations.
- [E23-T2](E23-location-display-name-normalization/tasks/E23-T2-display-name-backfill.md): P1 `done`; PR #317; M5; non-verified location rename backfill with production evidence.

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
- Anonymous browsing plus username/password registration, owner administration, and audited contact reveal: E6-T4 through E6-T7, E7-T10, E7-T7, E20-T1, E20-T2 (owner console visual alignment and layout repairs).
- English-first i18n-keyed interface: E6-T6.
- Verified Telegram links: E4-T3, E5-T3, then E8-T1 for live data.
- Import traceability and failure accounting: E2-T4, E3-T2, E3-T5.
- Geocoding accuracy/review: E3-T3, E3-T5; owner location management, manual point placement, and verification: E18-T1, E18-T2.
- Owner-only AI-assisted place validation, missing-only batch offer autofill,
  transparent AI origin labels, and parser-gap provenance from contact-masked
  complete source descriptions: E19-T1 through E19-T4.
- Owner-triggered ingestion AI parse fallback on deterministic parse misses,
  with explicit apply and parse-issue offer linking: E21 (PRs #259–#272).
- Evidence-backed Apartment/House/Semi-detached classification and a consistent
  URL-backed public filter: E22 (PRs #302–#304, production evidence recorded).
- Protected feature-branch/hotfix ownership plus required CI workflows: E1-T4, ADR-023, and [repository and change rules](../governance/REPOSITORY_RULES.md).
- Dependabot update pull requests: E1-T6.
- Scheduled owner-label/check/bot-commit-gated Dependabot merge workaround: E1-T7.
- Persistent PostgreSQL/media/checkpoint data outside Git: E3-T1, E3-T2, E3-T4, E7-T1; backups are deferred in E7-T5.
- Dockerized GitHub deployment: E7-T1 through E7-T4.
- Resumable verified materialized-snapshot transfer into a non-public production candidate: E7-T6; HTTPS/sensitive-feature-gated public activation: E7-T11.
- Monitoring, contact-data minimization, and accessibility: E5-T4, E6-T2, E6-T3, E6-T5; backups are deferred in E7-T5 and a formal privacy notice is out of scope.
- Live channel ingestion implementation: E8-T1 through E8-T5; blocker-priority source-completeness recovery and operational acceptance: E15-T1 through E15-T3.
- Raw-event retention with parser replay/re-import, currency-word price correctness, backend-owned canonical filter facets, and owner-gated backup replay promotion: E17-T1 through E17-T6.
- Post-launch maintainability, test confidence, SLOs, capacity, release integrity, and disaster-recovery evidence: E14-T1 through E14-T9, with existing E7-T5 as E14-T9's non-duplicated recovery prerequisite.
