import random
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_publication

pytestmark = pytest.mark.asyncio(scope="module")


async def test_publications_get_by_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):

    publication = await create_publication(async_client, async_session_maker)
    
    resp = await async_client.get(f"/publications/{publication['id']}/")
    assert resp.status_code == 200
    publication_data = resp.json()
    assert len(publication_data) == 7 # Make sure we check all response model fields
    assert publication_data["url"] == publication["url"]
    assert publication_data["id"] == publication["id"]
    assert publication_data["source_id"] == publication["source_id"]
    assert publication_data["dt"] == publication["dt"]
    assert publication_data["hash"] == publication["hash"]
    assert publication_data["preview"] == publication["preview"]
    assert publication_data["processed"] == publication["processed"]


async def test_publications_get_by_id_non_existed(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    publication_id = random.randint(1_000_000, 10_000_000)
    
    resp = await async_client.get(f"/publications/{publication_id}/")
    assert resp.status_code == 404
