from datetime import datetime
import random
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models.publication import PublicationInDB
from tests.helpers import create_publication

pytestmark = pytest.mark.asyncio(scope="module")


async def test_publication_delete(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Successfull scenario """

    publication = await create_publication(async_client, async_session_maker)

    resp = await async_client.delete(f"/publications/{publication['id']}/")
    assert resp.status_code == 200

    session: AsyncSession
    async with async_session_maker() as session:
        publication = await session.get(PublicationInDB, publication["id"])
    
    assert publication is None


async def test_publication_delete_not_exists(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    """ Publication doesn't exist """
    publication_id = random.randint(1_000_000, 10_000_000)

    resp = await async_client.delete(f"/publications/{publication_id}/")
    assert resp.status_code == 404

    session: AsyncSession
    async with async_session_maker() as session:
        publication = await session.get(PublicationInDB, publication_id)
    
    assert publication is None





