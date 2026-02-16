from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    s3_path = Column(String, unique=True, nullable=False)
    content_type = Column(String)
    size = Column(Integer)
    owner_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
