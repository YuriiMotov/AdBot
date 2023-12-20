from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_categories_list

pytestmark = pytest.mark.asyncio(scope="module")


async def test_categories_get_by_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    
    resp = await async_client.get(f"/categories/{categories[0].id}/")
    assert resp.status_code == 200
    category_data = resp.json()
    assert category_data["name"] == categories[0].name
    assert category_data["id"] == categories[0].id


async def test_categories_get_by_id_non_existed(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    
    resp = await async_client.get(f"/categories/{categories[0].id + 1}/")
    assert resp.status_code == 404
