# ══════════════════════════════════════════════════════════════
#  JARVIS — Dockerfile
# ══════════════════════════════════════════════════════════════
FROM python:3.14-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# ── Build stage ──
FROM base AS builder

COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install .

# ── Production stage ──
FROM base AS production

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Create data directories
RUN mkdir -p data/conversations data/knowledge_base data/vector_store data/long_term_memory data/logs

EXPOSE 8000

# Default: run the web UI
CMD ["python", "-m", "jarvis", "--ui", "web"]
