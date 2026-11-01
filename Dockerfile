FROM python:3.12-slim

# uv, copied from its official image rather than pip-installed: fast, pinned
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first so this layer is cached when only code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY ontology ./ontology
COPY dubious ./dubious
COPY app ./app
COPY worker.py ./

# Cloud Run sets $PORT; default to 8080 for local runs
ENV PORT=8080
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT"]