---
schema: ai-docs/adr@1
id: ADR-004
title: Use MapLibre and OpenFreeMap initially
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-004: Use MapLibre and OpenFreeMap initially

- Status: accepted
- Date: 2026-08-12
- Decision: render maps with MapLibre GL JS and use OpenFreeMap for the initial vector basemap.
- Rationale: this keeps the map stack open, avoids an API key for the first release, supports GeoJSON, clustering, click interactions, and can move to another compatible tile source.
- Consequence: OpenStreetMap attribution is mandatory. OpenFreeMap has no contractual SLA, so the style URL must be configurable and the application must tolerate provider failure.
