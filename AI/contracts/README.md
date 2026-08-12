# Contracts

This domain owns persisted entity semantics and externally observable HTTP/OpenAPI behavior.

## Canonical documents

- [Data model](DATA_MODEL.md) — owns canonical entities, relationships, invariants, lineage, indexes, field provenance, dry-run write rules, and persistence semantics.
- [HTTP API](HTTP_API.md) — owns API conventions, public/restricted endpoint behavior, filters, errors, pagination, internal command contracts, and compatibility semantics.
- [OpenAPI](OPENAPI.md) — owns deterministic machine-readable schema generation, committed artifacts, frontend type generation, schema compatibility checks, and static CI documentation.

## Precedence

1. Accepted decision records take precedence over this domain.
2. The data model is authoritative for persisted semantics, while the HTTP API is authoritative for intended endpoint and command behavior.
3. The committed OpenAPI artifact is authoritative for the machine-readable HTTP shape generated from FastAPI; the OpenAPI document owns how that artifact is produced and verified.
4. Contracts take precedence over application implementation and generated frontend consumers.

A mismatch among the three contract documents or the committed schema is a contract defect. Resolve it in the same change rather than treating one representation as permission to silently diverge.

## Contract rules

- The backend is authoritative for business rules, permissions, projections, and masking.
- FastAPI emits deterministic OpenAPI; generated frontend types consume that contract.
- Swagger, OpenAPI, and ReDoc routes remain disabled in production.
- Breaking public or persisted contract changes require an accepted decision and a migration/compatibility plan.
- Owner-console HTML under `/admin` is not a frontend API contract.

Contract changes must update affected tests, generated artifacts, product acceptance, decisions, and task traceability together.
