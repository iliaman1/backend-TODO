# Backend TODO - Микросервисный проект

## Описание

Этот проект представляет собой бэкенд для TODO-приложения, построенный на основе микросервисной архитектуры. Он демонстрирует взаимодействие различных сервисов, асинхронную обработку задач и сбор аналитики в реальном времени с использованием Kafka.

## Архитектура

Проект состоит из следующих ключевых компонентов:

*   **Nginx:** Единая точка входа, проксирующая запросы к соответствующим API-сервисам.
*   **Authentication Service (`auth-api`):** Отвечает за регистрацию, аутентификацию (JWT), управление пользователями, ролями и правами.
    *   **Стек:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, Celery, Redis.
*   **TODO Service (`todo-api`):** Основной сервис для управления проектами и задачами.
    *   **Стек:** Django, Django Rest Framework, PostgreSQL.
*   **Files Service (`files-api`):** Отвечает за загрузку, хранение и удаление файлов.
    *   **Стек:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, Minio (S3-совместимое хранилище).
*   **Analytics Service (`analytics-api`):** Собирает и предоставляет аналитические данные о действиях пользователей.
    *   **Стек:** FastAPI, MongoDB, Celery, Kafka.

### Взаимодействие сервисов

Взаимодействие между сервисами осуществляется двумя способами:
1.  **Синхронно (HTTP):** Некоторые сервисы могут делать прямые запросы к другим (например, для валидации токена).
2.  **Асинхронно (Kafka):** Основные бизнес-события (создание пользователя, загрузка файла и т.д.) публикуются в топики Kafka. `Analytics Service` подписывается на эти топики и обновляет свои данные в реальном времени.

## Как запустить проект

### Требования
*   Docker
*   Docker Compose

### 1. Настройка переменных окружения

Перед первым запуском необходимо создать и заполнить файлы с переменными окружения:

1.  **`infrastructure/.env`**: Этот файл содержит общие переменные для `docker-compose`, такие как логины и пароли для баз данных. Скопируйте `infrastructure/.env.example` и заполните его.
2.  **`.env` для каждого сервиса**: Каждый сервис в директории `services/` имеет свой файл `.env.example`. Скопируйте его в `.env` в той же директории и заполните необходимые значения (секретные ключи, токены, URL и т.д.).
    *   `services/authentication/.env`
    *   `services/TODO-core/.env`
    *   `services/files/.env`
    *   `services/analytics/.env`

### 2. Сборка и запуск

Выполните следующую команду из корневой директории проекта:

```bash
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Эта команда соберет образы для всех сервисов и запустит их в фоновом режиме.

## Описание сервисов и портов

*   **Nginx (API Gateway):** `http://localhost:8080`
*   **Authentication API:** `http://localhost:8080/api/auth/`
*   **TODO API:** `http://localhost:8080/api/core/`
*   **Files API:** `http://localhost:8080/api/files/`
*   **Analytics API:** `http://localhost:8080/api/analytics/`
*   **Minio Console:** `http://localhost:9001` (Веб-интерфейс для S3 хранилища)

## API Документация

Для каждого FastAPI-сервиса доступна интерактивная документация Swagger/OpenAPI по адресу `/docs`:

*   **Authentication API Docs:** `http://localhost:8080/api/auth/docs`
*   **Files API Docs:** `http://localhost:8080/api/files/docs`
*   **Analytics API Docs:** `http://localhost:8080/api/analytics/docs`
