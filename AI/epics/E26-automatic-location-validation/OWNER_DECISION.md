# E26 owner direction and approval boundary

Recorded 2026-09-06 in Codex task `01a0710e-cb6a-73c0-b27b-2214b4cc3b6f`.

The owner selected “E26 — Map accuracy: prevent wrong-street and misleading coarse pins, then automatically revalidate existing locations.” After clarifying that implementation had not started and that Ostrzycka and Jugosłowiańska were not verified fixed, the owner directed: “let's start”.

Codex interprets that direction as approval to advance the existing spike revision 1 recommendation into task refinement and implementation planning. This records the interpretation and exact instruction; it does not claim the owner explicitly named a revision. Implementation plan revision 1 was prepared afterward and remains awaiting approval under the repository workflow. No application code, tests, migrations, provider calls or production data changes were made in this planning change.

The updated repository instructions supply standing merge authorization after current-head CI, review and dependency requirements pass. They do not replace the separate implementation-plan gate.

Ostrzycka, the owner-reported Jugosłowiańska case and the additional Jugosłowiańska/Grochowska town-hall mismatch remain open acceptance cases. A sanitized regression passing later proves only the tested behavior; production correction requires separately recorded persisted and public-display evidence.

## Implementation approval

At 2026-09-06T05:33:04Z, the owner replied “i approve” directly to “Do you approve this plan for implementation?” after E26 implementation plan revision 1 was presented. Record revision 1 as approved and proceed within its task boundaries and dependency gates. E14-T5 remains a T3 dependency, and existing-location production application remains gated on the specified observation/canary/discovery conditions.

## Municipal-first follow-up authorization

Owner: prepare and merge a pr; after deployment run a verification run, maybe we’ll need a backfill; summary here. Authorizes the municipal → geocoding → bounded AI-address-recovery proposal in this conversation.

Recorded 2026-09-06T15:24:20.540396+00:00. The request authorizes implementation and normal release of the described routing policy, not increased paid quotas, invented AI coordinates, or overwriting protected corrections. Revision 2 records this direction; no additional per-PR permission is required.
