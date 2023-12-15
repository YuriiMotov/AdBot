import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_user
from models.user import UserPatch, UserInDB

pytestmark = pytest.mark.asyncio(scope="module")


async def test_update_user_empty_data(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update user with empty data """

    user = await create_user(async_session_maker)

    resp = await async_client.patch(f"/users/{user.uuid}/", json={})
    assert resp.status_code == 200
    user_data = resp.json()
    assert len(user_data) == 5  # Make sure we check all response model fields
    assert user_data["uuid"] == str(user.uuid)
    assert user_data["name"] == user.name
    assert user_data["lang"] == user.lang
    assert user_data["telegram_id"] == user.telegram_id
    assert user_data["active"] == user.active


async def test_update_user_max_data(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update a user with all the fields specified """

    user = await create_user(async_session_maker)

    update_data = {
        "name": str(user.uuid),
        "telegram_id": random.randint(1, 1_000_000),
        "lang": "ru"
    }
    assert len(update_data) == len(UserPatch.model_fields)  # Make sure all fields are set

    resp = await async_client.patch(f"/users/{user.uuid}/",json=update_data)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["name"] == update_data["name"]
    assert user_data["telegram_id"] == update_data["telegram_id"]
    assert user_data["lang"] == update_data["lang"]


async def test_update_user_extra_data(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update a user with extra fields """

    user = await create_user(async_session_maker)

    update_data = {
        "name": str(user.uuid),
        "telegram_id": random.randint(1, 1_000_000),
        "lang": "ru",
        "active": (not user.active),    # extra field
        "uuid": str(uuid4()),           # extra field
        f"{uuid4()}": "something"       # extra field
    }

    resp = await async_client.patch(f"/users/{user.uuid}/", json=update_data)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["name"] == update_data["name"]
    assert user_data["telegram_id"] == update_data["telegram_id"]
    assert user_data["lang"] == update_data["lang"]
    assert user_data["active"] == user.active       # Wasn't changed
    assert user_data["uuid"] == str(user.uuid)      # Wasn't changed


async def test_update_user_duplicate_name(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update user with duplicated name """

    user1 = await create_user(async_session_maker)
    user2 = await create_user(async_session_maker)

    update_data = {
        "name": user1.name
    }
    resp = await async_client.patch(f"/users/{user2.uuid}/", json=update_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "USER_NAME_ALREADY_USED"


async def test_update_user_duplicate_telegram_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update user with duplicated Telegram ID """

    user1 = await create_user(async_session_maker)
    user2 = await create_user(async_session_maker)

    update_data = {
        "telegram_id": user1.telegram_id
    }

    resp = await async_client.patch(f"/users/{user2.uuid}/", json=update_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "TELEGRAM_ID_ALREADY_USED"


async def test_update_user_duplicate_name_and_telegram_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Update user with duplicated name and Telegram ID """

    user1 = await create_user(async_session_maker)
    user2 = await create_user(async_session_maker)

    update_data = {
        "name": user1.name,
        "telegram_id": user1.telegram_id
    }

    resp = await async_client.patch(f"/users/{user2.uuid}/", json=update_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert len(resp_json["detail"]["errors"]) == 2


async def test_update_user_wrong_uuid(
    async_client: TestClient,
):
    """ Update non existing user """

    user_uuid = uuid4()

    update_data = {}
    resp = await async_client.patch(f"/users/{user_uuid}/", json=update_data)
    assert resp.status_code == 404

