import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from common_types import SourceType

from models.source import SourceInDB
from tests.helpers import create_categories_list, create_sources_list

pytestmark = pytest.mark.asyncio(scope="module")


async def test_source_delete(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Successfull scenario """

    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=1,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )

    resp = await async_client.delete(f"/sources/{sources[0].id}/")
    assert resp.status_code == 200

    session: AsyncSession
    async with async_session_maker() as session:
        source = await session.get(SourceInDB, sources[0].id)
    
    assert source is None


async def test_source_delete_not_exists(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Source doesn't exist """
    source_id = random.randint(1_000_000, 10_000_000)

    resp = await async_client.delete(f"/sources/{source_id}/")
    assert resp.status_code == 404

    session: AsyncSession
    async with async_session_maker() as session:
        source = await session.get(SourceInDB, source_id)
    
    assert source is None





