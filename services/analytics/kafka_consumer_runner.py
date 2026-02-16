import time
from tasks import process_kafka_events

if __name__ == "__main__":
    print("Starting Kafka Consumer Runner...")
    while True:
        try:
            process_kafka_events()
        except Exception as e:
            print(f"Error in Kafka consumer loop: {e}. Restarting in 5 seconds...")
            time.sleep(5)
