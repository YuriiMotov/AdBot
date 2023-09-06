import asyncio
from datetime import datetime, timedelta
import pytest

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from adbot.domain.services import AdBotServices, exc, IDLE_TIMEOUT_MINUTES
from adbot.domain import models
from adbot.domain import messagebus as mb
from adbot.domain import events


# ==============================================================================================
# helpers

def mock_method_raise_SQLAlchemyError(*arg, **kwarg):
    raise SQLAlchemyError()


def brake_sessionmaker(db_pool: sessionmaker):
    def broken_session_maker():
        session = db_pool()
        session.commit = mock_method_raise_SQLAlchemyError
        session.scalar = mock_method_raise_SQLAlchemyError
        session.scalars = mock_method_raise_SQLAlchemyError
        session.execute = mock_method_raise_SQLAlchemyError
        return session

    return broken_session_maker


# ==============================================================================================
# __init__

def test_adbot_init(in_memory_db_sessionmaker):
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)


def test_adbot_init_raises_exception_on_sql_error(in_memory_db_sessionmaker):
    db_pool_broken = brake_sessionmaker(in_memory_db_sessionmaker)

    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv = AdBotServices(db_pool_broken)


# ==============================================================================================
# get_user, create_user (by user_id, by telegram_id)

@pytest.mark.asyncio
async def test_get_user_by_user_id_returns_none_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.get_user_by_id(123)
    
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_tg_id_returns_none_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    
    assert user is None


@pytest.mark.asyncio
async def test_create_user_by_tg_data_returns_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    
    assert user is not None
    assert user.telegram_id == 123456789
    assert user.telegram_name == 'asd'


@pytest.mark.asyncio
async def test_create_user_by_tg_data_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv
    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit

    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    


@pytest.mark.asyncio
async def test_get_user_by_telegram_id_returns_correct_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    await adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.telegram_id == 123456789
    assert user1.telegram_name == 'asd'

    user2 = await adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.telegram_id == 987654321
    assert user2.telegram_name == 'dsa'


@pytest.mark.asyncio
async def test_get_user_by_user_id_returns_correct_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    created_user1 = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    created_user2 = await adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    selected_user = await adbot_srv.get_user_by_id(created_user1.id)
    assert selected_user is not None
    assert selected_user.id == created_user1.id
    assert selected_user.telegram_id == 123456789
    assert selected_user.telegram_name == 'asd'

    selected_user = await adbot_srv.get_user_by_id(created_user2.id)
    assert selected_user is not None
    assert selected_user.id == created_user2.id
    assert selected_user.telegram_id == 987654321
    assert selected_user.telegram_name == 'dsa'


# ==============================================================================================
# user subscription state management

@pytest.mark.asyncio
async def test_subscription_state_default_is_false(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.subscription_state is False

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is False


@pytest.mark.asyncio
async def test_set_subscription_state(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.subscription_state is False

    await adbot_srv.set_subscription_state(user.id, True)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is True

    await adbot_srv.set_subscription_state(user.id, False)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is False


@pytest.mark.asyncio
async def test_set_subscription_state_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user1.subscription_state is False
    user2 = await adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')
    assert user2.subscription_state is False

    await adbot_srv.set_subscription_state(user1.id, True)
    
    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.subscription_state is True
    user2 = await adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.subscription_state is False

    await adbot_srv.set_subscription_state(user2.id, True)
    await adbot_srv.set_subscription_state(user1.id, False)

    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.subscription_state is False
    user2 = await adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.subscription_state is True


@pytest.mark.asyncio
async def test_set_subscription_state_raises_exception_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        await adbot_srv.set_subscription_state(123, True)


@pytest.mark.asyncio
async def test_set_subscription_state_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.set_subscription_state(user.id, True)


# ==============================================================================================
# user forwarding state management

@pytest.mark.asyncio
async def test_forwarding_state_default_is_false(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.forwarding_state is False

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.forwarding_state is False


@pytest.mark.asyncio
async def test_set_forwarding_state(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.forwarding_state is False

    await adbot_srv.set_forwarding_state(user.id, True)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.forwarding_state is True

    await adbot_srv.set_forwarding_state(user.id, False)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.forwarding_state is False


@pytest.mark.asyncio
async def test_set_forwarding_state_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user1.forwarding_state is False
    user2 = await adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')
    assert user2.forwarding_state is False

    await adbot_srv.set_forwarding_state(user1.id, True)
    
    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.forwarding_state is True
    user2 = await adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.forwarding_state is False

    await adbot_srv.set_forwarding_state(user2.id, True)
    await adbot_srv.set_forwarding_state(user1.id, False)

    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.forwarding_state is False
    user2 = await adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.forwarding_state is True


@pytest.mark.asyncio
async def test_set_forwarding_state_raises_exception_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        await adbot_srv.set_forwarding_state(123, True)


@pytest.mark.asyncio
async def test_set_forwarding_state_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.set_forwarding_state(user.id, True)


# ==============================================================================================
# user menu closed state management

@pytest.mark.asyncio
async def test_menu_closed_state_default_is_true(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.menu_closed is True

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is True


@pytest.mark.asyncio
async def test_set_menu_closed_state(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.menu_closed is True

    await adbot_srv.set_menu_closed_state(user.id, False)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is False

    await adbot_srv.set_menu_closed_state(user.id, True)
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is True


@pytest.mark.asyncio
async def test_set_menu_closed_state_raises_exception_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        await adbot_srv.set_menu_closed_state(123, True)


@pytest.mark.asyncio
async def test_set_menu_closed_state_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.set_menu_closed_state(user.id, True)


# ==============================================================================================
# user idle timeout management

@pytest.mark.asyncio
async def test_onload_set_last_activity_dt_for_users_with_opened_menu(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 1)'))
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (222222, 0)'))
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (333333, 1)'))
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (444444, 0)'))
        session.commit()

    adbot_srv = AdBotServices(in_memory_db_sessionmaker)

    user_ids = [2, 4]
    user_ids_set = set(user_ids)
    assert len(adbot_srv._menu_activity_cache) == 2
    last_activity_dt_uids = list(adbot_srv._menu_activity_cache.keys())
    assert last_activity_dt_uids[0] in user_ids_set
    user_ids_set.remove(last_activity_dt_uids[0])
    assert last_activity_dt_uids[1] in user_ids_set
    user_ids_set.remove(last_activity_dt_uids[1])

    left_dt = datetime.now() - timedelta(seconds=1)
    assert left_dt <= adbot_srv._menu_activity_cache[user_ids[0]]['act_dt'] <= datetime.now()
    assert left_dt <= adbot_srv._menu_activity_cache[user_ids[1]]['act_dt'] <= datetime.now()


@pytest.mark.asyncio
async def test_get_is_idle_default_false(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 1)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == False


@pytest.mark.asyncio
async def test_get_is_idle_onload_on_user_with_opened_menu_returns_false(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 0)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == False


@pytest.mark.asyncio
async def test_get_is_idle_on_user_with_timeout_more_when_limit_returns_true(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 0)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)

    idle_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    adbot_srv._menu_activity_cache[1]['act_dt'] = idle_point
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == True


@pytest.mark.asyncio
async def test_get_is_idle_on_user_with_timeout_less_when_limit_returns_false(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 0)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)

    idle_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    adbot_srv._menu_activity_cache[1]['act_dt'] = idle_point + timedelta(seconds=1)
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == False


@pytest.mark.asyncio
async def test_get_reset_idle_timeout(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 0)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)

    idle_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    adbot_srv._menu_activity_cache[1]['act_dt'] = idle_point
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == True
    
    await adbot_srv.reset_idle_timeout(1)
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == False


@pytest.mark.asyncio
async def test_get_is_idle_on_user_with_timeout_more_when_limit_and_closed_menu_returns_false(in_memory_db_sessionmaker):
    with in_memory_db_sessionmaker() as session:
        session.execute(text(f'INSERT INTO user_account (telegram_id, menu_closed) VALUES (111111, 0)'))
        session.commit()
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)
    idle_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)
    adbot_srv._menu_activity_cache[1]['act_dt'] = idle_point
    await adbot_srv.set_menu_closed_state(1, True)
    assert (await adbot_srv.get_is_idle_with_opened_menu(1)) == False


# ==============================================================================================
# user keywords list management

@pytest.mark.asyncio
async def test_add_keyword(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = await adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1
    assert user.keywords[0].word == 'new_keyword'


@pytest.mark.asyncio
async def test_add_keyword_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit

    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.add_keyword(user.id, 'new_keyword')


@pytest.mark.asyncio
async def test_add_keyword_raises_exception_if_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        await adbot_srv.add_keyword(123456789, 'new_keyword')


@pytest.mark.asyncio
async def test_add_keyword_unique_in_user_list(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = await adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    res = await adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1
    assert user.keywords[0].word == 'new_keyword'


@pytest.mark.asyncio
async def test_add_keyword_word_is_unique_in_db(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    user2 = await adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    res = await adbot_srv.add_keyword(user1.id, 'new_keyword')
    assert res == True

    res = await adbot_srv.add_keyword(user2.id, 'new_keyword')
    assert res == True

    user1 = await adbot_srv.get_user_by_telegram_id(123456789)
    user2 = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user1.keywords) == 1
    assert len(user2.keywords) == 1
    assert user1.keywords[0].id == user2.keywords[0].id


@pytest.mark.asyncio
async def test_remove_keyword(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    res = await adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1

    res = await adbot_srv.remove_keyword(user.id, 'new_keyword')
    assert res == True
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 0


@pytest.mark.asyncio
async def test_remove_keyword_return_true_if_not_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = await adbot_srv.remove_keyword(user.id, 'new_keyword')
    assert res == True
    user = await adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 0


@pytest.mark.asyncio
async def test_remove_keyword_raises_exception_if_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        await adbot_srv.remove_keyword(123456789, 'new_keyword')


@pytest.mark.asyncio
async def test_remove_keyword_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    res = await adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.remove_keyword(user.id, 'new_keyword')


@pytest.mark.asyncio
async def test_get_all_keywords_one_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_keyword(user.id, 'scooter')
    await adbot_srv.add_keyword(user.id, 'sofa')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = await adbot_srv._get_all_keywords(session)

    assert keywords is not None
    assert len(keywords) == 3

    for kw, users in keywords.items():
        assert len(users) == 1


@pytest.mark.asyncio
async def test_get_all_keywords_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_keyword(user.id, 'scooter')
    await adbot_srv.add_keyword(user.id, 'sofa')

    user = await adbot_srv.create_user_by_telegram_data(22222, 'dsa')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_keyword(user.id, 'bicycle')
    await adbot_srv.add_keyword(user.id, 'pen')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = await adbot_srv._get_all_keywords(session)

    assert keywords is not None
    assert len(keywords) == 5

    kw_users = {
        'apple': 2,
        'scooter': 1,
        'sofa': 1,
        'bicycle': 1,
        'pen': 1
    }
    for kw, users in keywords.items():
        assert len(users) == kw_users[kw]


@pytest.mark.asyncio
async def test_get_all_keywords_subscription_on_off(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user1.id, True)
    await adbot_srv.add_keyword(user1.id, 'apple')
    await adbot_srv.add_keyword(user1.id, 'scooter')
    await adbot_srv.add_keyword(user1.id, 'sofa')

    user2 = await adbot_srv.create_user_by_telegram_data(22222, 'dsa')
    await adbot_srv.set_subscription_state(user2.id, True)
    await adbot_srv.add_keyword(user2.id, 'apple')
    await adbot_srv.add_keyword(user2.id, 'bicycle')
    await adbot_srv.add_keyword(user2.id, 'pen')

    user3 = await adbot_srv.create_user_by_telegram_data(33333, 'sda')
    await adbot_srv.set_subscription_state(user3.id, True)
    await adbot_srv.add_keyword(user3.id, 'car')
    await adbot_srv.add_keyword(user3.id, 'bicycle')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = await adbot_srv._get_all_keywords(session)

    assert keywords is not None
    assert len(keywords) == 6

    kw_users = {
        'apple': 2,
        'scooter': 1,
        'sofa': 1,
        'bicycle': 2,
        'car': 1,
        'pen': 1
    }
    for kw, users in keywords.items():
        assert len(users) == kw_users[kw]

    # Set subscription state of user2 to False. His keywords should be excluded
    await adbot_srv.set_subscription_state(user2.id, False)
    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = await adbot_srv._get_all_keywords(session)

    assert keywords is not None
    assert len(keywords) == 5

    kw_users = {
        'apple': 1,
        'scooter': 1,
        'sofa': 1,
        'bicycle': 1,
        'car': 1,
        'pen': 0
    }
    for kw, users in keywords.items():
        assert len(users) == kw_users[kw]


# ==============================================================================================
# message management

@pytest.mark.asyncio
async def test_add_message(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    res = await adbot_srv.add_message(11, 22, 'message_text', 'https://t.me/c/123/456')
    assert res == True

    messages = None
    session: Session
    with adbot_srv._db_pool() as session:
        messages = session.scalars(select(models.GroupChatMessage)).all()
    
    assert messages is not None
    assert len(messages) == 1
    for message in messages:
        assert message.processed == False
        assert message.cat_id == 11
        assert message.source_id == 22
        assert message.text == 'message_text'
        assert message.url == 'https://t.me/c/123/456'
        assert (message.text_hash is not None) and (len(message.text_hash) == 32)


@pytest.mark.asyncio
async def test_add_message_raise_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv.add_message(11, 22, 'message_text', 'https://t.me/c/123/456')


@pytest.mark.asyncio
async def test_process_messages_one_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    res = await adbot_srv.add_message(11, 22, 'apple banana orange', 'https://t.me/c/123/456')
    res = await adbot_srv.add_message(12, 23, 'car bicycle scooter', 'https://t.me/c/456/789')
    res = await adbot_srv.add_message(13, 24, 'pen pencil brush', 'https://t.me/c/789/012')
    res = await adbot_srv.add_message(14, 25, 'chair table sofa', 'https://t.me/c/012/345')

    user = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)

    res = await adbot_srv.add_keyword(user.id, 'apple')
    res = await adbot_srv.add_keyword(user.id, 'scooter')
    res = await adbot_srv.add_keyword(user.id, 'sofa')

    res = await adbot_srv._process_messages()
    assert res is None

    # check `processed`=1
    res = None
    with adbot_srv._db_pool() as session:
        res = session.execute(text(f"SELECT processed FROM chat_message")).all()
    assert res is not None
    assert len(res) == 4
    assert res[0][0] == 1
    assert res[1][0] == 1
    assert res[2][0] == 1
    assert res[3][0] == 1

    # Check messages are prepeared for forwarding
    res = None
    with adbot_srv._db_pool() as session:
        res = session.execute(text(f"SELECT user_id, message_id FROM user_message_link")).all()

    msg_ids = [1, 2, 4]
    assert res is not None
    assert len(res) == 3
    assert (res[0][0] == user.id)
    assert (res[1][0] == user.id)
    assert (res[2][0] == user.id)
    assert (res[0][1] in msg_ids)
    msg_ids.remove(res[0][1])
    assert (res[1][1] in msg_ids)
    msg_ids.remove(res[1][1])
    assert (res[2][1] in msg_ids)
    msg_ids.remove(res[2][1])


@pytest.mark.asyncio
async def test_process_messages_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    await adbot_srv.add_message(11, 22, 'apple banana orange', 'https://t.me/c/123/456')

    user = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)

    await adbot_srv.add_keyword(user.id, 'apple')

    adbot_srv._db_pool = brake_sessionmaker(adbot_srv._db_pool)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        await adbot_srv._process_messages()


# ==============================================================================================
# Message forwarding

@pytest.mark.asyncio
async def test_forward_messages(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotMessageForwardRequest], fake_subscriber_func_local)

    await adbot_srv.add_message(11, 22, 'apple banana orange', 'https://t.me/c/123/456')
    await adbot_srv.add_message(12, 23, 'car bicycle', 'https://t.me/c/234/567')

    user = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.set_forwarding_state(user.id, True)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_keyword(user.id, 'bicycle')
    await adbot_srv._process_messages()

    await adbot_srv._forward_messages()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    expected_messages = {
        'apple banana orange',
        'car bicycle'
    }

    assert len(catched_events) == 2
    assert catched_events[0].message_text in expected_messages
    expected_messages.remove(catched_events[0].message_text)
    assert catched_events[1].message_text in expected_messages
    expected_messages.remove(catched_events[1].message_text)
    assert len(expected_messages) == 0


@pytest.mark.asyncio
async def test_forward_messages_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotMessageForwardRequest], fake_subscriber_func_local)

    await adbot_srv.add_message(11, 22, 'apple banana orange', 'https://t.me/c/123/456')
    await adbot_srv.add_message(12, 23, 'car bicycle', 'https://t.me/c/234/567')
    await adbot_srv.add_message(13, 24, 'sofa', 'https://t.me/c/345/678')

    user1 = await adbot_srv.create_user_by_telegram_data(11111, 'asd')
    await adbot_srv.set_subscription_state(user1.id, True)
    await adbot_srv.set_forwarding_state(user1.id, True)
    await adbot_srv.add_keyword(user1.id, 'apple')
    await adbot_srv.add_keyword(user1.id, 'bicycle')

    user2 = await adbot_srv.create_user_by_telegram_data(22222, 'dsa')
    await adbot_srv.set_subscription_state(user2.id, True)
    await adbot_srv.set_forwarding_state(user2.id, True)
    await adbot_srv.add_keyword(user2.id, 'bicycle')
    await adbot_srv.add_keyword(user2.id, 'sofa')

    await adbot_srv._process_messages()
    await adbot_srv._forward_messages()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    messages_to_users = {
        'apple banana orange': {user1.id},
        'car bicycle': {user1.id, user2.id},
        'sofa': {user2.id},
    }

    assert len(catched_events) == 4

    assert catched_events[0].user_id in messages_to_users[catched_events[0].message_text]
    messages_to_users[catched_events[0].message_text].remove(catched_events[0].user_id)

    assert catched_events[1].user_id in messages_to_users[catched_events[1].message_text]
    messages_to_users[catched_events[1].message_text].remove(catched_events[1].user_id)

    assert catched_events[2].user_id in messages_to_users[catched_events[2].message_text]
    messages_to_users[catched_events[2].message_text].remove(catched_events[2].user_id)

    assert catched_events[3].user_id in messages_to_users[catched_events[3].message_text]
    messages_to_users[catched_events[3].message_text].remove(catched_events[3].user_id)


# ==============================================================================================
# Inactivity timeout events

@pytest.mark.asyncio
async def test_inactivity_timeouts_none_when_menu_closed(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    adbot_srv._menu_activity_cache[user.id] = {
        'menu_closed': True,
        'act_dt': datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES*2)
    }
    await adbot_srv._check_idle_timeouts()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 0
    

@pytest.mark.asyncio
async def test_inactivity_timeouts_none_when_user_active(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_menu_closed_state(user.id, False)
    await adbot_srv.reset_idle_timeout(user.id)
    await adbot_srv._check_idle_timeouts()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 0
    

@pytest.mark.asyncio
async def test_inactivity_timeouts_none_when_user_active_2(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_menu_closed_state(user.id, False)
    adbot_srv._menu_activity_cache[user.id]['act_dt'] = datetime.now() - timedelta(seconds=IDLE_TIMEOUT_MINUTES*60 - 1)

    await adbot_srv._check_idle_timeouts()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 0
    


@pytest.mark.asyncio
async def test_inactivity_timeouts_event_when_user_inactive_and_menu_open(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_menu_closed_state(user.id, False)
    adbot_srv._menu_activity_cache[user.id]['act_dt'] = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES*2)
    await adbot_srv._check_idle_timeouts()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 1


@pytest.mark.asyncio
async def test_inactivity_timeouts_several_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotInactivityTimeout], fake_subscriber_func_local)

    # User1 - menu is open and user is inactive
    user1 = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_menu_closed_state(user1.id, False)
    adbot_srv._menu_activity_cache[user1.id]['act_dt'] = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)

    # User2 - menu is open and user is active
    user2 = await adbot_srv.create_user_by_telegram_data(222222, 'dsa')
    await adbot_srv.set_menu_closed_state(user2.id, False)

    # User3 - menu is open and user is inactive
    user3 = await adbot_srv.create_user_by_telegram_data(333333, 'sda')
    await adbot_srv.set_menu_closed_state(user3.id, False)
    adbot_srv._menu_activity_cache[user3.id]['act_dt'] = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES*2)

    await adbot_srv._check_idle_timeouts()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 2     # InactivityTimeout events for User1 and User3
    uids = [user1.id, user3.id]
    assert catched_events[0].user_id in uids
    uids.remove(catched_events[0].user_id)
    assert catched_events[1].user_id in uids
    uids.remove(catched_events[1].user_id)


# ==============================================================================================
# `User data updated` events

@pytest.mark.asyncio
async def test_check_user_data_updated_generate_event(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotUserDataUpdated], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.set_forwarding_state(user.id, True)
    await adbot_srv.set_menu_closed_state(user.id, False)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_message(1, 1, 'apple and banana', 'http://t.me/c/11/11')
    await adbot_srv._process_messages()
    await adbot_srv._forward_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 1
    assert catched_events[0].user_id == user.id


@pytest.mark.asyncio
async def test_check_user_data_updated_doesnt_generate_event_if_menu_closed(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotUserDataUpdated], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.set_forwarding_state(user.id, True)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_message(1, 1, 'apple and banana', 'http://t.me/c/11/11')
    await adbot_srv._process_messages()
    await adbot_srv._forward_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 0


@pytest.mark.asyncio
async def test_check_user_data_updated_doesnt_duplicate_event(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotUserDataUpdated], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.set_forwarding_state(user.id, True)
    await adbot_srv.set_menu_closed_state(user.id, False)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_message(1, 1, 'apple and banana', 'http://t.me/c/11/11')
    await adbot_srv._process_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks
    await adbot_srv._process_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 1
    assert catched_events[0].user_id == user.id


@pytest.mark.asyncio
async def test_check_user_data_updated_generate_second_event(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotUserDataUpdated], fake_subscriber_func_local)

    user = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_subscription_state(user.id, True)
    await adbot_srv.set_forwarding_state(user.id, True)
    await adbot_srv.set_menu_closed_state(user.id, False)
    await adbot_srv.add_keyword(user.id, 'apple')
    await adbot_srv.add_message(1, 1, 'apple and banana', 'http://t.me/c/11/11')
    await adbot_srv._process_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    await adbot_srv.add_message(2, 2, 'one more apple', 'http://t.me/c/22/22')
    await adbot_srv._process_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 2
    assert catched_events[0].user_id == user.id
    assert catched_events[1].user_id == user.id


@pytest.mark.asyncio
async def test_check_user_data_updated_generate_events_several_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    catched_events = []
    async def fake_subscriber_func_local(event: mb.AdBotEvent):
        catched_events.append(event)

    adbot_srv.messagebus.subscribe([events.AdBotUserDataUpdated], fake_subscriber_func_local)

    user1 = await adbot_srv.create_user_by_telegram_data(111111, 'asd')
    await adbot_srv.set_subscription_state(user1.id, True)
    await adbot_srv.set_forwarding_state(user1.id, True)
    await adbot_srv.set_menu_closed_state(user1.id, False)
    await adbot_srv.add_keyword(user1.id, 'apple')

    user2 = await adbot_srv.create_user_by_telegram_data(222222, 'dsa')
    await adbot_srv.set_subscription_state(user2.id, True)
    await adbot_srv.set_forwarding_state(user2.id, True)
    await adbot_srv.set_menu_closed_state(user2.id, False)
    await adbot_srv.add_keyword(user2.id, 'banana')

    user3 = await adbot_srv.create_user_by_telegram_data(333333, 'sda')
    await adbot_srv.set_subscription_state(user3.id, True)
    await adbot_srv.set_forwarding_state(user3.id, True)
    await adbot_srv.set_menu_closed_state(user3.id, False)
    await adbot_srv.add_keyword(user3.id, 'orange')

    await adbot_srv.add_message(1, 1, 'apple and banana', 'http://t.me/c/11/11')
    await adbot_srv._process_messages()
    await adbot_srv._check_user_data_updated()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    assert len(catched_events) == 2     # UserDataUpdated events for user1 and user2
    uids = [user1.id, user2.id]
    assert catched_events[0].user_id in uids
    uids.remove(catched_events[0].user_id)
    assert catched_events[1].user_id in uids
    uids.remove(catched_events[1].user_id)
