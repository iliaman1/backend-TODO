import asyncio
import uuid
from os import environ
from typing import AsyncGenerator

import pytest
from auth.models.models import Base
from core.database import get_session
from main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# URL для подключения к самому СЕРВЕРУ, а не к конкретной базе
# Используем базу 'postgres', которая всегда существует
ADMIN_DB_URL = (
    f"postgresql+asyncpg://{environ.get('DATABASE_USER')}:{environ.get('DATABASE_PASSWORD')}@"
    f"{environ.get('DATABASE_HOST')}:{environ.get('DATABASE_PORT')}/postgres"
)

# Базовый URL для подключения к ТЕСТОВОЙ базе, которую мы создадим
BASE_TEST_DB_URL = (
    f"postgresql+asyncpg://{environ.get('DATABASE_USER')}:{environ.get('DATABASE_PASSWORD')}@"
    f"{environ.get('DATABASE_HOST')}:{environ.get('DATABASE_PORT')}"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Фикстура для создания тестовой БД, применения миграций и её удаления."""
    db_name = f"test_db_{uuid.uuid4().hex}"

    admin_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{db_name}"'))

    test_db_url = f"{BASE_TEST_DB_URL}/{db_name}"
    test_engine = create_async_engine(test_db_url)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    await test_engine.dispose()
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE "{db_name}" WITH (FORCE)'))

    await admin_engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Фикстура, предоставляющая сессию к тестовой БД."""
    async_session_maker = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_session(db_session: AsyncSession):
    """Переопределяет зависимость get_session для использования тестовой сессии."""

    async def _override():
        return db_session

    app.dependency_overrides[get_session] = _override
