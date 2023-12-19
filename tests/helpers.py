from dataclasses import dataclass
import random
from typing import Any, Optional, AsyncGenerator
from uuid import uuid4
from fastapi.testclient import TestClient

from sqlalchemy import delete, func, select, insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlmodel import col

from models.keyword import KeywordInDB
from models.user import UserInDB


async def get_unique_telegram_id(
    async_session_maker: async_sessionmaker
) -> int:
    async with async_session_maker() as session:
        i = 5
        while i > 0:
            telegram_id = random.randint(1, 1_000_000)
            st = select(UserInDB).where(UserInDB.telegram_id==telegram_id)
            user = await session.scalar(st)
            if user is None:
                return telegram_id
            i -= 1
    raise Exception("Couldn't generate unique telegram id")


async def create_user(
    async_session_maker: async_sessionmaker,
    *,
    defaults=False,
    active=True,
    lang="en",
    keywords: list[KeywordInDB] = None
) -> UserInDB:
    if keywords is None:
        keywords = []
    user_uuid = uuid4()
    if defaults:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}",
            keywords=keywords
        )
    else:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}",
            telegram_id=random.randint(1, 1_000_000),
            active=active,
            lang=lang,
            keywords=keywords
        )
    async with async_session_maker() as session:
        session.add(user)
        await session.commit()

    return user


async def create_keywords_list(
    async_session_maker: async_sessionmaker,
    *,
    count: int = 10,
    prefix: Optional[str] = None
) -> list[KeywordInDB]:
    if count == 0:
        return []

    if prefix is None:
        prefix = f"{uuid4()}_"

    session: AsyncSession
    async with async_session_maker() as session:
        res = await session.scalars(
            insert(KeywordInDB).returning(KeywordInDB),
            [{"word":f"{prefix}{i}"} for i in range(count)]
        )
        await session.commit()
    return res.all()


async def get_keywords_count_by_filter(
    async_session_maker: async_sessionmaker,
    *,
    filter: Optional[str] = None,
    strict: bool = True
) -> int:
    session: AsyncSession
    async with async_session_maker() as session:
        st = select(func.count(KeywordInDB.id))
        if filter:
            if strict:
                st = st.where(KeywordInDB.word == filter)
            else:
                st = st.where(col(KeywordInDB.word).like(filter))
        return await session.scalar(st)


async def delete_all_keywords(
    async_session_maker: async_sessionmaker,
) -> int:
    session: AsyncSession
    async with async_session_maker() as session:
        await session.execute(delete(KeywordInDB))
        await session.commit()


class ResStat():
    total_pages: int
    total_results: int
    def __init__(self):
        self.total_pages = 1
        self.total_results = 0


async def get_multimage_results(
    async_client: TestClient,
    base_url: str,
    limit: Optional[int] = None,
    resp_stat: Optional[ResStat] = None
) -> AsyncGenerator[dict[str, Any], None]:
    """
        Iterates throught pages and yields all items from results. 
        Also checks pagination.
    """

    # Initialization
    if resp_stat is None:
        resp_stat = ResStat()
    url = base_url
    url_connector = "?" if (base_url.find("?") < 0) else "&"

    # Request first page and iterate throught results
    if limit:
        url += f"{url_connector}limit={limit}"
    resp = await async_client.get(url)
    assert resp.status_code == 200, "Request error (status_code != 200)"
    resp_data = resp.json()
    for item in resp_data["results"]:
        resp_stat.total_results += 1
        yield item

    total_pages = resp_data["total_pages"]
    total_results = resp_data["total_results"]

    # Request other pages and iterate throught results    
    for page in range(2, total_pages + 1):
        resp_stat.total_pages += 1
        url = f"{base_url}{url_connector}page={page}"
        if limit:
            url += f"&limit={limit}"
        resp = await async_client.get(url)
        assert resp.status_code == 200, "Request error (status_code != 200)"
        resp_data = resp.json()
        assert resp_data["total_pages"] == total_pages, "Pagination error, " \
                                                    "different `total_pages` field value"
        assert resp_data["total_results"] == total_results, "Pagination error, " \
                                                    "different `total_results` field value"
        for item in resp_data["results"]:
            resp_stat.total_results += 1
            yield item
    
    # compare the stated amount of pages and results and the actual data
    assert resp_stat.total_pages == total_pages, "Pagination error, " \
                                                        "wrong `total_pages` field value"
    assert resp_stat.total_results == total_results, "Pagination error, " \
                                                        "wrong `total_results` field value"


