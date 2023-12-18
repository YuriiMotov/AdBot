from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_keywords_list

pytestmark = pytest.mark.asyncio(scope="module")


async def test_keywords_get_by_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    keywords = await create_keywords_list(async_session_maker, count=1)
    
    resp = await async_client.get(f"/keywords/{keywords[0].id}/")
    assert resp.status_code == 200
    keyword_data = resp.json()
    assert keyword_data["word"] == keywords[0].word
    assert keyword_data["id"] == keywords[0].id


async def test_keywords_get_by_id_non_existed(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    keywords = await create_keywords_list(async_session_maker, count=1)
    
    resp = await async_client.get(f"/keywords/{keywords[0].id + 1}/")
    assert resp.status_code == 404
