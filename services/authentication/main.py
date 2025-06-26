from fastapi import FastAPI, Depends
import uvicorn
from sqlalchemy import text

from auth.routers.auth import router, auth_required
from core.database import get_session

from tasks import send_email

app = FastAPI()
app.include_router(router)


@app.get('/')
def read_root():
    return {'message': 'auth service'}


@app.get('/onlyauth')
def onlyauth(user_id: str = Depends(auth_required)):
    return {"user_id": user_id, "message": "Authenticated!"}


@app.get('/test')
async def test_session():
    session = await get_session()
    try:
        result = await session.execute(text("SELECT 1"))
        return {'data': result.scalar()}  # Должно быть 1
    finally:
        await session.close()

@app.post('/send-email')
def trigger_email():
    result = send_email.delay()
    return {'status': 'Задача отправлена', 'task_id': str(result)}


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
