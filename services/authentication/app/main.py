from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get('/')
def home():
    return {'data': 'ok'}


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)