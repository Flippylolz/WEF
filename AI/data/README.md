# Data

This domain owns the observed Telegram export evidence, source lineage, known quality limitations, retention constraints, and readiness gates. It describes evidence; it does not silently override accepted product, contract, or ingestion rules.

## Canonical documents

- [Source baseline](SOURCE_BASELINE.md) — source inventory, channel/message shape, listing population, coordinates, media relationships, and identity/lineage.
- [Quality and readiness](QUALITY_AND_READINESS.md) — quality risks, import accounting, retention/environment constraints, and the data-readiness gate.

## Handling rules

- Preserve immutable source messages and source lineage.
- Record parsing and geocoding uncertainty explicitly.
- Keep raw exports, media, databases, and source-derived sensitive reports outside Git and Docker build contexts.
- Never interpret the absence of a reliable status signal as current availability.
- Do not expose source contacts through public data contracts.

Readiness claims must cite reconciled counts and known exclusions. Source-asset links are relative to this folder and point outside `AI/`; the raw data remains outside documentation and Git.
