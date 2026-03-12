import time
from tasks import process_kafka_events

import time
import sys
from tasks import process_kafka_events

if __name__ == "__main__":
    print("Kafka Consumer Runner script started.", flush=True)
    while True:
        try:
            print("Calling process_kafka_events task...", flush=True)
            process_kafka_events()
            print(
                "process_kafka_events task finished unexpectedly. Restarting...",
                flush=True,
            )
        except Exception as e:
            print(
                f"CRITICAL: Error in Kafka consumer loop: {e}. Restarting in 5 seconds...",
                flush=True,
            )
            time.sleep(5)
