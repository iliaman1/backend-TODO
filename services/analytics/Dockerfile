# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install "poetry==1.8.2"

COPY poetry.lock pyproject.toml README.md ./
RUN poetry install --no-root

COPY . .
