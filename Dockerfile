# un contenedor: API + web estatica en el mismo :8000
# build: docker build -t soc-precinct6 .
# run:   docker run -p 8000:8000 soc-precinct6

# --- web: build del React ---
FROM node:22-alpine AS web
WORKDIR /w
COPY soc-ui/package.json soc-ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY soc-ui/ ./
RUN VITE_API_URL="" npm run build

# --- api: python 3.10 para igualar el .venv local (sklearn 1.7.2 / xgboost 3.2.0, sin warnings)
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
# ponytail: libgomp1 = OpenMP que exigen LightGBM/XGBoost en slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable
COPY app/ ./app/
COPY src/ ./src/
COPY data/signals/signals.parquet ./data/signals/signals.parquet
COPY data/graph/nodes.parquet data/graph/edges-00000.parquet data/graph/attack_reports.parquet ./data/graph/
COPY models/m1.pkl models/m1_metrics.json models/m1_meta.json ./models/
COPY models/m2.pkl models/m2_metrics.json models/m3.pkl models/m3_metrics.json ./models/
COPY --from=web /w/dist ./soc-ui/dist
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["sh", "-c", ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
