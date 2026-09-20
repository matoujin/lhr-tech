FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV DATA_DIR=/data
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8080
EXPOSE 8080
VOLUME ["/data"]

CMD ["tesla-readonly"]
