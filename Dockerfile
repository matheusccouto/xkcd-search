FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY README.md LICENSE ./
COPY .agents/ ./.agents/
COPY src/ ./src/

RUN uv sync --frozen --no-dev

ENV PORT=7860
EXPOSE 7860

CMD ["uv", "run", "python", "-m", "xkcd_search.app"]
