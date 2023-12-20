import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import (
    create_user, create_keywords_list, get_multimage_results,
    create_categories_list, add_user_keywords
)

pytestmark = pytest.mark.asyncio(scope="module")


async def test_get_user_keywords_user_doesnt_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """ User doesn't exist - return empty results """

    user_uuid = str(uuid4())
    cats = await create_categories_list(async_session_maker, count=1)

    resp = await async_client.get(f"/users/{user_uuid}/categories/{cats[0].id}/keywords/")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


async def test_get_user_keywords_category_doesnt_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """ Category doesn't exist - return empty results """

    user = await create_user(async_session_maker, defaults=True)
    non_existed_cat_id = random.randint(1_000_000, 10_000_000)

    url = f"/users/{user.uuid}/categories/{non_existed_cat_id}/keywords/"
    resp = await async_client.get(url)
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


@pytest.mark.parametrize(
    "cats_cnt,keywords_cnt,limit",
    [(1, 0, None), (2, 1, None), (2, 5, None), (2, 50, None), (2, 5, 2)]
)
async def test_get_user_keywords(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    cats_cnt: int,
    keywords_cnt: int,
    limit: int
):
    """ User keywords """

    # Create user and keywords, add keywords to user's list
    user = await create_user(async_session_maker, defaults=True)
    cats = await create_categories_list(async_session_maker, count=cats_cnt)
    keywords = {}
    for cat in cats:
        keywords[cat.id] = await create_keywords_list(
            async_session_maker, count=keywords_cnt
        )
        await add_user_keywords(
            async_session_maker, user=user, category_id=cat.id, keywords=keywords[cat.id]
        )

    # Request user's keyword list
    for cat in cats:
        keywords_results = get_multimage_results(
            async_client=async_client,
            base_url=f"/users/{user.uuid}/categories/{cat.id}/keywords/",
            limit=limit
        )
        unique_words = {keyword["word"] async for keyword in keywords_results}

        assert len(unique_words) == keywords_cnt
