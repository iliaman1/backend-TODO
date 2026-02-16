import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from os import getenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
from dotenv import load_dotenv
from os import getenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

app = FastAPI(openapi_prefix="/api/analytics")


@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(getenv("MONGO_URI"))
    app.mongodb = app.mongodb_client.analytics_db


@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()


@app.get("/")
def read_root():
    return {"message": "Analytics service is running"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=int(getenv("ANALYTICS_SERVICE_PORT", 8002))
    )
