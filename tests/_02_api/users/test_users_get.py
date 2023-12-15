import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_user
from models.user import UserInDB, UserOutput

pytestmark = pytest.mark.asyncio(scope="module")


async def test_get_user_not_exist(async_client: TestClient):
    user_uuid = uuid4()

    resp = await async_client.get(f"/users/{user_uuid}/")
    assert resp.status_code == 404


async def test_get_user_defaults(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Get user with all optional fields equal to default values """
    user = await create_user(async_session_maker, defaults=True)

    resp = await async_client.get(f"/users/{user.uuid}/")
    assert resp.status_code == 200
    resp_json = resp.json()
    assert len(resp_json) == 5  # Make sure we check all response model fields
    assert resp_json["uuid"] == str(user.uuid)
    assert resp_json["name"] == user.name
    assert resp_json["telegram_id"] == None
    assert resp_json["active"] == True
    assert resp_json["lang"] == "en"
    

async def test_get_user_non_defaults(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Get user with all optional fields not equal to default values """
    user = await create_user(
        async_session_maker,
        defaults=False,
        active=False,
        lang="ru"
    )

    resp = await async_client.get(f"/users/{user.uuid}/")
    assert resp.status_code == 200
    resp_json = resp.json()
    assert len(resp_json) == 5  # Make sure we check all response model fields
    assert resp_json["uuid"] == str(user.uuid)
    assert resp_json["name"] == user.name
    assert resp_json["telegram_id"] == user.telegram_id
    assert resp_json["active"] == user.active
    assert resp_json["lang"] == user.lang

    

