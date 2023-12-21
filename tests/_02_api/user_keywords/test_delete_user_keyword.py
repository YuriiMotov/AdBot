import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from models.keyword import KeywordInDB
from models.users_keywords_links import UserKeywordLink
from tests.helpers import (
    create_user, create_keywords_list, get_multipage_results,
    create_categories_list, add_user_keywords, get_user_keywords
)

pytestmark = pytest.mark.asyncio(scope="module")


async def test_delete_user_keyword(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        Keyword exists in user's list
    """

    user = await create_user(async_session_maker, defaults=True)
    categories = await create_categories_list(async_session_maker, count=1)
    keywords = await create_keywords_list(async_session_maker, count=1)
    await add_user_keywords(
        async_session_maker, user=user, category_id=categories[0].id, keywords=keywords
    )

    url = f"/users/{user.uuid}/categories/{categories[0].id}/keywords/" \
                f"?word={keywords[0].word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data.find("deleted") >= 0

    user_keywords = await get_user_keywords(
        async_session_maker, user_uuid=user.uuid, category_id=categories[0].id
    )
    assert len(user_keywords) == 0


async def test_delete_user_keyword_not_exist_in_user_list(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        Keyword doesn't exist in user's list
    """

    user = await create_user(async_session_maker, defaults=True)
    categories = await create_categories_list(async_session_maker, count=1)
    keywords = await create_keywords_list(async_session_maker, count=2)
    await add_user_keywords(
        async_session_maker,
        user=user,
        category_id=categories[0].id,
        keywords=keywords[:1]           # Add to user's list only first keyword
    )

    url = f"/users/{user.uuid}/categories/{categories[0].id}/keywords/" \
                f"?word={keywords[1].word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data.find("was not in") >= 0

    user_keywords = await get_user_keywords(
        async_session_maker, user_uuid=user.uuid, category_id=categories[0].id
    )
    assert len(user_keywords) == 1, "doesn't affect other keywords of this user"


async def test_delete_user_keyword_not_exist_in_table(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        Keyword doesn't exist in 'keywords' table
    """

    user = await create_user(async_session_maker, defaults=True)
    categories = await create_categories_list(async_session_maker, count=1)
    keywords = await create_keywords_list(async_session_maker, count=1)
    await add_user_keywords(
        async_session_maker,
        user=user,
        category_id=categories[0].id,
        keywords=keywords
    )
    word = f"kw_{uuid4()}"

    url = f"/users/{user.uuid}/categories/{categories[0].id}/keywords/" \
                f"?word={word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data.find("was not in") >= 0

    user_keywords = await get_user_keywords(
        async_session_maker, user_uuid=user.uuid, category_id=categories[0].id
    )
    assert len(user_keywords) == 1, "doesn't affect other keywords of this user"


async def test_delete_user_keyword_in_different_category(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        Keyword is in user's list but in different category
    """

    user = await create_user(async_session_maker, defaults=True)
    categories = await create_categories_list(async_session_maker, count=2)
    keywords = await create_keywords_list(async_session_maker, count=1)
    await add_user_keywords(
        async_session_maker,
        user=user,
        category_id=categories[0].id,
        keywords=keywords
    )

    url = f"/users/{user.uuid}/categories/{categories[1].id}/keywords/" \
                f"?word={keywords[0].word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data.find("was not in") >= 0

    user_keywords = await get_user_keywords(
        async_session_maker, user_uuid=user.uuid, category_id=categories[0].id
    )
    assert len(user_keywords) == 1, "doesn't affect other keywords of this user"


async def test_delete_user_keyword_user_not_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        User doesn't exist
    """

    user_uuid = uuid4()
    categories = await create_categories_list(async_session_maker, count=1)
    word = f"kw_{uuid4()}"

    url = f"/users/{user_uuid}/categories/{categories[0].id}/keywords/" \
                f"?word={word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 404
    resp_data = resp.json()
    assert resp_data["detail"].find(str(user_uuid)) >= 0


async def test_delete_user_keyword_category_not_exist(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
):
    """
        Delete keyword from user's list.
        Category doesn't exist
    """

    user = await create_user(async_session_maker, defaults=True)
    category_id = random.randint(1_000_000, 10_000_000)
    word = f"kw_{uuid4()}"

    url = f"/users/{user.uuid}/categories/{category_id}/keywords/" \
                f"?word={word}"
    resp = await async_client.delete(url)
    assert resp.status_code == 404
    resp_data = resp.json()
    assert resp_data["detail"].find(str(category_id)) >= 0

