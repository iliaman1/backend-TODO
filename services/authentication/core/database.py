import datetime
import re
from os import environ
from typing import AsyncGenerator

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.pool import NullPool

DATABASE_URL = (
    f"postgresql+asyncpg://{environ.get('DATABASE_USER')}:{environ.get('DATABASE_PASSWORD')}@"
    f"{environ.get('DATABASE_HOST')}:{environ.get('DATABASE_PORT')}/{environ.get('DATABASE_NAME')}"
)

engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


class Model(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.now
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        return re.sub("(?!^)([A-Z]+)", r"_\1", cls.__name__).lower()
