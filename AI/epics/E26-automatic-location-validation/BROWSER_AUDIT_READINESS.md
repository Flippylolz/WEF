# Browser audit readiness correction

The release of PR #364 and worker PR #357 were blocked by the real browser
accessibility gate on 2026-09-06. Privacy-scanned traces showed only the
`document-title` violation: the server-rendered title existed before the audit,
then hydration replaced metadata during axe's asynchronous scan. A single
`toHaveTitle` assertion did not synchronize that replacement.

The shared audit now polls the complete WCAG A/AA scan for up to 15 seconds.
Every rule remains enabled, persistent violations fail, and whole-test retries
remain zero. This is a standalone delivery defect discovered during E26 rollout;
it does not extend E14 implementation scope or change production behavior.

Validation: `make verify` passed (1,244 backend tests, 185 frontend tests,
186 script tests, format/lint/types/contracts/runtime/build/architecture checks).
`make test-e2e` passed: 48 passed, 12 explicit WebGL skips, zero test retries.
Required CI remains a merge gate. The compatibility release must succeed before the additive worker schema
can deploy; no production application gate is waived.
