# ============ Stage 1: build the React app ============
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ============ Stage 2: Django + RAG engine ============
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0 \
    FRONTEND_DIST=/app/frontend_dist \
    MODEL_CACHE_DIR=/app/model_cache \
    STORAGE_DIR=/app/storage
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model + reranker now, so the app starts fast and works offline
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/model_cache')" && \
    python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2', cache_dir='/app/model_cache')"

COPY backend/ ./
COPY --from=frontend /frontend/dist ./frontend_dist

EXPOSE 8000
# 1 worker (the AI model is loaded once) with 4 threads to handle several users
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "180"]
