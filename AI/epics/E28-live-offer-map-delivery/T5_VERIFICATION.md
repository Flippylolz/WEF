# E28-T5 verification

The bounded operator includes previously unlinked current source revisions,
provides dry-run counts, requires a frozen upper bound, and preserves the live
cursor. Each application locks and checks the current revision and uses existing
parser/persistence, encrypted contacts and protected field-origin paths. Replaying
a page is idempotent; existing known location identities and visibility survive.
No new provider or dependency is introduced.

The delivery stage reports recent text-photo/linked posts through offer, map and
gallery outcomes. It excludes media-only children, deleted sources and intentional
hiding. Explicit current media/location deferrals count as waiting. New successful
deliveries cannot hide an older offer exceeding the five-minute deadline.

Focused database checks passed (14 tests). Full pre-stack suite passed 1,386
backend and 186 frontend tests with coverage. Invalid operator bounds are tested
before any database access. Real persistence proves a missed offer is created,
unchanged raw revisions and IDs survive replay, manual hiding remains, and live
checkpoints stay untouched. Final combined stack validation and production
backfill receipts will be appended; neither backfill nor the 24-hour window is
claimed complete here.
