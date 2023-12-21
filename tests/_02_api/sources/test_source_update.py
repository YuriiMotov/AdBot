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


@pytest.mark.parametrize("source_type", [SourceType.telegram, SourceType.facebook])
async def test_source_update(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    source_type: SourceType
):
    categories = await create_categories_list(async_session_maker, count=2)
    sources = await create_sources_list(
        async_session_maker,
        count=1,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    new_source_type = SourceType.facebook if (source_type == SourceType.telegram) else SourceType.telegram
    update_data = {
        "title": str(uuid4()),
        "type": new_source_type,
        "source_info": f"info_{uuid4()}",
        "category_id": categories[1].id
    }
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)
    assert resp.status_code == 201
    source_data = resp.json()
    assert len(source_data) == 5  # Make sure we check all response model fields
    assert source_data["id"] == sources[0].id
    assert source_data["title"] == update_data["title"]
    assert source_data["type"] == update_data["type"]
    assert source_data["source_info"] == update_data["source_info"]
    assert source_data["category_id"] == update_data["category_id"]

    session: AsyncSession
    async with async_session_maker() as session:
        source = await session.get(SourceInDB, source_data["id"])
        assert source is not None


async def test_source_update_empty_data(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    categories = await create_categories_list(async_session_maker, count=2)
    sources = await create_sources_list(
        async_session_maker,
        count=1,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    update_data = {}
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)
    assert resp.status_code == 201
    source_data = resp.json()
    assert len(source_data) == 5  # Make sure we check all response model fields
    assert source_data["id"] == sources[0].id
    assert source_data["title"] == sources[0].title
    assert source_data["type"] == sources[0].type
    assert source_data["source_info"] == sources[0].source_info
    assert source_data["category_id"] == sources[0].category_id



async def test_source_update_dupliacted_title(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=2,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    update_data = {
        "title": sources[1].title
    }
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)
    
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "SOURCE_TITLE_ALREADY_EXISTS"


async def test_source_update_dupliacted_info(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=2,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    update_data = {
        "source_info": sources[1].source_info
    }
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)

    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "SOURCE_INFO_ALREADY_EXISTS"



async def test_source_update_dupliacted_title_and_info(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=2,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    update_data = {
        "title": sources[1].title,
        "source_info": sources[1].source_info
    }
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)

    assert resp.status_code == 400
    resp_json = resp.json()
    assert len(resp_json["detail"]["errors"]) == 2
    errors = [
        resp_json["detail"]["errors"][0]["code"],
        resp_json["detail"]["errors"][1]["code"]
    ]
    assert "SOURCE_INFO_ALREADY_EXISTS" in errors
    assert "SOURCE_TITLE_ALREADY_EXISTS" in errors


async def test_source_update_category_doesnt_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    sources = await create_sources_list(
        async_session_maker,
        count=2,
        source_type=SourceType.telegram,
        category_id=categories[0].id,
    )
    update_data = {
        "category_id": random.randint(1_000_000, 10_000_000)
    }
    resp = await async_client.patch(f"/sources/{sources[0].id}/", json=update_data)

    assert resp.status_code == 404
    resp_json = resp.json()
    assert resp_json["detail"].find(str(update_data["category_id"])) >= 0


