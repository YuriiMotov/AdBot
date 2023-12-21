import random
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from common_types import SourceType

from tests.helpers import create_sources_list, create_categories_list

pytestmark = pytest.mark.asyncio(scope="module")


async def test_sources_get_by_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)

    sources = await create_sources_list(
        async_session_maker,
        count=1,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    
    resp = await async_client.get(f"/sources/{sources[0].id}/")
    assert resp.status_code == 200
    source_data = resp.json()
    assert source_data["title"] == sources[0].title
    assert source_data["id"] == sources[0].id
    assert source_data["type"] == sources[0].type
    assert source_data["category_id"] == sources[0].category_id
    assert source_data["source_info"] == sources[0].source_info


async def test_sources_get_by_id_non_existed(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    source_id = random.randint(1_000_000, 10_000_000)
    
    resp = await async_client.get(f"/sources/{source_id}/")
    assert resp.status_code == 404
