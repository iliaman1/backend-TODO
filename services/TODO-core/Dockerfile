FROM python:3.11-alpine

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip3 install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

RUN poetry install --no-root --no-interaction

COPY . .