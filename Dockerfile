FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.7 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev
COPY . .
RUN uv sync --locked --no-dev
EXPOSE 8000
CMD ["sh", "-c", "python -m filtr_firm.seed && uvicorn filtr_firm.api.app:app --host 0.0.0.0 --port 8000"]
