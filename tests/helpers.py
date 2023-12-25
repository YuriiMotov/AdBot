from dataclasses import dataclass
from datetime import datetime
import random
from typing import Any, Optional, AsyncGenerator
from uuid import uuid4
from fastapi.testclient import TestClient

from sqlalchemy import and_, delete, func, select, insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlmodel import col
from common_types import SourceType
from models.category import CategoryInDB

from models.keyword import KeywordInDB
from models.publication import PublicationInDB
from models.source import SourceInDB
from models.user import UserInDB
from models.users_keywords_links import UserKeywordLink


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
) -> UserInDB:
    user_uuid = uuid4()
    if defaults:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}",
        )
    else:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}",
            telegram_id=random.randint(1, 1_000_000),
            active=active,
            lang=lang,
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
    word_filter: Optional[str] = None,
    strict: bool = True
) -> int:
    session: AsyncSession
    async with async_session_maker() as session:
        st = select(func.count(KeywordInDB.id))
        if word_filter:
            if strict:
                st = st.where(KeywordInDB.word == word_filter)
            else:
                st = st.where(col(KeywordInDB.word).like(word_filter))
        return await session.scalar(st)


async def add_user_keywords(
    async_session_maker: async_sessionmaker,
    *,
    user: UserInDB,
    category_id: int,
    keywords: list[KeywordInDB]
):
    if not keywords:
        return
    insert_data = []
    for kw in keywords:
        insert_data.append({
            "user_uuid": user.uuid,
            "keyword_id": kw.id,
            "category_id": category_id
        })

    session: AsyncSession
    async with async_session_maker() as session:
        await session.execute(insert(UserKeywordLink), insert_data)
        await session.commit()


async def get_user_keywords(
    async_session_maker: async_sessionmaker,
    *,
    user_uuid: int,
    category_id: int,
):
    async with async_session_maker() as session:
        st = (
            select(KeywordInDB)
                .select_from(UserKeywordLink)
                .join(KeywordInDB)
                .where(
                    and_(
                        UserKeywordLink.user_uuid == user_uuid,
                        UserKeywordLink.category_id == category_id
                    )
                )
        )
        return (await session.scalars(st)).all()


async def create_categories_list(
    async_session_maker: async_sessionmaker,
    *,
    count: int = 10,
    prefix: Optional[str] = None
) -> list[CategoryInDB]:
    if count == 0:
        return []

    if prefix is None:
        prefix = f"{uuid4()}_"

    session: AsyncSession
    async with async_session_maker() as session:
        res = await session.scalars(
            insert(CategoryInDB).returning(CategoryInDB),
            [{"name":f"{prefix}{i}"} for i in range(count)]
        )
        await session.commit()
    return res.all()


async def get_categories_count_by_filter(
    async_session_maker: async_sessionmaker,
    *,
    name_filter: Optional[str] = None,
    strict: bool = True
) -> int:
    session: AsyncSession
    async with async_session_maker() as session:
        st = select(func.count(CategoryInDB.id))
        if name_filter:
            if strict:
                st = st.where(CategoryInDB.name == name_filter)
            else:
                st = st.where(col(CategoryInDB.name).like(name_filter))
        return await session.scalar(st)


async def create_sources_list(
    async_session_maker: async_sessionmaker,
    *,
    count: int = 10,
    source_type: SourceType = SourceType.telegram,
    category_id: Optional[int] = None,
    prefix: Optional[str] = None
) -> list[SourceInDB]:
    if count == 0:
        return []

    if prefix is None:
        prefix = f"{uuid4()}_"

    if category_id is None:
        categories = await create_categories_list(async_session_maker, count=1)
        category_id = categories[0].id

    insert_data = []
    for i in range(count):
        insert_data.append({
            "title": f"{prefix}{i}",
            "type": source_type,
            "source_info": f"{prefix}{i}",
            "category_id": category_id
        })

    session: AsyncSession
    async with async_session_maker() as session:
        res = await session.scalars(
            insert(SourceInDB).returning(SourceInDB),
            insert_data
        )
        await session.commit()
    return res.all()


async def create_publication(
    async_client: TestClient,
    async_session_maker: async_sessionmaker,
) -> dict:
    sources = await create_sources_list(async_session_maker, count=1)
    create_data = {
        "url": str(uuid4()),
        "dt": datetime.now().isoformat(),
        "text": str(uuid4()),
        "source_id": sources[0].id
    }
    resp = await async_client.post(f"/publications/", json=create_data)
    assert resp.status_code == 201
    return resp.json()


async def delete_all_objects(
    async_session_maker: async_sessionmaker,
    object_model: type
):
    session: AsyncSession
    async with async_session_maker() as session:
        await session.execute(delete(object_model))
        await session.commit()


class ResStat():
    total_pages: int
    total_results: int
    def __init__(self):
        self.total_pages = 1
        self.total_results = 0


async def get_multipage_results(
    async_client: TestClient,
    base_url: str,
    *,
    query_params: dict[str, Any] = None,
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
    params = query_params.copy() if query_params else {}

    # Request first page and iterate throught results
    if limit:
        params["limit"] = limit

    resp = await async_client.get(base_url, params=params)
    # if resp.status_code != 200:
    #     print(resp.status_code)
    #     print(resp.json())
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
        params["page"] = page

        resp = await async_client.get(base_url, params=params)
        # if resp.status_code != 200:
        #     print(resp.status_code)
        #     print(resp.json())
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


