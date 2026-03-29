FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 


RUN apt-get update && apt-get install -y \
    libpq-dev

COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /uvx /bin/
COPY pyproject.toml uv.lock /_lock/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /app
WORKDIR /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Create data directory for SQLite database with proper permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
