import random
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select, insert
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
    lang="en"
) -> UserInDB:
    user_uuid = uuid4()
    if defaults:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}"
        )
    else:
        user = UserInDB(
            uuid=user_uuid,
            name=f"user:{user_uuid}",
            telegram_id=random.randint(1, 1_000_000),
            active=active,
            lang=lang
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

                                   