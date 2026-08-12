# Warsaw Estate Platform

Warsaw Estate Platform (WEF) will turn a Telegram real-estate export into a filterable map of Warsaw developments and offers.

## Current status

The repository is in its approval-gated foundation phase. Application code, Dockerfiles, Docker Compose, and Make targets have not been implemented yet.

Start with:

- [AI documentation index](AI/README.md)
- [Architecture](AI/architecture/README.md)
- [Epics and task dependencies](AI/epics/README.md)
- [Approval-gated workflow](AI/workflow/README.md)
- [Repository and change rules](AI/governance/REPOSITORY_RULES.md)

## Planned stack

- Python, FastAPI, SQLAlchemy, PostgreSQL, and PostGIS
- TypeScript, Next.js, React, and MapLibre
- Docker Compose with Caddy
- GitHub Actions and GitHub Container Registry

The backend is authoritative for business behavior. The frontend primarily renders generated API contracts and backend-provided projections.

## Repository safety

The local `est-test/` export, `est-test.tar.gz`, media, environment files, Telegram sessions, local databases, and generated sensitive reports must never be committed or copied into Docker build contexts.

Use `.env.example` only as a list of safe local-development names. Production configuration is transferred from GitHub Actions during deployment and is never committed.

## Contribution workflow

Each implementation task requires:

1. an approved epic spike;
2. promotion from `proposed-tasks/` to `tasks/`;
3. an approved implementation plan;
4. completed dependencies; and
5. one dedicated branch and pull request.

GitHub-enforced branch protection is currently out of scope, so reviews and checks are enforced procedurally.
