FROM python:3.12-slim

# uv 版本與 CI／本機三處必須一致（見 CLAUDE.md「Python 依賴管理」）。
# 要升級就三處一起升，不要只動一處。
COPY --from=ghcr.io/astral-sh/uv:0.6.11 /uv /uvx /bin/

WORKDIR /app

# venv 必須放在 /app 之外。docker-compose.yml 會把 ./apps/api 掛載成 /app，
# 預設的 /app/.venv 會被主機（Windows）的 .venv 整個蓋掉，容器裡就找不到
# alembic / uvicorn。放 /opt/venv 就不受掛載影響。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# 依賴層：只複製 lock 與 pyproject，原始碼改動時這層仍能命中 cache。
# --locked：lock 與 pyproject 不一致就直接失敗，不會像 pip 那樣默默解析出另一組版本。
# --no-dev：排除 pytest / ipykernel。
# --no-install-project：此時 app/ 還沒複製進來，先只裝第三方依賴。
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

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

# 補裝專案本身（上一次 sync 用了 --no-install-project）
RUN uv sync --locked --no-dev

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
