# Release artifact integrity and reuse coverage

Coverage work reproduced four uncaught `AttributeError` results for manifests or
image evidence containing JSON arrays/null. These invalid artifacts should cause
the existing reuse search to fall back to full verification, but their unexpected
exception type escaped its validation-error handling.

## Corrected behavior

The bundle validator explicitly requires object-shaped manifest and image evidence,
raising its supported type-validation error before inspecting fields. The existing
reuse search then rejects the artifact and continues its normal full-verification
fallback. Explicit artifact validation still refuses invalid evidence. Source SHA,
workflow fingerprint, immutable image, checksum, required-file and symlink checks
retain their existing behavior; invalid artifacts never authorize deployment.

## Regression and coverage evidence

Eight new cases and eight existing release-order cases cover all 179 statements and
58 branch paths in `create_checksums.py`, `create_release_manifest.py` and
`reuse_release.py`. Each has an independent 100% operational floor, with deliberate
policy faults rejecting a removed floor. Runtime exclusions and dependencies are
unchanged. The only runtime change is the two explicit JSON object checks.

Tests assert sorted deterministic checksums, empty and multi-chunk files, complete
artifact inventories, source/digest/timestamp/fingerprint validation, malformed
object shapes, symlink/path escapes, duplicate/corrupt/missing files, trusted
workflow definition identity and exact-source successful main-push job evidence.
Reuse search exercises missing tools, unusable runs/artifacts, failed downloads,
malformed downloaded evidence, safe fallback and valid synthetic downloads. CLI
outputs retain exact digests, lowercase image identity, reuse status and append-only
Actions output behavior. Invalid command input and explicit validation refusal
remain errors.

Every GitHub API call and artifact download is replaced with synthetic data; actual
CLI subprocesses only print help or hash an invented temporary bundle. No real
artifact is listed, downloaded, changed or deployed. The pre-fix four-error
regression log and generated reports remain ignored.

This is unplanned maintenance under the owner's coverage request, protecting the
existing [E7-T3 immutable delivery workflow](../epics/E7-production-delivery/tasks/E7-T3-implement-github-image-and-deployment-workflows.md)
and [verified delivery cache boundaries](../operations/DEPLOYMENT.md). Remaining
operational Python, shell and substantive embedded Python stay in scope before
completing the repository-wide 100% goal.
