---
schema: ai-docs/adr@1
id: ADR-001
title: Split Python API and TypeScript web application
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-001: Split Python API and TypeScript web application

- Status: accepted
- Date: 2026-08-12
- Decision: use Python/FastAPI for the API and ingestion code, and TypeScript/Next.js for the web application.
- Rationale: Python is the stronger fit for Telegram ingestion, text parsing, geocoding, and offline data work. Next.js and React provide a mature interactive map UI and a clear client/server boundary.
- Consequence: the repository has two dependency ecosystems and two application images. API schemas must be generated or tested to prevent frontend/backend drift.
