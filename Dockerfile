FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install "poetry>=2.0,<3.0"

WORKDIR /app

# Отдельный слой для зависимостей — кеш не сбрасывается при изменении кода.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Fallback для `docker run` без compose. Compose переопределяет command,
# добавляя `alembic upgrade head` перед запуском.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
