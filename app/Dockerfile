# syntax=docker/dockerfile:1
# ===========================
# Base Image
# ===========================

FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ===========================
# Builder Stage
# ===========================
FROM base AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY ./app/pyproject.toml ./app/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ===========================
# Production Stage
# ===========================
FROM base AS production

ENV PATH="/app/.venv/bin:$PATH" \
    UV_CACHE_DIR="/tmp/uv-cache"

RUN groupadd --system appgroup && \
    useradd --system --no-create-home --gid appgroup appuser

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

CMD ["uv", "run", "--", "fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]
