# E28-T2 street resolution evidence

Read-only municipal inspection on 8 September confirmed Szeligowska is one exact
ULICE record with two geometry components, not two competing street identities.
The old PostGIS selector required one merged LineString and returned no point.
The new selector clips verified geometry to the verified source district and
returns a deterministic midpoint on its longest nonzero component. It does not
average unrelated hosted points or weaken cross-record ambiguity checks.

The source parser also treated Sielce as a different city. The reviewed
Sielce→Mokotów neighborhood relation now preserves Warsaw and rejects an explicitly
conflicting district. Cache normalizer and municipal request versions change to
make stale results reevaluable under the existing guarded revalidation workflow.

Focused address/municipal/display tests: 83 passed. A real PostGIS regression
checks disconnected component ordering, coordinate derivation and district bounds.
Existing wrong-street, missing-address, protected-selection, source-fencing and
ambiguous-hosted-candidate tests remain binding. Full validation and production
canary evidence will be appended after completion; this task is not yet done.

Full local validation: `make lint`, `make format-check`, `make typecheck` and
`make contract-check` passed. `make test` passed 1,381 backend and 186 frontend
tests, including coverage gates. The isolated Compose frontend runner used two
Vitest workers to avoid host CPU contention. An initial test expected the old
municipal request version; its assertion now checks the intentionally bumped v2.
Production acceptance awaits the release and guarded revalidation. T1's release
passed verification but failed configuration validation before activation; the
concurrent shared-edge task is repairing loopback binding support.


## Production backfill follow-up

The current-template backfill exposed a further exact address mismatch: source
`al.` and provider `Aleje` avenue prefixes. T2 now normalizes only reviewed Polish
avenue spellings to one retained avenue token. It does not discard the avenue
identity or conflate it with an ordinary street; street names, house numbers,
city, country, confidence, ambiguity and owner fences remain authoritative.
Normalizer v6 invalidates stale address-mismatch observations for guarded replay.
Invented regression cases cover all three spellings and the conflicting components.
No raw offer text or provider exports are committed. Production acceptance requires
revalidation of the newly recovered apartment after this follow-up release.

The follow-up passed 49 focused address tests, full `make test` (1,417 backend
and 186 frontend tests with coverage), `make lint`, `make format-check`,
`make typecheck`, and `make contract-check`. Initial fresh PostgreSQL startup
raced test reset; the complete retry after initialization passed.
