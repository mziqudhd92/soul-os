FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.2.14 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

COPY packages/soulos-core/ .
COPY spec/ /spec/

RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --system -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
