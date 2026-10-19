# Backend image (dependencies from uv.lock, no dev tools, non-root). Contracts are copied for Catalog validation.
FROM python:3.12-alpine AS build
COPY --from=ghcr.io/astral-sh/uv:0.6.17 /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12-alpine
# Patch OS packages and drop pip (not used at runtime) so the image carries no known fixable CVEs.
# Tesseract with Japanese data reads scanned documents (ADR-003, D-033; Apache-2.0).
RUN apk upgrade --no-cache && apk add --no-cache tesseract-ocr tesseract-ocr-data-jpn \
    && python -m pip uninstall -y pip && adduser -S -D -H -u 10001 easf \
    && mkdir -p /data/documents && chown easf /data/documents && chmod 700 /data/documents
WORKDIR /app/backend
COPY --from=build /app/backend/.venv /app/backend/.venv
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY contracts /app/contracts
ENV PATH="/app/backend/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 EASF_CONTRACTS_DIR=/app/contracts
USER easf
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8000/health || exit 1
CMD ["uvicorn", "app.main:create_app", "--factory", "--no-server-header", "--host", "0.0.0.0", "--port", "8000"]
