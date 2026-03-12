import json
from os import getenv

from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv()

KAFKA_BROKER_URL = getenv("KAFKA_BROKER_URL")


def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER_URL,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def send_kafka_message(topic: str, message: dict):
    try:
        producer = get_kafka_producer()
        producer.send(topic, message)
        producer.flush()
        print(f"Sent message to Kafka topic '{topic}': {message}")
    except Exception as e:
        print(f"Failed to send message to Kafka: {e}")
