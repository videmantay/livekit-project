# The agent's image, built by LiveKit Cloud from `lk agent create` / `lk agent deploy`.
# Secrets come from LiveKit Cloud agent secrets at runtime, never from this image, and
# LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET are injected by LiveKit Cloud.
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

COPY *.py ./
COPY facts ./facts

RUN useradd --system --create-home app
USER app

# Bake the VAD model into the image (in the app user's cache), so the first
# call doesn't download it. agent.py validates its settings at import, so this step gets
# placeholder values that aren't secrets and don't reach the running container.
RUN ELEVENLABS_VOICE_ID=build ELEVENLABS_SPANISH_VOICE_ID=build TAVUS_API_KEY=build TAVUS_FACE_ID=build \
    .venv/bin/python agent.py download-files

CMD [".venv/bin/python", "agent.py", "start"]
