import pytest

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from adbot.domain.services import AdBotServices, exc
from adbot.domain import models


# ==============================================================================================
# helpers

def mock_method_raise_SQLAlchemyError(*arg, **kwarg):
    raise SQLAlchemyError()


def brake_sessionmaker(adbot_srv: AdBotServices):
    db_pool = adbot_srv._db_pool
    def broken_session_maker():
        session = db_pool()
        session.commit = mock_method_raise_SQLAlchemyError
        session.scalar = mock_method_raise_SQLAlchemyError
        session.scalars = mock_method_raise_SQLAlchemyError
        session.execute = mock_method_raise_SQLAlchemyError
        return session

    adbot_srv._db_pool = broken_session_maker


# ==============================================================================================
# get_user, create_user (by user_id, by telegram_id)

def test_get_user_by_user_id_returns_none_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.get_user_by_id(123)
    
    assert user is None


def test_get_user_by_tg_id_returns_none_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.get_user_by_telegram_id(123456789)
    
    assert user is None


def test_create_user_by_tg_data_returns_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    
    assert user is not None
    assert user.telegram_id == 123456789
    assert user.telegram_name == 'asd'


def test_create_user_by_tg_data_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv
    brake_sessionmaker(adbot_srv)    # broken DB returns SQLAlchemyError on every query and commit

    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    


def test_get_user_by_telegram_id_returns_correct_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    user1 = adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.telegram_id == 123456789
    assert user1.telegram_name == 'asd'

    user2 = adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.telegram_id == 987654321
    assert user2.telegram_name == 'dsa'


def test_get_user_by_user_id_returns_correct_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    created_user1 = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    created_user2 = adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    selected_user = adbot_srv.get_user_by_id(created_user1.id)
    assert selected_user is not None
    assert selected_user.id == created_user1.id
    assert selected_user.telegram_id == 123456789
    assert selected_user.telegram_name == 'asd'

    selected_user = adbot_srv.get_user_by_id(created_user2.id)
    assert selected_user is not None
    assert selected_user.id == created_user2.id
    assert selected_user.telegram_id == 987654321
    assert selected_user.telegram_name == 'dsa'


# ==============================================================================================
# user subscription state management

def test_subscription_state_default_is_false(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.subscription_state is False

    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is False


def test_set_subscription_state(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.subscription_state is False

    adbot_srv.set_subscription_state(user.id, True)
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is True

    adbot_srv.set_subscription_state(user.id, False)
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.subscription_state is False


def test_set_subscription_state_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user1.subscription_state is False
    user2 = adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')
    assert user2.subscription_state is False

    adbot_srv.set_subscription_state(user1.id, True)
    
    user1 = adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.subscription_state is True
    user2 = adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.subscription_state is False

    adbot_srv.set_subscription_state(user2.id, True)
    adbot_srv.set_subscription_state(user1.id, False)

    user1 = adbot_srv.get_user_by_telegram_id(123456789)
    assert user1.subscription_state is False
    user2 = adbot_srv.get_user_by_telegram_id(987654321)
    assert user2.subscription_state is True


def test_set_subscription_state_raises_exception_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        adbot_srv.set_subscription_state(123, True)


def test_set_subscription_state_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    brake_sessionmaker(adbot_srv)
    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.set_subscription_state(user.id, True)



# ==============================================================================================
# user menu closed state management

def test_menu_closed_state_default_is_true(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.menu_closed is True

    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is True


def test_set_menu_closed_state(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    assert user.menu_closed is True

    adbot_srv.set_menu_closed_state(user.id, False)
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is False

    adbot_srv.set_menu_closed_state(user.id, True)
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert user.menu_closed is True


def test_set_menu_closed_state_raises_exception_when_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        adbot_srv.set_menu_closed_state(123, True)


def test_set_menu_closed_state_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    brake_sessionmaker(adbot_srv)
    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.set_menu_closed_state(user.id, True)


# ==============================================================================================
# user keywords list management

def test_add_keyword(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1
    assert user.keywords[0].word == 'new_keyword'


def test_add_keyword_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    brake_sessionmaker(adbot_srv)    # broken DB returns SQLAlchemyError on every query and commit

    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.add_keyword(user.id, 'new_keyword')


def test_add_keyword_raises_exception_if_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        adbot_srv.add_keyword(123456789, 'new_keyword')


def test_add_keyword_unique_in_user_list(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    res = adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1
    assert user.keywords[0].word == 'new_keyword'


def test_add_keyword_word_is_unique_in_db(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    user2 = adbot_srv.create_user_by_telegram_data(telegram_id=987654321, telegram_name='dsa')

    res = adbot_srv.add_keyword(user1.id, 'new_keyword')
    assert res == True

    res = adbot_srv.add_keyword(user2.id, 'new_keyword')
    assert res == True

    user1 = adbot_srv.get_user_by_telegram_id(123456789)
    user2 = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user1.keywords) == 1
    assert len(user2.keywords) == 1
    assert user1.keywords[0].id == user2.keywords[0].id


def test_remove_keyword(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    res = adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 1

    res = adbot_srv.remove_keyword(user.id, 'new_keyword')
    assert res == True
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 0


def test_remove_keyword_return_true_if_not_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')

    res = adbot_srv.remove_keyword(user.id, 'new_keyword')
    assert res == True
    user = adbot_srv.get_user_by_telegram_id(123456789)
    assert len(user.keywords) == 0


def test_remove_keyword_raises_exception_if_user_doesnt_exist(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    with pytest.raises(exc.AdBotExceptionUserNotExist):
        adbot_srv.remove_keyword(123456789, 'new_keyword')


def test_remove_keyword_raises_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(telegram_id=123456789, telegram_name='asd')
    res = adbot_srv.add_keyword(user.id, 'new_keyword')
    assert res == True

    brake_sessionmaker(adbot_srv)    # broken DB returns SQLAlchemyError on every query and commit
    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.remove_keyword(user.id, 'new_keyword')


def test_get_all_keywords_one_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(11111, 'asd')
    adbot_srv.set_subscription_state(user.id, True)
    adbot_srv.add_keyword(user.id, 'apple')
    adbot_srv.add_keyword(user.id, 'scooter')
    adbot_srv.add_keyword(user.id, 'sofa')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = adbot_srv._get_all_keywords(session)

    assert keywords is not None
    assert len(keywords) == 3

    for kw, users in keywords.items():
        assert len(users) == 1


def test_get_all_keywords_two_users(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user = adbot_srv.create_user_by_telegram_data(11111, 'asd')
    adbot_srv.set_subscription_state(user.id, True)
    adbot_srv.add_keyword(user.id, 'apple')
    adbot_srv.add_keyword(user.id, 'scooter')
    adbot_srv.add_keyword(user.id, 'sofa')

    user = adbot_srv.create_user_by_telegram_data(22222, 'dsa')
    adbot_srv.set_subscription_state(user.id, True)
    adbot_srv.add_keyword(user.id, 'apple')
    adbot_srv.add_keyword(user.id, 'bicycle')
    adbot_srv.add_keyword(user.id, 'pen')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = adbot_srv._get_all_keywords(session)

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


def test_get_all_keywords_subscription_on_off(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    user1 = adbot_srv.create_user_by_telegram_data(11111, 'asd')
    adbot_srv.set_subscription_state(user1.id, True)
    adbot_srv.add_keyword(user1.id, 'apple')
    adbot_srv.add_keyword(user1.id, 'scooter')
    adbot_srv.add_keyword(user1.id, 'sofa')

    user2 = adbot_srv.create_user_by_telegram_data(22222, 'dsa')
    adbot_srv.set_subscription_state(user2.id, True)
    adbot_srv.add_keyword(user2.id, 'apple')
    adbot_srv.add_keyword(user2.id, 'bicycle')
    adbot_srv.add_keyword(user2.id, 'pen')

    user3 = adbot_srv.create_user_by_telegram_data(33333, 'sda')
    adbot_srv.set_subscription_state(user3.id, True)
    adbot_srv.add_keyword(user3.id, 'car')
    adbot_srv.add_keyword(user3.id, 'bicycle')

    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = adbot_srv._get_all_keywords(session)

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
    adbot_srv.set_subscription_state(user2.id, False)
    keywords= None
    with adbot_srv._db_pool() as session:
        keywords = adbot_srv._get_all_keywords(session)

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

def test_add_message(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    res = adbot_srv.add_message(11, 22, 'message_text', 'https://t.me/c/123/456')
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


def test_add_message_raise_exception_on_sql_error(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    brake_sessionmaker(adbot_srv)
    with pytest.raises(exc.AdBotExceptionSQL):
        adbot_srv.add_message(11, 22, 'message_text', 'https://t.me/c/123/456')


def test_process_messages_one_user(in_memory_adbot_srv: AdBotServices):
    adbot_srv = in_memory_adbot_srv

    res = adbot_srv.add_message(11, 22, 'apple banana orange', 'https://t.me/c/123/456')
    res = adbot_srv.add_message(12, 23, 'car bicycle scooter', 'https://t.me/c/456/789')
    res = adbot_srv.add_message(13, 24, 'pen pencil brush', 'https://t.me/c/789/012')
    res = adbot_srv.add_message(14, 25, 'chair table sofa', 'https://t.me/c/012/345')

    user = adbot_srv.create_user_by_telegram_data(11111, 'asd')
    adbot_srv.set_subscription_state(user.id, True)

    res = adbot_srv.add_keyword(user.id, 'apple')
    res = adbot_srv.add_keyword(user.id, 'scooter')
    res = adbot_srv.add_keyword(user.id, 'sofa')

    res = adbot_srv.process_messages()
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
