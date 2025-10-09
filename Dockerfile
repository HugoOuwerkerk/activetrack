FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir "poetry==$POETRY_VERSION" \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

COPY . .

RUN mkdir -p /data

ENV FLASK_APP=app.py

EXPOSE 8000

CMD ["poetry", "run", "gunicorn", "app:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
