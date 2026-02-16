import uvicorn
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from dotenv import load_dotenv
from os import getenv
import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from s3_utils import get_s3_client, create_presigned_url, delete_object
from database import async_session_maker
from models import FileMetadata
from authentication import get_current_user, JWTPayloadUser
from sqlalchemy.future import select
from sqlalchemy import delete, update
from services.common.kafka_utils import send_kafka_message

load_dotenv()

app = FastAPI(openapi_prefix="/api/files")

MINIO_BUCKET_NAME = getenv("MINIO_BUCKET_NAME")


# --- Schemas ---
class FileUpdateSchema(BaseModel):
    filename: str


class FileOutSchema(BaseModel):
    id: int
    filename: str
    content_type: str | None
    size: int | None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Files service is running"}


@app.post("/upload/", response_model=FileOutSchema)
async def upload_file(
    file: UploadFile = File(...), user: JWTPayloadUser = Depends(get_current_user)
):
    s3_client = get_s3_client()
    file_extension = file.filename.split(".")[-1]
    s3_path = f"{uuid.uuid4()}.{file_extension}"

    try:
        # Перематываем файл в начало
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file,
            MINIO_BUCKET_NAME,
            s3_path,
            ExtraArgs={"ContentType": file.content_type},
        )

        async with async_session_maker() as session:
            new_file_meta = FileMetadata(
                filename=file.filename,
                s3_path=s3_path,
                content_type=file.content_type,
                size=file.size,
                owner_id=user.id,  # Теперь owner_id берется из токена
            )
            session.add(new_file_meta)
            await session.commit()
            await session.refresh(new_file_meta)

            # Отправляем сообщение в Kafka
            send_kafka_message(
                "files",
                {
                    "event_type": "file_uploaded",
                    "file_id": new_file_meta.id,
                    "owner_id": user.id,
                    "filename": new_file_meta.filename,
                    "s3_path": new_file_meta.s3_path,
                    "content_type": new_file_meta.content_type,
                    "size": new_file_meta.size,
                    "created_at": new_file_meta.created_at.isoformat(),
                },
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

    return new_file_meta


@app.get("/files/", response_model=List[FileOutSchema])
async def list_files(user: JWTPayloadUser = Depends(get_current_user)):
    async with async_session_maker() as session:
        # Фильтрация по owner_id
        query = select(FileMetadata).where(FileMetadata.owner_id == user.id)
        result = await session.execute(query)
        files = result.scalars().all()
    return files


@app.get("/files/{file_id}/", response_model=FileOutSchema)
async def get_file_info(file_id: int, user: JWTPayloadUser = Depends(get_current_user)):
    async with async_session_maker() as session:
        file_meta = await session.get(FileMetadata, file_id)

    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")

    # Проверка прав доступа
    if file_meta.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return file_meta


@app.get("/files/{file_id}/url/")
async def get_file_url(file_id: int, user: JWTPayloadUser = Depends(get_current_user)):
    async with async_session_maker() as session:
        file_meta = await session.get(FileMetadata, file_id)

    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")

    # Проверка прав доступа
    if file_meta.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    url = create_presigned_url(file_meta.s3_path)
    if not url:
        raise HTTPException(status_code=500, detail="Could not generate file URL")

    return {"url": url}


@app.delete("/files/{file_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: int, user: JWTPayloadUser = Depends(get_current_user)):
    async with async_session_maker() as session:
        file_meta = await session.get(FileMetadata, file_id)

        if not file_meta:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # Проверка прав доступа
        if file_meta.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        if not delete_object(file_meta.s3_path):
            raise HTTPException(
                status_code=500, detail="Failed to delete file from storage"
            )

        await session.delete(file_meta)
        await session.commit()

        # Отправляем сообщение в Kafka
        send_kafka_message(
            "files",
            {
                "event_type": "file_deleted",
                "file_id": file_meta.id,
                "owner_id": user.id,
                "s3_path": file_meta.s3_path,
                "deleted_at": datetime.now().isoformat(),
            },
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/files/{file_id}/", response_model=FileOutSchema)
async def update_file_metadata(
    file_id: int,
    file_data: FileUpdateSchema,
    user: JWTPayloadUser = Depends(get_current_user),
):
    async with async_session_maker() as session:
        file_meta = await session.get(FileMetadata, file_id)

        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")

        if file_meta.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        file_meta.filename = file_data.filename
        await session.commit()
        await session.refresh(file_meta)

    return file_meta


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=int(getenv("FILES_SERVICE_PORT", 8003))
    )
