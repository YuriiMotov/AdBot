from datetime import datetime
import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from common_types import SourceType

from models.publication import PublicationInDB
from tests.helpers import (
    create_categories_list, create_sources_list
)

pytestmark = pytest.mark.asyncio(scope="module")



async def test_publication_add(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=1,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    create_data = {
        "url": str(uuid4()),
        "dt": datetime.now().isoformat(),
        "text": str(uuid4()),
        "source_id": sources[0].id
    }
    resp = await async_client.post(f"/publications/", json=create_data)
    assert resp.status_code == 201
    publication_data = resp.json()
    assert len(publication_data) == 7  # Make sure we check all response model fields
    assert publication_data["id"] > 0
    assert publication_data["url"] == create_data["url"]
    assert len(publication_data["hash"]) == 32
    assert publication_data["preview"] == create_data["text"][:150]
    assert publication_data["source_id"] == create_data["source_id"]
    assert publication_data["dt"] == create_data["dt"]
    assert publication_data["processed"] == False

    session: AsyncSession
    async with async_session_maker() as session:
        publication = await session.get(PublicationInDB, publication_data["id"])
        assert publication is not None


async def test_publication_add_dupliacted_hash(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=2,
        source_type=SourceType.telegram,
        category_id=categories[0].id
    )
    create_data = {
        "url": str(uuid4()),
        "dt": datetime.now().isoformat(),
        "text": str(uuid4()),
        "source_id": sources[0].id
    }
    resp = await async_client.post(f"/publications/", json=create_data)
    assert resp.status_code == 201
    resp_data = resp.json()
    publication_1_id = resp_data["id"]

    create_data_2 = {
        "url": str(uuid4()),                        # Different url
        "dt": datetime.now().isoformat(),           # The same date, but different time
        "text": create_data["text"],                # The same text
        "source_id": sources[1].id                  # Different source
    }
    assert create_data["dt"] != create_data_2["dt"]

    resp = await async_client.post(f"/publications/", json=create_data_2)
    assert resp.status_code == 200  # Was not added

    publication_data = resp.json()
    assert len(publication_data) == 7  # Make sure we check all response model fields
    assert publication_data["id"] == publication_1_id   # first publication ID
    assert publication_data["url"] == create_data["url"]
    assert len(publication_data["hash"]) == 32
    assert publication_data["preview"] == create_data["text"][:150]
    assert publication_data["source_id"] == create_data["source_id"]
    assert publication_data["dt"] == create_data["dt"]
    assert publication_data["processed"] == False


async def test_publication_create_category_doesnt_exist(async_client: TestClient):
    create_data = {
        "url": str(uuid4()),
        "dt": datetime.now().isoformat(),
        "text": str(uuid4()),
        "source_id": random.randint(1_000_000, 10_000_000)
    }
    resp = await async_client.post(f"/publications/", json=create_data)
    assert resp.status_code == 404
    resp_json = resp.json()
    assert resp_json["detail"].find(str(create_data["source_id"])) >= 0