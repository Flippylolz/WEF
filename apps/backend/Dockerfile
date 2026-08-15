# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.13.2-slim-bookworm@sha256:6b3223eb4d93718828223966ad316909c39813dee3ee9395204940500792b740
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.3@sha256:2d890623d310b57771ce840f0da5eed5fc6d657da05ffaa45d82797b53fa3abc

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY apps/backend/src ./src
COPY apps/backend/alembic.ini ./alembic.ini
COPY apps/backend/migrations ./migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM build AS development

ENV PATH="/build/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/build/.venv \
    WEF_HOST=0.0.0.0

WORKDIR /workspace/apps/backend

COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
COPY apps/backend/src ./src
COPY apps/backend/alembic.ini ./alembic.ini
COPY apps/backend/migrations ./migrations
COPY apps/backend/scripts ./scripts
COPY apps/backend/tests ./tests
COPY contracts /workspace/contracts

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "wef_backend.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]


FROM ${PYTHON_IMAGE} AS runtime

RUN groupadd --system --gid 10001 wef \
    && useradd --system --uid 10001 --gid wef --home-dir /nonexistent wef

ENV PATH="/build/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WEF_HOST=0.0.0.0

WORKDIR /app

COPY --from=build --chown=wef:wef /build/.venv /build/.venv
COPY --from=build --chown=wef:wef /build/alembic.ini /app/alembic.ini
COPY --from=build --chown=wef:wef /build/migrations /app/migrations

USER wef

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2)"]

CMD ["wef-backend"]
