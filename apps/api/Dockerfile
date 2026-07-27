FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir hatchling

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Pre-download the FlashRank reranker model weights into the image so cold
# starts (this app scales to zero when idle) don't hit the network on every
# wake-up. cache_dir is pinned explicitly rather than relying on the default
# (/tmp, which some runtimes mount as a fresh tmpfs at container start —
# baked-in files there would be invisible at runtime unless the path matches
# what app/services/ai_service/rerank.py uses).
RUN python -c "\
from flashrank import Ranker; \
Ranker(model_name='ms-marco-MultiBERT-L-12', cache_dir='/app/.cache/flashrank')"

COPY . .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
