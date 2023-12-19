import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import ResStat, create_user, create_keywords_list, get_multimage_results
from models.user import UserInDB, UserOutput

pytestmark = pytest.mark.asyncio(scope="module")


async def test_get_user_keywords_user_doesnt_exist(
    async_client: TestClient,
):
    """ User doesn't exist - return empty results """

    user_uuid = str(uuid4())

    resp = await async_client.get(f"/users/{user_uuid}/keywords/")
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["total_results"] == 0
    assert resp_data["total_pages"] == 1
    assert resp_data["current_page"] == 1
    assert len(resp_data["results"]) == 0


@pytest.mark.parametrize(
    "user_keywords_cnt,limit",
    [(0, None), (1, None), (5, None), (100, None), (5, 2)]
)
async def test_get_user_keywords_empty(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
    user_keywords_cnt: int,
    limit: int
):
    """ User with not empty keyword list """

    # Create user and keywords, add some keywords to user's list
    keywords = await create_keywords_list(
        async_session_maker,
        count=(user_keywords_cnt * 2)
    )
    user = await create_user(
        async_session_maker, defaults=True, keywords=keywords[:user_keywords_cnt]
    )

    # Request user's keyword list
    keywords_results = get_multimage_results(
        async_client=async_client,
        base_url=f"/users/{user.uuid}/keywords/",
        limit=limit
    )
    user_unique_words = {keyword["word"] async for keyword in keywords_results}

    assert len(user_unique_words) == user_keywords_cnt
