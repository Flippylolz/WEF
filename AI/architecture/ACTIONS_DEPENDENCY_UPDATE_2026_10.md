# October 2026 GitHub Actions dependency refresh

This is unplanned dependency maintenance requested by the repository owner.
Every committed external action reference was checked against its upstream stable
release and its tag dereferenced to a full commit SHA on 2026-10-19, including
nested composite actions.

The updated releases are setup-node 7.1.0, setup-uv 10.3.0, upload-artifact 7.0.2,
download-artifact 8.0.2, docker/build-push-action 7.4.0, and
docker/setup-buildx-action 4.4.1. Other action pins already match their current
stable releases. Permissions, event triggers, deployment topology, required
checks, and expected-head merge protections remain unchanged.

Local format, lint, type, contract, full test, and quality gates verify the
repository after the pin changes. GitHub's required current-head CI validates
actual action execution before merge. No application or database migration is
needed. Rollback is a squash-commit revert restoring the preceding action SHAs.
