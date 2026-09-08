# Python 3.12, not 3.13 or 3.14. sentence-transformers does not classify above
# 3.13 and CLIP embeddings are on the critical path for search.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libgomp is LightGBM's OpenMP runtime. Without it `import lightgbm` fails at
# load time with an error that does not mention LightGBM.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# The deploy extra, not the bare package. Without google-genai every listing
# generation and image enhancement returns 503, and it fails at runtime rather
# than at build time, so the container starts looking perfectly healthy.
RUN pip install --upgrade pip && pip install ".[deploy]"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY data ./data

EXPOSE 8000

# Render, Railway and Fly all inject the port to bind. Hardcoding 8000 makes
# the container start cleanly and then be unreachable, which is the most
# annoying possible failure because nothing looks wrong.
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
