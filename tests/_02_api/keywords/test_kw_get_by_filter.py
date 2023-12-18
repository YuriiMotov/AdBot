from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_keywords_list, get_keywords_count_by_filter

pytestmark = pytest.mark.asyncio(scope="module")


async def test_keywords_get_by_filter_strict(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    keywords = await create_keywords_list(async_session_maker, count=1)
    resp = await async_client.get(f"/keywords/?word={keywords[0].word}")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 1
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 1
    assert resp_data["results"][0]["word"] == keywords[0].word


async def test_keywords_get_by_filter_empty_str_filter(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    keywords = await create_keywords_list(async_session_maker, count=20)
    keywords_total = await get_keywords_count_by_filter(async_session_maker)
    resp = await async_client.get(f"/keywords/?word=")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == keywords_total


async def test_keywords_get_by_filter_none_filter(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    keywords = await create_keywords_list(async_session_maker, count=20)
    keywords_total = await get_keywords_count_by_filter(async_session_maker)

    resp = await async_client.get(f"/keywords/")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == keywords_total


async def test_keywords_get_by_filter_empty_res(
    async_client: TestClient,
):
    keyword = str(uuid4())
    resp = await async_client.get(f"/keywords/?word={keyword}")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


@pytest.mark.parametrize("limit", [None, 1, 2, 100])
async def test_keywords_get_multipage_default_limit(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    limit
):
    """ Request all words page by page, count unique words in results """

    keywords = await create_keywords_list(async_session_maker, count=40)
    keywords_total = await get_keywords_count_by_filter(async_session_maker)

    url = f"/keywords/"
    if limit:
        url += f"?limit={limit}"
    resp = await async_client.get(url)
    assert resp.status_code == 200

    resp_data = resp.json()
    assert resp_data["total_results"] == keywords_total
    assert resp_data["current_page"] == 1

    unique_words = {keyword["word"] for keyword in resp_data["results"]}
    
    total_pages = resp_data["total_pages"]
    assert total_pages > 1
    
    for page in range(2, total_pages + 1):
        url = f"/keywords/?page={page}"
        if limit:
            url += f"&limit={limit}"
        resp = await async_client.get(url)
        assert resp.status_code == 200
        resp_data = resp.json()
        page_unique_words = {keyword["word"] for keyword in resp_data["results"]}
        unique_words.update(page_unique_words)
    
    assert len(unique_words) == keywords_total



