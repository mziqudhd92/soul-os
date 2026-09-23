FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app

COPY packages/soulos-gateway/requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY packages/soulos-gateway/ .

RUN echo '{}' > /app/keys.json \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin soulos \
    && chown -R soulos:soulos /app \
    && mkdir -p /tmp/uv-cache && chown -R soulos:soulos /tmp/uv-cache

USER soulos

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
