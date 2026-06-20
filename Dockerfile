FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY config.toml ./
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1
CMD ["python", "-m", "src.main"]
