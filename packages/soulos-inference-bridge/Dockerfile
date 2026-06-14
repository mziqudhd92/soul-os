FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY packages/soulos-inference-bridge/ .

RUN pip install --no-cache-dir . && pip install --no-cache-dir pytest pytest-asyncio httpx

EXPOSE 11434

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "11434"]
