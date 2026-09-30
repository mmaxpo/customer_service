FROM python:3.13-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_HTTP_TIMEOUT=120
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.8.15
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --system tajeran && useradd --system --gid tajeran tajeran
COPY --from=builder /app/.venv /app/.venv
COPY app app
COPY migrations migrations
COPY scripts scripts
COPY alembic.ini pyproject.toml ./
RUN chown -R tajeran:tajeran /app
USER tajeran
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
