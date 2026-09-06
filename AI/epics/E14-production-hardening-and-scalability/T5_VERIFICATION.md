# E14-T5 real-stack browser verification

## Topology and data boundary

`make test-e2e` installs the locked Playwright browsers and invokes
`scripts/run_full_stack_e2e.py`. Each invocation generates a distinct Compose project,
loopback port and ephemeral credentials. It builds the production web/API targets,
runs real migrations and a guarded one-time synthetic seed against tmpfs PostGIS,
and serves the normal API and public-media routes through Caddy. Database/API/web
remain on an internal network; only the edge has a loopback published port.
The runner removes only its generated project and volumes on every exit.

No live Telegram, geocoding provider, production database, or privileged fixture API
is used. The seed requires the exact test database identity and an empty account
table. It supplies existing M1 synthetic catalog fixtures, generated account secrets,
a reserved fictional contact encrypted by the actual contact persistence path,
and invented image pixels. The offline MapLibre style has no external sources;
real API points and district geometry still exercise the WebGL renderer. This
proves application map wiring, not external basemap quality or live geocode accuracy.

## Required matrix and journeys

Desktop Chromium, Firefox and WebKit plus Pixel 7 Chrome and iPhone 13 Safari
emulation run serially with zero retries. Chromium owns a required real WebGL pin
selection test; its four other project entries are explicitly skipped. Other
journeys use real routing, catalog filtering, URL sharing, detail/media, keyboard,
registration, persisted favorites, contact reveal, password changes, logout,
forced-password restrictions and CSRF checks. API failure recovery stops and starts
only the generated API container, avoiding a second run of the one-time seed.
The no-WebGL journey removes the browser WebGL capability while retaining real APIs.

Axe WCAG 2 A/AA and 2.1 AA violations fail the critical surfaces. Browser page errors
also fail. The existing unit/contract/coverage checks remain required alongside this
matrix; the browser job does not replace them.

## Failure evidence and privacy

Raw test logs stay in the ignored local run directory and are never uploaded.
Private account/contact journeys disable traces and videos. Screenshots exist only
on failure and mask inputs, revealed-contact lists and account details before capture.
Anonymous traces are also retained only on failure. The runner bounds artifact size
and inspects every uncompressed ZIP member for generated secrets, contact values and
session/private-field markers. It copies only scanned PNG/ZIP evidence and safe run
metadata into the upload directory. CI retains that directory for seven days only on
failure. Negative unit tests exercise compressed private payload rejection and
non-artifact exclusion. No raw source exports or media enter repository artifacts.

## Product defects found by the harness

- Version badge opacity reduced small-text contrast below 4.5:1; remove the opacity.
- Gallery Escape propagated to the parent offer drawer; contain gallery keyboard
  events, focus its close control, cycle Tab within controls and return to its opener.
- Missing WebGL2 left a partially initialized renderer whose cleanup crashed the
  explorer. Check capability before construction and release the probe context;
  preserve real listing access and retry without constructing the broken renderer.
- Catalog refresh could replace the offer opener while the gallery was open.
  Register the replacement button so closing detail restores focus to a connected
  control. The regression test verifies this reference lifecycle.

On macOS WebKit, keyboard traversal uses Option-Tab (and Option-Shift-Tab), following
[Apple's Safari keyboard navigation documentation](https://support.apple.com/guide/safari/keyboard-shortcuts-and-gestures-cpsh003/mac).
Linux CI and other browsers use Tab/Shift-Tab. No DOM focus shortcut substitutes
for the keyboard-only journey. Axe's temporary analysis page is closed and the
journey page brought back to the front before testing focus.

## Execution evidence

`make test-e2e` passed from commit `9fa8f46376d93364308c4ecd4ed02d807134fb77`:
36 journeys passed, four explicit non-Chromium WebGL skips, zero retries, zero
failure artifacts. Fresh migrations, seed, production image startup, release badge,
all five profiles and automatic volume cleanup succeeded. The earlier manual
synthetic project was removed separately after its full matrix also passed.

Focused frontend coverage passed all 176 tests with 95.76% lines and 90.06% branches.
Backend verification passed 1,232 tests at 91.00% coverage. Artifact privacy negative
tests passed. One containerized frontend attempt timed out waiting one second for a
mocked query while concurrent browser work ran; no timeout or retry policy was
relaxed. The complete `make verify` rerun without browser contention passed: 1,232 backend,
176 frontend and 186 script tests; format/lint/types, independent critical coverage,
contract drift/breaking probes, quality fault probes, runtime topology/rollback,
production builds, architecture violation probes and Markdown links all passed.
The shipped JavaScript is 566,530 gzip bytes across 17 chunks, below the unchanged
569,273-byte budget. Current-head CI and merge evidence remain required before
completion.
