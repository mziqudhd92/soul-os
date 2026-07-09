FROM python:3.12-slim
WORKDIR /app
COPY packages/soulos-sdk/python /sdk
COPY examples/fastapi-hybrid/app.py /app/app.py
COPY examples/support-bot/support-bot.soul.json /app/examples/support-bot/support-bot.soul.json
RUN pip install --no-cache-dir -e /sdk fastapi uvicorn httpx
ENV SOULOS_SOUL_PATH=/app/examples/support-bot/support-bot.soul.json
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
