from datetime import datetime
import random
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from common_types import SourceType
from models.category import CategoryInDB
from models.source import SourceInDB

from models.user import UserInDB
from models.publication import PublicationInDB
from models.users_publications_links import UserPublicationLink


pytestmark = pytest.mark.asyncio(scope="module")


async def test_user_publication_unique_constraint(
    async_session_maker: async_sessionmaker
):
    session: AsyncSession
    async with async_session_maker() as session:
        user = UserInDB(uuid=uuid4(), name=f"user_{uuid4()}")
        session.add(user)
        await session.commit()
        # await session.refresh(user)

        category = CategoryInDB(name=f"cat_{uuid4()}")
        session.add(category)
        await session.commit()
        # await session.refresh(category)

        source = SourceInDB(
            title=f"source_{uuid4()}",
            type=SourceType.telegram,
            source_info=f"info_{uuid4()}",
            category_id=category.id
        )
        session.add(source)
        await session.commit()
        # await session.refresh(source)

        publication = PublicationInDB(
            url=f"url_{uuid4()}",
            dt=datetime.now(),
            source_id=source.id,
            preview=f"preview_{uuid4()}",
            hash='0' * 32
        )
        session.add(publication)
        await session.commit()
        # await session.refresh(publication)

        user_pub_link = UserPublicationLink(
            user_uuid=user.uuid,
            publication_id=publication.id
        )
        session.add(user_pub_link)
        await session.commit()

        user_pub_link2 = UserPublicationLink(
            user_uuid=user.uuid,
            publication_id=publication.id
        )
        session.add(user_pub_link2)
        with pytest.raises(IntegrityError):
            await session.commit()
