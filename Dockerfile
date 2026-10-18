# Артефакт приложения: Docker-образ REST-сервиса бронирования
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала зависимости — этот слой кэшируется, пока requirements.txt не меняется
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Версия «зашивается» в образ при сборке в CI (см. .github/workflows/ci.yml)
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.version=${APP_VERSION}

RUN useradd --create-home appuser && chown appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# opentelemetry-instrument включает автоматический сбор трассировок, метрик и логов
CMD ["opentelemetry-instrument", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
