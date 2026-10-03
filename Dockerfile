# Stage 1: Build the React Frontend SPA
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend + Static SPA Server
FROM python:3.10-slim
WORKDIR /app

# System dependencies for PostgreSQL and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code and alembic migrations
COPY backend/ ./backend/

# Copy built frontend static assets from Stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend_dist/

# Set production environment variables
ENV FRONTEND_DIST=/app/frontend_dist
ENV PYTHONPATH=/app/backend
ENV PORT=8000

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
