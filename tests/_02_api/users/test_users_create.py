import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.helpers import create_user
from models.user import UserCreate

pytestmark = pytest.mark.asyncio(scope="module")


async def test_create_user_min_data(async_client: TestClient):
    """ Create user with only required data (uuid and name) """
    
    user_uuid = uuid4()
    create_data = {
        "name": f"user:{user_uuid}"
    }

    resp = await async_client.post(f"/users/{user_uuid}/", json=create_data)
    assert resp.status_code == 201
    user = resp.json()
    assert len(user) == 5  # Make sure we check all response model fields
    assert user["uuid"] == str(user_uuid)
    assert user["name"] == create_data["name"]
    assert user["telegram_id"] == None
    assert user["active"] == True
    assert user["lang"] == "en"


async def test_create_user_max_data(async_client: TestClient):
    """ Create a user with all the fields specified """
    
    user_uuid = uuid4()
    create_data = {
        "name": f"user:{user_uuid}",
        "telegram_id": random.randint(1, 1_000_000)
    }

    assert len(create_data) == len(UserCreate.model_fields) # Make sure all fields are set

    resp = await async_client.post(f"/users/{user_uuid}/", json=create_data)
    assert resp.status_code == 201
    user = resp.json()
    assert user["uuid"] == str(user_uuid)
    assert user["name"] == create_data["name"]
    assert user["telegram_id"] == create_data["telegram_id"]

    
async def test_create_user_optional_none(async_client: TestClient):
    """ Create user with all optional fields set to `None` """
    
    user_uuid = uuid4()
    create_data = {
        "name": f"user:{user_uuid}",
        "telegram_id": None
    }

    assert len(create_data) == len(UserCreate.model_fields) # Make sure all fields are set

    resp = await async_client.post(f"/users/{user_uuid}/", json=create_data)
    assert resp.status_code == 201
    user = resp.json()
    assert user["uuid"] == str(user_uuid)
    assert user["name"] == create_data["name"]
    assert user["telegram_id"] == None


async def test_create_user_extra_fields(async_client: TestClient):
    """
        Create user with extra fields in input data.
        These extra fields should be ignored
    """
    user_uuid = uuid4()
    create_data = {
        "name": f"user:{user_uuid}",
        "telegram_id": None,
        "uuid": str(uuid4()),   # Extra field
        "active": False,        # Extra field
        "lang": "ru"            # Extra field
    }

    resp = await async_client.post(f"/users/{user_uuid}/", json=create_data)
    assert resp.status_code == 201
    user = resp.json()
    assert user["uuid"] == str(user_uuid)       # Wasn't changed
    assert user["name"] == create_data["name"]
    assert user["telegram_id"] == None
    assert user["active"] == True               # Wasn't changed
    assert user["lang"] == "en"                 # Wasn't changed

    
async def test_create_user_duplicate_uuid(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Create user with duplicated uuid """

    user1 = await create_user(async_session_maker)

    create_data = {
        "name": f"user:{uuid4()}"
    }

    resp = await async_client.post(f"/users/{user1.uuid}/", json=create_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "DUPLICATE_UUID"
    

async def test_create_user_duplicate_name(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Create user with duplicated name """

    user1 = await create_user(async_session_maker)

    create_data = {
        "name": user1.name
    }
    user2_uuid = uuid4()

    resp = await async_client.post(f"/users/{user2_uuid}/", json=create_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "USER_NAME_ALREADY_USED"


async def test_create_user_duplicate_telegram_id(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Create user with duplicated Telegram ID """

    user1 = await create_user(async_session_maker)

    create_data = {
        "name": f"user:{uuid4()}",
        "telegram_id": user1.telegram_id
    }
    user2_uuid = uuid4()

    resp = await async_client.post(f"/users/{user2_uuid}/", json=create_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert resp_json["detail"]["errors"][0]["code"] == "TELEGRAM_ID_ALREADY_USED"


async def test_create_user_duplicate_all(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Create user with duplicated uuid, name and Telegram ID """

    user1 = await create_user(async_session_maker)

    create_data = {
        "name": user1.name,
        "telegram_id": user1.telegram_id
    }
    user2_uuid = user1.uuid

    resp = await async_client.post(f"/users/{user2_uuid}/", json=create_data)
    assert resp.status_code == 400
    resp_json = resp.json()
    assert len(resp_json["detail"]["errors"]) == 3



