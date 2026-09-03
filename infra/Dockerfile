# syntax=docker/dockerfile:1.4
# Multi-stage production container image for ShreeNexa processes (F13.1)
# Serves api, engine, feedd, and worker roles with non-root privileges.

# ------------------------------------------------------------------------------
# Stage 1: Dependency & Wheel Builder
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv

# Copy dependency specifications first for optimal layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev packages)
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend source code and config
COPY backend/ ./backend/
COPY config/ ./config/

# Install the application package
RUN uv sync --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 2: Hardened Runtime Container
# ------------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/backend" \
    APP_ENV="production"

# Install curl for HTTP container health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create unprivileged non-root system user and group (UID/GID 10001)
RUN groupadd -g 10001 shreenexa && \
    useradd -u 10001 -g shreenexa -d /app -s /usr/sbin/nologin -c "ShreeNexa unprivileged service user" shreenexa

WORKDIR /app

# Copy virtual environment and app files with unprivileged ownership
COPY --from=builder --chown=shreenexa:shreenexa /build/.venv /app/.venv
COPY --from=builder --chown=shreenexa:shreenexa /build/backend /app/backend
COPY --from=builder --chown=shreenexa:shreenexa /build/config /app/config
COPY --from=builder --chown=shreenexa:shreenexa /build/pyproject.toml /app/pyproject.toml

# Create runtime directories with appropriate permissions
RUN mkdir -p /app/data /tmp && \
    chown -R shreenexa:shreenexa /app/data /tmp

# Switch to unprivileged non-root user
USER shreenexa:shreenexa

# Default expose API port
EXPOSE 8000

# Default entrypoint runs API role (overridden by compose services)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
