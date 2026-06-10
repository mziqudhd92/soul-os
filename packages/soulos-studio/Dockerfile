FROM python:3.12-slim

WORKDIR /app

COPY packages/soulos-studio/pyproject.toml packages/soulos-studio/README.md ./
COPY packages/soulos-studio/soulos_studio ./soulos_studio
COPY docs /docs

RUN pip install --no-cache-dir .

ENV SOULOS_KERNEL_URL=http://soulos-kernel:8000
ENV SOULOS_DOCS_ROOT=/docs

EXPOSE 8765

CMD ["soulos-studio", "--host", "0.0.0.0", "--port", "8765"]
