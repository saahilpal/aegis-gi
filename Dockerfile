# Multi-stage production build for Aegis GI Backend
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final lean runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user for security
RUN groupadd -r aegis && useradd -r -g aegis aegis

# Copy python dependencies from builder
COPY --from=builder /root/.local /home/aegis/.local
ENV PATH=/home/aegis/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Copy application code
COPY backend ./backend
COPY pytest.ini .

# Create data directory for SQLite fallback if used
RUN mkdir -p data && chown -R aegis:aegis /app

USER aegis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
