# Multi-stage Dockerfile for TextLoom production deployment

###########################################
# Base stage with common dependencies
###########################################
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Set working directory
WORKDIR /app

###########################################
# Development stage
###########################################
FROM base as development

# Install development dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --dev

# Copy application code
COPY --chown=appuser:appuser . .

# Create required directories
RUN mkdir -p logs workspace && \
    chown -R appuser:appuser logs workspace

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

###########################################
# Builder stage for production
###########################################
FROM base as builder

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

###########################################
# Production stage
###########################################
FROM python:3.11-slim as production

# Build metadata
ARG BUILD_DATE
ARG VERSION
ARG GIT_COMMIT

LABEL org.opencontainers.image.title="TextLoom" \
      org.opencontainers.image.description="Intelligent text-to-video generation system" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.source="https://github.com/textloom/textloom" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="TextLoom Team"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    TEXTLOOM_VERSION="${VERSION}" \
    ENVIRONMENT=production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Copy health check script
COPY --chown=appuser:appuser scripts/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Create required directories
RUN mkdir -p logs workspace && \
    chown -R appuser:appuser logs workspace

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh api

# Expose port
EXPOSE 8000

# Production command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

###########################################
# Worker stage for Celery workers
###########################################
FROM production as worker

# Override health check for worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import celery_config; app = celery_config.celery_app; inspect = app.control.inspect(); stats = inspect.stats(); exit(0 if stats else 1)"

# Worker command
CMD ["python", "-m", "celery", "-A", "celery_config", "worker", "--loglevel=info", "--concurrency=2"]

###########################################
# Flower stage for monitoring
###########################################
FROM production as flower

# Expose Flower port
EXPOSE 5555

# Override health check for Flower
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5555 || exit 1

# Flower command
CMD ["python", "-m", "celery", "-A", "celery_config", "flower", "--address=0.0.0.0", "--port=5555"]

###########################################
# Beat stage for scheduled tasks
###########################################
FROM production as beat

# Override health check for Beat
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/tmp/celerybeat.pid') else 1)"

# Beat command
CMD ["python", "-m", "celery", "-A", "celery_config", "beat", "--loglevel=info", "--schedule=/tmp/celerybeat-schedule"]