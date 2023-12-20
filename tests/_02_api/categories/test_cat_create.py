from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models.category import CategoryInDB

pytestmark = pytest.mark.asyncio(scope="module")


async def test_category_create(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    create_data = {
        "name": str(uuid4())
    }
    resp = await async_client.post(f"/categories/", json=create_data)
    assert resp.status_code == 201
    cat_data = resp.json()
    assert "id" in cat_data
    assert cat_data["name"] == create_data["name"]

    session: AsyncSession
    async with async_session_maker() as session:
        cat = await session.get(CategoryInDB, cat_data["id"])
    
    assert cat is not None
    assert cat.name == create_data["name"]
    assert cat_data["id"] == cat.id


async def test_category_create_too_short(
    async_client: TestClient,
):
    create_data = {
        "name": str(uuid4())[0]
    }
    resp = await async_client.post(f"/categories/", json=create_data)
    assert resp.status_code == 422


async def test_category_create_duplicated(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    name = str(uuid4())
    session: AsyncSession
    async with async_session_maker() as session:
        cat = CategoryInDB(name=name)
        session.add(cat)
        await session.commit()

    create_data = {
        "name": name
    }
    resp = await async_client.post(f"/categories/", json=create_data)
    assert resp.status_code == 200
    cat_data = resp.json()

    session: AsyncSession
    async with async_session_maker() as session:
        st = select(CategoryInDB).where(CategoryInDB.name == name)
        cats = (await session.scalars(st)).all()

        assert len(cats) == 1
        assert cats[0].id == cat_data["id"]
