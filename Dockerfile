# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm config set strict-ssl false && npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + static frontend
FROM python:3.12-slim AS runtime

# System dependencies for chromadb / bcrypt / sentence-transformers
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Pre-download the sentence-transformers embedding model so cold starts are fast
ENV HF_HUB_DISABLE_SSL_VERIFY=1
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy backend source
COPY backend/app ./app

# Copy built frontend into static directory served by FastAPI
COPY --from=frontend-build /build/dist ./static

# Copy local data (ChromaDB, SQLite, uploads) as seed data
COPY backend/data ./data

# Default port; Azure Container Apps can override via PORT env var
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "30"]
