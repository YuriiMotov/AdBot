import asyncio
import pytest
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adbot.domain.services import AdBotServices
from adbot.domain import models


@pytest.mark.asyncio
async def test_create_user_add_keywords_many_tasks(config_url_adbot_srv: AdBotServices):

    # Helper functions

    async def create_user(
        ad_bot_srv: AdBotServices, user_tg_id: int, keywords: list[str]
    ) -> None:
        user = await ad_bot_srv.create_user_by_telegram_data(
            telegram_id=user_tg_id, telegram_name='asd'
        )

    async def add_keywords(
        ad_bot_srv: AdBotServices, user_tg_id: int, keywords: list[str]
    ) -> None:
        try:
            user = await ad_bot_srv.get_user_by_telegram_id(telegram_id=user_tg_id)
            for keyword in keywords:
                await asyncio.sleep(0.1)
                await ad_bot_srv.add_keyword(user.id, keyword)
        except Exception as e:
            raise
        finally:
            await asyncio.sleep(0.00001)

    # Data for test
    adbot_srv = config_url_adbot_srv
    TASKS_CNT = 50
    USER_TG_IDS = [i for i in range(100000, 100000 + TASKS_CNT)]
    TASKS_KEYWORDS = ['monitor', 'laptop', 'bicycle', 'PSP']

    # Create users
    tasks = []
    for user_tg_id in USER_TG_IDS:
        await create_user(adbot_srv, user_tg_id, TASKS_KEYWORDS)
    await asyncio.sleep(0.5)

    # Run TASKS_CNT parallel tasks and wait for the completion of all of them
    tasks = []
    for user_tg_id in USER_TG_IDS:
        tasks.append(
            asyncio.create_task(
                add_keywords(adbot_srv, user_tg_id, TASKS_KEYWORDS)
            )
        )
        await asyncio.sleep(0.000001)
    await asyncio.gather(*tasks)

    # Check results and DB consistency
    async with adbot_srv._db_pool() as session:
        session: AsyncSession
        
        # All the users exist in DB
        st = select(models.User)
        users = (await session.scalars(st)).all()
        users_set = {user.id for user in users}
        assert len(users_set) == TASKS_CNT

        # All the keywords exist in DB
        st = select(models.Keyword)
        keywords = (await session.scalars(st)).all()
        keywords_set = {keyword.id for keyword in keywords}
        assert len(keywords_set) == len(set(TASKS_KEYWORDS))

        # All the keywords are connected to all the users
        st = select(models.Keyword).options(selectinload(models.Keyword.users))
        keywords = (await session.scalars(st)).all()
        for keyword in keywords:
            assert len(keyword.users) == TASKS_CNT

