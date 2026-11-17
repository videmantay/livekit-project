# The gatekeeper's image, built by Cloud Build from deploy.sh. Only app/ is copied in,
# so .env and tests never reach the image.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /bin/uv

WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Dependencies first, so code changes reuse this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

RUN useradd --system --no-create-home app
USER app

# Cloud Run sets PORT.
CMD ["sh", "-c", "exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
