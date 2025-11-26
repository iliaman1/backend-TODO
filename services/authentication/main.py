from datetime import timedelta

import uvicorn
from auth.dependencies import get_current_user
from auth.models.models import User
from auth.queries import create_access_token
from auth.routers import admin, auth, internal
from auth.schemas import UserOutSchema
from core.database import get_session
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tasks import send_email

app = FastAPI(openapi_prefix="/api/auth")
app.include_router(auth.auth_router)
app.include_router(admin.admin_router)
app.include_router(internal.internal_router)


@app.get("/")
def read_root():
    return {"message": "auth service"}


@app.get("/onlyauth", response_model=UserOutSchema)
async def onlyauth(user: User = Depends(get_current_user)):
    return user


@app.get("/test")
async def test_session(session: AsyncSession = Depends(get_session)):
    print("Database session check successful.")
    result = await session.execute(text("SELECT 1"))
    return {"data": result.scalar()}


@app.get("/generate-service-token")
async def generate_service_token_endpoint(user: User = Depends(get_current_user)):
    # Этот токен будет иметь очень большой срок действия
    service_token = create_access_token(user=user, expires_delta=timedelta(days=365))
    return {"service_token": service_token}


@app.post("/send-email")
def trigger_email():
    result = send_email.delay()
    return {"status": "Задача отправлена", "task_id": str(result)}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
