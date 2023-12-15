import random
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

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
