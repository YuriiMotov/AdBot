from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models.keyword import KeywordInDB

pytestmark = pytest.mark.asyncio(scope="module")


async def test_keyword_create(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    create_data = {
        "word": str(uuid4())
    }
    resp = await async_client.post(f"/keywords/", json=create_data)
    assert resp.status_code == 201
    kw_data = resp.json()
    assert "id" in kw_data
    assert kw_data["word"] == create_data["word"]

    session: AsyncSession
    async with async_session_maker() as session:
        kw = await session.get(KeywordInDB, kw_data["id"])
    
    assert kw is not None
    assert kw.word == create_data["word"]
    assert kw_data["id"] == kw.id


async def test_keyword_create_too_short(
    async_client: TestClient,
):
    create_data = {
        "word": str(uuid4())[0]
    }
    resp = await async_client.post(f"/keywords/", json=create_data)
    assert resp.status_code == 422


async def test_keyword_create_duplicated(
    async_client: TestClient,
    async_session_maker: async_sessionmaker
):
    word = str(uuid4())
    session: AsyncSession
    async with async_session_maker() as session:
        kw = KeywordInDB(word=word)
        session.add(kw)
        await session.commit()

    create_data = {
        "word": word
    }
    resp = await async_client.post(f"/keywords/", json=create_data)
    assert resp.status_code == 200
    kw_data = resp.json()

    session: AsyncSession
    async with async_session_maker() as session:
        st = select(KeywordInDB).where(KeywordInDB.word == word)
        kws = (await session.scalars(st)).all()

        assert len(kws) == 1
        assert kws[0].id == kw_data["id"]


async def test_keyword_create_case_insensitive(
    async_client: TestClient,
):
    word = f'aA_{uuid4()}'
    create_data = {
        "word": word
    }
    resp = await async_client.post(f"/keywords/", json=create_data)
    assert resp.status_code == 201
    kw_data = resp.json()
    assert kw_data["word"] == word.lower()


async def test_keyword_create_duplicated_case_insensitive(
    async_client: TestClient,
):
    word_1 = f'aA_{uuid4()}'
    word_2 = word_1.title()
    create_data_1 = {
        "word": word_1
    }
    resp1 = await async_client.post(f"/keywords/", json=create_data_1)
    assert resp1.status_code == 201
    resp1_json = resp1.json()

    create_data_2 = {
        "word": word_2
    }
    resp2 = await async_client.post(f"/keywords/", json=create_data_2)
    assert resp2.status_code == 200
    resp2_json = resp2.json()

    assert resp2_json["word"] == resp1_json["word"]
    assert resp2_json["id"] == resp1_json["id"]