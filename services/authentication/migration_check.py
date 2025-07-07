import time

from alembic import command
from alembic.config import Config


def check_migrations():
    retries = 5
    while retries > 0:
        try:
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            return True
        except Exception as e:
            print(f"Migration failed: {e}, retries left: {retries}")
            time.sleep(1)
            retries -= 1
    raise Exception("Failed to apply migrations")


if __name__ == "__main__":
    check_migrations()
