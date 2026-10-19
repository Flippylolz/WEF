# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e

ARG PYTHON_IMAGE=python:3.13.16-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336

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
