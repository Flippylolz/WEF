# Map rendering readiness correction

Release run 34033274878 for documentation PR #367 failed the Chromium cluster
expansion journey before deployment. Production remained on the healthy
`94a8932e00582e894a8ea9f52e2b0e86b5e4ceee` release and automatic location
revalidation continued independently.

The journey waited for MapLibre's load callback and initial camera URL update,
then clicked the canvas center once. Those events do not guarantee that the
GeoJSON worker has finished rendering interactive cluster features. The
privacy-scanned trace showed that center click without the expected expansion;
the failure image subsequently showed the cluster at that position. This is
consistent with a rendering race, rather than evidence that any production
coordinate has been corrected.

The map now exposes `aria-busy` while initially loading, processing data events,
or moving. Only MapLibre's idle event marks rendering settled. The cluster and
street-selection journeys wait for that state before their single canvas click.
The existing finite-viewport, zoom expansion, precision, and selection assertions
remain intact. No arbitrary delay, critical route mock, assertion relaxation,
new browser skip, or whole-test retry is added.

A component regression checks that load alone remains busy and that later data
and movement each require a fresh idle event. This is a standalone delivery
correction within the approved E26 work, with no dependency or schema change.

Validation: `UV_PYTHON=3.13.2 make verify` passed (1,287 backend tests,
186 frontend tests, 186 script tests, formatting, lint, types, contracts,
architecture, build and runtime proofs). `make test-e2e` passed all five profiles:
48 passed, 12 existing WebGL skips, zero retries. After moving the cluster's
baseline viewport capture behind the readiness wait, the final Chromium profile
passed all 12 journeys again. Required current-head CI and the ordinary release
gates remain mandatory.
