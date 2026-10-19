# Production and candidate configuration coverage

Twelve new boundary cases and the existing five candidate cases cover all 487
statements and 158 branch paths in the production builder/validator and candidate
builder/validator. Each of the four implementations has an independent 100%
operational floor. Deliberate policy faults reject removal of each floor.

The tests use invented credentials, isolated environment mappings and temporary
files. No provider, database, host or account is contacted. Real subprocess
entrypoints print help only; configuration creation and validation run against
synthetic inputs. Runtime implementation, dependencies, source inventory and
coverage exclusions are unchanged.

## Assertions

- Production configuration round-trips through the restricted parser, percent-encodes
  database credentials, writes sorted mode-0600 files and refuses to overwrite an
  existing file without changing its contents.
- Missing/empty required values, invalid identifiers/passwords, malformed provider,
  contact and Telegram credentials, equal contact keys and unsupported log levels
  are rejected without including their values in errors.
- Bootstrap credentials require both fields and their minimum lengths. Optional
  Telegram values and parser replay flags retain explicit normalization.
- Groq configuration validates its key, fixed model, enablement/recovery flags,
  UUID owner, timeout and batch bounds, including nonnumeric/nonfinite inputs.
  Blank batch settings retain the documented defaults for batch and synchronous
  operation. These tests never send a provider request or activate recovery.
- Production validation rejects malformed/duplicate env lines, missing keys,
  placeholders, mismatched source identity/paths, unsafe ports/binds, mutable image
  references, external database targets and invalid runtime credentials. Test-mode
  local images and loopback configuration retain their explicit allowance.
- Candidate validation preserves checksum-scoped media roots, migration identity,
  database identity and loopback-only verification. Unsafe names/passwords/ports,
  missing or placeholder values, foreign paths/roots, unexpected checksums and
  external/wrong database targets are rejected.
- CLI composition returns bounded status, writes private candidate configuration
  and reports malformed production input through the existing argument parser.

This is unplanned quality maintenance under the owner's repository-wide coverage
request, protecting the existing [E7-T3 deployment configuration](../epics/E7-production-delivery/tasks/E7-T3-implement-github-image-and-deployment-workflows.md)
and [E7-T11 historical candidate workflow](../epics/E7-production-delivery/tasks/E7-T11-activate-the-verified-historical-candidate.md) boundaries.
Remaining operational Python, shell and substantive embedded Python remain required
before completing the overall 100% goal.
