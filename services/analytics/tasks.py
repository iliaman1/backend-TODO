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
    print("Attempting to create KafkaConsumer...", flush=True)
    consumer = None
    try:
        consumer = KafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=KAFKA_BROKER_URL,
            group_id="analytics_consumer_group_v3",  # Снова меняем, чтобы 100% перечитать
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            # consumer_timeout_ms=10000 # Добавляем тайм-аут, чтобы цикл не был вечным, если нет сообщений
        )
        print(
            "KafkaConsumer created successfully. Entering message loop...", flush=True
        )
    except Exception as e:
        print(f"FATAL: Could not create KafkaConsumer: {e}", flush=True)
        return

    mongo_client = get_mongo_client()
    db = mongo_client.analytics_db
    print("MongoDB client connected.", flush=True)

    for message in consumer:
        try:
            print(f"Received raw message: {message}", flush=True)
            event = message.value
            event_type = event.get("event_type")

            # Получаем ID пользователя, пробуя сначала 'user_id', потом 'owner_id'
            user_id = event.get("user_id") or event.get("owner_id")

            if not event_type or not user_id:
                print(
                    f"Skipping invalid event (missing event_type or user_id/owner_id): {event}",
                    flush=True,
                )
                continue

            print(
                f"[{datetime.now()}] Processing event: {event_type} for user {user_id} from topic {message.topic}",
                flush=True,
            )

            # ... (логика обработки) ...

        except Exception as e:
            print(
                f"Error processing Kafka message: {e}, message: {message.value}",
                flush=True,
            )

    print("Exited consumer loop.", flush=True)
    if consumer:
        consumer.close()
