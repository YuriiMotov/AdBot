import asyncio
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine

from adbot.api.main import app
from database import get_async_session
from sqlmodel import SQLModel


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    yield create_async_engine(
        'sqlite+aiosqlite://', connect_args={"check_same_thread": False}
    )


@pytest.fixture(scope="session")
async def prepare_database(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="session")
def async_session_maker(engine, prepare_database) -> async_sessionmaker:
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def override_dependencies(async_session_maker: async_sessionmaker):
    async def get_async_session_override() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            yield session

    prev = app.dependency_overrides.get(get_async_session)
    app.dependency_overrides[get_async_session] = get_async_session_override
    yield
    if prev:
        app.dependency_overrides[get_async_session] = prev


@pytest.fixture(name="sync_client", scope="session")
def get_sync_client(override_dependencies) -> TestClient:
    yield TestClient(app)


@pytest.fixture(name="async_client", scope="session")
async def get_async_client(
    override_dependencies
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac


