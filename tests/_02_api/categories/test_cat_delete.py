import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models.category import CategoryInDB
from tests.helpers import create_categories_list

pytestmark = pytest.mark.asyncio(scope="module")


async def test_category_delete(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Successfull scenario """
    categories = await create_categories_list(async_session_maker, count=1)

    resp = await async_client.delete(f"/categories/{categories[0].id}/")
    assert resp.status_code == 200

    session: AsyncSession
    async with async_session_maker() as session:
        cat = await session.get(CategoryInDB, categories[0].id)
    
    assert cat is None


async def test_category_delete_not_exists(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Category doesn't exist """
    cat_id = random.randint(1_000_000, 10_000_000)

    resp = await async_client.delete(f"/categories/{cat_id}/")
    assert resp.status_code == 404

    session: AsyncSession
    async with async_session_maker() as session:
        cat = await session.get(CategoryInDB, cat_id)
    
    assert cat is None





