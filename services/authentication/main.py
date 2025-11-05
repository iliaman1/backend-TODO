import uvicorn
from auth.dependencies import get_current_user
from auth.models.models import User
from auth.routers.admin import admin_router
from auth.routers.auth import auth_router
from auth.schemas import UserOutSchema
from core.database import get_session
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tasks import send_email

app = FastAPI()
app.include_router(auth_router)
app.include_router(admin_router)


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


@app.post("/send-email")
def trigger_email():
    result = send_email.delay()
    return {"status": "Задача отправлена", "task_id": str(result)}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
