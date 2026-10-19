# October 2026 shared-edge Compose image update

This is unplanned owner-requested maintenance to complete Dependabot PR #415.
The update selects the official Nginx 1.31.7 Alpine mainline image and Python
3.14 Alpine image for the disposable shared-edge HTTP fixtures. Both published
multi-platform manifest digests were verified against Docker Hub on 2026-10-19.
Application Python remains 3.13.16; the Python image change serves test fixtures.

Dependabot updated the four Compose manifests but left the deployment release
helper, certificate-renewal helper, and topology proof on the preceding image
pins. The existing safety check correctly rejected that inconsistency. Those
three references now match the immutable Compose pins. All consistency checks,
TLS verification, renewal and rollback assertions remain in place.

Validation covers frozen installation, formatting, lint, types, contracts,
repository quality gates, full backend/frontend suites, Compose rendering, and
production proofs including shared-edge TLS issuance, renewal, routing, and
rollback using the updated images. Required current-head CI remains the merge
gate. No application contract, database migration, deployment topology, or
configuration-ownership change is introduced. Roll back by reverting the PR's
squash commit and redeploying the previous pinned images.
