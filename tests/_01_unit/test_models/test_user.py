import random
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.user import UserInDB
from tests.helpers import get_unique_telegram_id


pytestmark = pytest.mark.asyncio(scope="module")


async def test_telegram_id_unique_constraint(
    async_session_maker: async_sessionmaker
):
    """ Attemption to add user with diplicated telegram_id raises IntegrityError """

    telegram_id = await get_unique_telegram_id(async_session_maker)

    async with async_session_maker() as session:
        session.add(
            UserInDB(name=str(uuid4()), telegram_id=telegram_id)
        )
        await session.commit()

        with pytest.raises(IntegrityError):
            session.add(
                UserInDB(name=str(uuid4()), telegram_id=telegram_id)
            )
            await session.commit()



async def test_telegram_id_none_allowed(
    async_session_maker: async_sessionmaker
):
    """ telegram_id may be None """

    async with async_session_maker() as session:
        session.add(UserInDB(name=str(uuid4())))
        await session.commit()

        session.add(UserInDB(name=str(uuid4())))
        await session.commit()


