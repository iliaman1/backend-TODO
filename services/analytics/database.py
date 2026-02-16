from os import getenv
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = getenv("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
database = client.analytics_db

# Пример: доступ к коллекции
# project_stats_collection = database.get_collection("project_stats")
