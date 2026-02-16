from datetime import date, datetime, timedelta
from os import getenv

from celery import Celery  # Восстановлен импорт Celery
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from kafka import KafkaConsumer  # Перенесен сюда
import json  # Перенесен сюда

from celeryconfig import beat_schedule

# Загрузка переменных окружения
load_dotenv()

# Инициализация Celery
app = Celery(
    "analytics_tasks",
    broker=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    backend=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
)

# Celery Configuration Options (аналогично settings.py Django)
app.conf.update(
    broker_url=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    result_backend=f'redis://{getenv("REDIS_HOST")}:{getenv("REDIS_PORT")}/0',
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    task_default_queue="analytics_queue",  # Уникальная очередь для analytics
    enable_utc=True,
    # beat_schedule=beat_schedule, # Отключаем старую задачу beat
)


# MongoDB client (для использования внутри задач Celery)
def get_mongo_client():
    return AsyncIOMotorClient(getenv("MONGO_URI"))


# Kafka Consumer
KAFKA_BROKER_URL = getenv("KAFKA_BROKER_URL")
KAFKA_TOPICS = ["users", "files"]  # Добавляем топики, которые будем слушать


@app.task
def process_kafka_events():
    consumer = KafkaConsumer(
        *KAFKA_TOPICS,
        bootstrap_servers=KAFKA_BROKER_URL,
        group_id="analytics_consumer_group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    print(
        f"[{datetime.now()}] Starting Kafka event processing for topics: {KAFKA_TOPICS}"
    )

    mongo_client = get_mongo_client()
    db = mongo_client.analytics_db

    for message in consumer:
        try:
            event = message.value
            event_type = event.get("event_type")
            user_id = event.get("user_id")

            if not event_type or not user_id:
                print(f"Skipping invalid event: {event}")
                continue

            print(
                f"[{datetime.now()}] Received event: {event_type} for user {user_id} from topic {message.topic}"
            )

            # Пример обработки событий (пока упрощенно)
            if event_type == "user_created":
                # Обновляем/создаем документ пользователя в MongoDB
                db.users_summary.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "email": event.get("email"),
                            "created_at": event.get("created_at"),
                        }
                    },
                    upsert=True,
                )
            elif event_type == "file_uploaded":
                # Увеличиваем счетчик файлов для пользователя
                db.users_summary.update_one(
                    {"user_id": user_id}, {"$inc": {"total_files": 1}}, upsert=True
                )
                # Сохраняем метаданные файла в отдельную коллекцию (если нужно)
                db.files_metadata.insert_one(event)
            elif event_type == "file_deleted":
                # Уменьшаем счетчик файлов для пользователя
                db.users_summary.update_one(
                    {"user_id": user_id}, {"$inc": {"total_files": -1}}
                )
                # Удаляем метаданные файла, если они хранились
                db.files_metadata.delete_one({"file_id": event.get("file_id")})

        except Exception as e:
            print(f"Error processing Kafka message: {e}, message: {message.value}")
