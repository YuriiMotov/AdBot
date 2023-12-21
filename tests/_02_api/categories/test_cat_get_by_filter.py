from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import (
    ResStat, create_categories_list, get_categories_count_by_filter, delete_all_categories, get_multipage_results
)

pytestmark = pytest.mark.asyncio(scope="module")


async def test_categories_get_by_filter_strict(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=1)
    resp = await async_client.get(f"/categories/?name={categories[0].name}")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 1
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 1
    assert resp_data["results"][0]["name"] == categories[0].name


async def test_categories_get_by_filter_empty_str_filter(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=20)
    categories_total = await get_categories_count_by_filter(async_session_maker)
    resp = await async_client.get(f"/categories/?name=")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == categories_total


async def test_categories_get_by_filter_none_filter(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    categories = await create_categories_list(async_session_maker, count=20)
    categories_total = await get_categories_count_by_filter(async_session_maker)

    resp = await async_client.get(f"/categories/")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == categories_total


async def test_categories_get_by_filter_empty_res(
    async_client: TestClient,
):
    category = str(uuid4())
    resp = await async_client.get(f"/categories/?name={category}")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


async def test_categories_get_by_filter_none_filter_empty_res(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    await delete_all_categories(async_session_maker)

    resp = await async_client.get(f"/categories/")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


@pytest.mark.parametrize("limit", [None, 1, 2, 100])
async def test_categories_get_multipage(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    limit
):
    """ Request all categories page by page, count unique names in results """

    categories = await create_categories_list(async_session_maker, count=40)
    categories_total = await get_categories_count_by_filter(async_session_maker)

    resp_stat = ResStat()
    categories_results = get_multipage_results(
        async_client=async_client,
        base_url="/categories/",
        resp_stat=resp_stat,
        limit=limit
    )

    unique_names = {category["name"] async for category in categories_results}
    
    assert len(unique_names) == categories_total

