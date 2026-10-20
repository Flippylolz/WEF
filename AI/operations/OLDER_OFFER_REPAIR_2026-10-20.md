# 20 October 2026 older-offer address repair

The owner requested checking other offers for the same problem after the
[recent-listing incident](INCIDENT_2026-10-20.md). This unplanned follow-up stays
within deterministic source extraction and the existing bounded offer-recovery
operator. It adds no dependency, schema, provider, location acceptance exception
or automatic historical replay activation.

## Initial audit and recovery

Read-only pages of 500 covered 30,332 non-deleted current source revisions through
the observed channel head `31793`. Parser `e2-v19` found 3,573 candidates, all with
primary canonical offers, and 26,759 non-candidates. There were no missing
canonical candidates. After the 19 recent repairs, six older source-backed
unknown locations remained recoverable: `19245`, `31501`, `31511`, `31521`,
`31530`, `31540`. Those six were dry-run, applied through the existing operator
and replayed idempotently.

The first 25 recoveries preserved offer IDs, price/business fields, source rows,
source revision counts and all photo associations. Hash comparisons also found
unrelated offers unchanged. All four posts from 19–20 October became public;
facets advanced from 15 October to `2026-10-20T09:22:21Z`. Two 16 October
locations remain subject to genuine geocoder ambiguity/address-mismatch review;
neither was force-accepted. Equivalent avenue spellings were checked against the
municipal resolver without canonical writes and yielded no verified match.

## Additional confirmed parser gaps

The remaining unknown-location population was not treated as proven source
absence. Public address sections and server-side shape/count diagnostics exposed:

- Ukrainian location/address labels that the Russian label rule missed.
- A standalone pin followed by an address line.
- A structured unit title containing pipe-delimited address evidence.
- A second pin marking nearby-amenity prose, incorrectly conflicting with the
  actual property address on the first pin.

Parser `e2-v20` recognizes those forms. Pin candidates must begin with supported
street/city/locality or exact district evidence; amenity prose cannot override an
address merely because it mentions another street. Explicit property pins take
precedence over title summaries. Distinct property addresses/districts still
conflict. Blank, delimiter-only and emoji-only template values are skipped before
source-span construction. Source spans and distinct pin/summary rule provenance
are retained. No fuzzy street, neighborhood or city substitution is introduced.

The final read-only `e2-v20` canary reconciled the same 30,332 current source
revisions and 3,573 linked candidates, with zero missing canonical candidates or
parser exceptions. It found 31 additional source-supported unknown locations
eligible for bounded address recovery; 12 unknown locations remain unsupported by
these deterministic formats. These are address-extraction populations, not a
claim that every recovered address will pass geocoding or that unsupported posts
contain no address information.

Invented regression fixtures cover supported forms, section boundaries, true
conflicts and descriptive pins. PostGIS recovery cases verify dry-run/apply/repeat
for labeled, standalone-pin, Ukrainian and summary forms, preserving source and
offer identities and publication gates. The separately accepted automatic
historical replay remains at `e2-v18/source-evidence-v3`; its production guard
does not accept this new parser.

Local validation passed `make lint`, `make format-check`, `make typecheck`,
`make contract-check`, the full test/coverage gate and the Markdown link check.
The full backend/PostGIS suite passed 2,304 tests at 100% line/branch coverage;
the frontend retains its independent 100% per-file coverage requirement. Pinned
container runtimes provide Python, Node and pnpm for local validation.

## Rollout and evidence boundaries

Run the candidate parser against retained current revisions read-only, exporting
only counts, IDs and decision categories. After green CI and the ordinary release,
freeze the additional source IDs, snapshot privacy-safe hashes, dry-run each exact
source, apply a one-offer canary, then apply the reviewed remainder and repeat it.
Normal geocoding/publication must accept an address before a new map pin appears.

Repeat the source audit and reconcile canonical, photo and public-map projections.
Unrecognized neighborhoods, unsupported address forms and conflicting provider
results require the established location-review workflow. Their presence is not
permission to invent a coordinate or publish through a weaker policy. No raw
source payload, contact, session or provider credential belongs in the receipts
or repository. Rollback uses the preceding compatible application image and
retains source history and recovered canonical identities.
