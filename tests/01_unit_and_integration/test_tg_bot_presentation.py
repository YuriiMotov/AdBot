import asyncio
from datetime import datetime, timedelta
import pytest
from unittest.mock import AsyncMock, patch

from aiogram_dialog.test_tools.keyboard import InlineButtonTextLocator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adbot.domain import models
from adbot.domain.services import IDLE_TIMEOUT_MINUTES
from adbot.domain.services import events
from conftest import Env, brake_sessionmaker

# ========================================================================================
# Start cmd

@pytest.mark.asyncio
async def test_first_start_cmd_creates_user(env: Env):
    await env.client.send("/start")

    message = env.message_manager.one_message()
    assert message.text.startswith('<b>Subscr') == True

    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    assert user.telegram_id == env.client.user.id


@pytest.mark.asyncio
async def test_second_start_cmd_doesnt_create_duplicate_of_user(env: Env):
    await env.client.send("/start")

    env.message_manager.reset_history()
    await env.client.send("/start")

    message = env.message_manager.last_message()
    assert message.text.startswith('<b>Subscr') == True

    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    assert user.telegram_id == env.client.user.id

    async with env.ad_bot_srv._db_pool() as session:
        session: AsyncSession
        users = (await session.scalars(select(models.User))).all()
   
    assert len(users) == 1


@pytest.mark.asyncio
async def test_start_cmd_shows_error_msg_on_sql_error(env: Env):
    env.ad_bot_srv._db_pool = brake_sessionmaker(env.ad_bot_srv._db_pool)

    await env.client.send("/start")

    message = env.message_manager.one_message()
    assert message.text.find('Service unavailable. Please try later') > 0


@pytest.mark.asyncio
async def test_start_cmd_closes_previous_dialog(env: Env):
    await env.client.send('/start')
    env.message_manager.reset_history()
    await env.client.send('/start')
    assert len(env.message_manager.sent_messages) == 3
    assert env.message_manager.sent_messages[0].text.find('Settings menu is closed') >= 0
    assert env.message_manager.sent_messages[2].text.startswith('<b>Subscr')



# help cmd

@pytest.mark.asyncio
async def test_help_cmd_user_doesnt_exist(env: Env):
    await env.client.send('/help')
    message = env.message_manager.one_message()
    assert message.text.startswith('<b>Help</b>') == True


@pytest.mark.asyncio
async def test_help_cmd_user_exist(env: Env):
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    await env.client.send('/help')
    message = env.message_manager.one_message()
    assert message.text.startswith('<b>Help</b>') == True


@pytest.mark.asyncio
async def test_help_dialog_close_shows_points(env: Env):
    await env.client.send('/help')
    message = env.message_manager.one_message()
    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Close')
    )
    env.message_manager.assert_answered(callback_id)

    assert len(env.message_manager.sent_messages) == 1
    assert env.message_manager.sent_messages[0].text is None


@pytest.mark.asyncio
async def test_help_dialog_close_shows_points(env: Env):
    await env.client.send('/help')
    message = env.message_manager.one_message()
    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Close')
    )
    env.message_manager.assert_answered(callback_id)
    assert len(env.message_manager.sent_messages) == 1
    assert env.message_manager.sent_messages[0].text is None


@pytest.mark.asyncio
async def test_help_cmd_closes_previous_dialog(env: Env):
    await env.client.send('/start')
    env.message_manager.reset_history()
    await env.client.send('/help')
    assert len(env.message_manager.sent_messages) == 3
    assert env.message_manager.sent_messages[0].text.find('Settings menu is closed') >= 0
    assert env.message_manager.sent_messages[2].text.startswith('<b>Help</b>')




# ========================================================================================
# Menu\settings cmd

@pytest.mark.parametrize('cmd', ['/menu', '/settings', '/start'])
@pytest.mark.asyncio
async def test_menu_cmd_shows_menu(env: Env, cmd):
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    await env.client.send(cmd)
    message = env.message_manager.one_message()
    assert message.text.startswith('<b>Subscr') == True


@pytest.mark.parametrize('cmd', ['/menu', '/settings', '/start'])
@pytest.mark.asyncio
async def test_menu_cmd_sets_menuclosed_to_false(env: Env, cmd):
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    await env.client.send(cmd)
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    assert user.menu_closed == False


# ========================================================================================
# Subcription state toggle

@pytest.mark.asyncio
async def test_subcription_enable_click(env: Env):
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    await env.client.send('/menu')

    message = env.message_manager.one_message()

    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Enable subscription'),
    )
    env.message_manager.assert_answered(callback_id)
    second_message = env.message_manager.one_message()
    assert second_message.text.find('✅ enabled')  > 0


@pytest.mark.asyncio
async def test_subcription_disable_click(env: Env):
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    await env.ad_bot_srv.set_subscription_state(user.id, True)
    await env.client.send('/menu')

    message = env.message_manager.one_message()

    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Disable subscription'),
    )
    env.message_manager.assert_answered(callback_id)
    second_message = env.message_manager.one_message()
    assert second_message.text.find('☑ disabled')  > 0


@pytest.mark.asyncio
async def test_subcription_toogle_click_shows_error_msg_on_sql_error(env: Env):
    # Open menu
    await env.client.send("/start")
    message = env.message_manager.one_message()
    env.message_manager.reset_history()

    # Brake sessionmaker and try to enable subscription.
    # Check that DB error message is displayed
    env.message_manager.reset_history()
    env.ad_bot_srv._db_pool = brake_sessionmaker(env.ad_bot_srv._db_pool)
    await env.client.click(
        message, InlineButtonTextLocator('Enable subscription'),
    )
    message = env.message_manager.one_message()
    assert message.text.find('Service unavailable. Please try later') > 0


# ========================================================================================
# Keywords managment

@pytest.mark.asyncio
async def test_show_keywords(env: Env):
    KEYWORDS = ['AbRaCaDaBrA', 'KEYWORD']
    KEYWORDS_LOWER = [kw.lower() for kw in KEYWORDS]
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    await env.ad_bot_srv.add_keyword(user.id, KEYWORDS[0])
    await env.ad_bot_srv.add_keyword(user.id, KEYWORDS[1])

    await env.client.send('/menu')
    message = env.message_manager.one_message()
    assert message.text.find(KEYWORDS_LOWER[0]) > 0
    assert message.text.find(KEYWORDS_LOWER[1]) > 0


@pytest.mark.asyncio
async def test_add_keywords(env: Env):
    KEYWORDS = ['AbRaCaDaBrA', 'KEYWORD']
    KEYWORDS_LOWER = [kw.lower() for kw in KEYWORDS]
    await env.client.send('/menu')
    message = env.message_manager.one_message()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Manage keywords'),
    )
    env.message_manager.assert_answered(callback_id)
    await env.client.send(KEYWORDS[0])
    env.message_manager.reset_history()
    await env.client.send(KEYWORDS[1])
    message = env.message_manager.one_message()
    assert message.text.find(KEYWORDS_LOWER[0]) > 0
    assert message.text.find(KEYWORDS_LOWER[1]) > 0


@pytest.mark.asyncio
async def test_remove_keywords(env: Env):
    KEYWORDS = ['AbRaCaDaBrA', 'KEYWORD']
    KEYWORDS_LOWER = [kw.lower() for kw in KEYWORDS]

    # Create user and add two keywords
    await env.ad_bot_srv.create_user_by_telegram_data(
        env.client.user.id, env.client.user.full_name
    )
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    await env.ad_bot_srv.add_keyword(user.id, KEYWORDS[0])
    await env.ad_bot_srv.add_keyword(user.id, KEYWORDS[1])

    # Open menu and navigate to remove keywords
    await env.client.send('/menu')
    message = env.message_manager.one_message()
    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Manage keywords'),
    )
    env.message_manager.assert_answered(callback_id)
    message = env.message_manager.one_message()
    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Remove keywords'),
    )
    env.message_manager.assert_answered(callback_id)
    message = env.message_manager.one_message()

    # Remove first keyword and navigate to 'Manage keywords'
    # Check that first keyword is absent, but second is exist
    callback_id = await env.client.click(
        message, InlineButtonTextLocator(f'❌ {KEYWORDS_LOWER[0]}'),
    )
    env.message_manager.assert_answered(callback_id)
    env.message_manager.reset_history()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator(f'Back'),
    )
    env.message_manager.assert_answered(callback_id)
    message = env.message_manager.one_message()
    assert message.text.find(KEYWORDS_LOWER[0]) < 0
    assert message.text.find(KEYWORDS_LOWER[1]) > 0


@pytest.mark.asyncio
async def test_add_keyword_shows_error_msg_on_sql_error(env: Env):
    # Open menu and navigate to 'Keywords management'
    await env.client.send("/start")
    message = env.message_manager.one_message()
    callback_id = await env.client.click(
        message, InlineButtonTextLocator('Manage keywords'),
    )
    env.message_manager.assert_answered(callback_id)
    
    # Brake sessionmaker and try to add keyword
    env.message_manager.reset_history()
    env.ad_bot_srv._db_pool = brake_sessionmaker(env.ad_bot_srv._db_pool)
    await env.client.send('something')
    message = env.message_manager.one_message()
    assert message.text.find('Service unavailable. Please try later') > 0


# ========================================================================================
# Message frowarding

@pytest.mark.asyncio
async def test_show_in_menu_number_of_messages_in_the_queue(env: Env):
    # Create user, message and add message to user's queue

    async with env.ad_bot_srv._db_pool() as session:
        session: AsyncSession
        user = models.User(telegram_id = env.client.user.id)
        msg = models.GroupChatMessage(
            source_id = 0,
            cat_id = 0, 
            text = 'some text',
            url = 'https://t.me',
            text_hash = ''
        )
        user.forward_queue.append(msg)
        session.add(user)
        await session.commit()

    # Open menu and check
    await env.client.send('/menu')
    message = env.message_manager.one_message()
    assert message.text.find('You have 1 forwarded messages') > 0


@pytest.mark.asyncio
async def test_MessageForwardRequest_event_handler_sends_message(env: Env):
    msg_url = 'https://t.me'
    # Create user, message and add message to user's queue
    async with env.ad_bot_srv._db_pool() as session:
        session: AsyncSession
        user = models.User(telegram_id = env.client.user.id)
        user.forwarding_state = True
        msg = models.GroupChatMessage(
            source_id = 0,
            cat_id = 0, 
            text = 'some text',
            url = msg_url,
            text_hash = ''
        )
        user.forward_queue.append(msg)
        session.add(user)
        await session.commit()
    
    # Call AdBotServices._forward_messages method to generate MessageForwardRequest events
    # And check that Bot.send() was called
    await env.ad_bot_srv._forward_messages()
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks
    env.tg_bot._bot.send_message.assert_awaited_once_with(
        env.client.user.id, msg_url
    )


# ========================================================================================
# Idle timeout event, close_dialog cmd

@pytest.mark.asyncio
async def test_InactivityTimeout_event_handler_sends_closedialog_cmd(env: Env):
    # Open menu, imitate idle timeout
    await env.client.send('/menu')
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)
    idle_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES*2)
    env.ad_bot_srv._menu_activity_cache[user.id]['act_dt'] = idle_point


    assert (await env.ad_bot_srv.get_is_idle_with_opened_menu(user.id)) == True


    # Call AdBotServices._check_idle_timeouts to generate MessageForwardRequest events
    # And check that TgBot._send_bot_cmd method was called
    await env.ad_bot_srv._check_idle_timeouts()

    await asyncio.sleep(0.1)     # Give time to process asyncio tasks
                                  # (more, because of async DB IO)

    env.tg_bot._send_bot_cmd.assert_awaited_once_with(
        '/close_dialog', env.client.user.id
    )


@pytest.mark.asyncio
async def test_closedialog_cmd_shows_dialog_closed_window(env: Env):
    # Open menu, imitate sending dialog_close cmd after idle timeout event
    await env.client.send('/menu')
    # env.message_manager.reset_history()
    await env.client.send('/close_dialog')
    await asyncio.sleep(0.00000001)     # Give time to process asyncio tasks

    # Check whether the menu was closed
    message = env.message_manager.sent_messages[-2]
    assert message.text.find('Settings menu is closed') > 0


@pytest.mark.asyncio
async def test_closedialog_cmd_does_nothing_when_menu_is_closed(env: Env):
    # Open menu, and close menu
    await env.client.send('/menu')
    message = env.message_manager.one_message()
    await env.client.click(
        message, InlineButtonTextLocator('Close menu'),
    )

    # Imitate sending dialog_close cmd after idle timeout event
    env.message_manager.reset_history()
    await env.client.send('/close_dialog')

    # Check that nothing happend
    assert len(env.message_manager.sent_messages) == 0


# ========================================================================================
# DataUpdated event

@pytest.mark.asyncio
async def test_UserDataUpdated_event_handler_sends_refreshdialog_cmd(env: Env):
    # Open menu, change user data
    await env.client.send('/menu')
    user = await env.ad_bot_srv.get_user_by_telegram_id(env.client.user.id)

    # Imitate DataUpdated event, check whether the TgBot._send_bot_cmd method was called
    env.ad_bot_srv.messagebus.post_event(
        events.AdBotUserDataUpdated(user.id)
    )
    await asyncio.sleep(0.1)     # Give time to process asyncio tasks
                                  # (more, because of async DB IO)

    env.tg_bot._send_bot_cmd.assert_awaited_once_with(
        '/refresh_dialog', env.client.user.id
    )
    

@pytest.mark.asyncio
async def test_refreshdialog_cmd_updates_data_in_window(env: Env):
    # Open menu, change user data, imitate refresh_dialog cmd
    await env.client.send('/menu')
    async with env.ad_bot_srv._db_pool() as session:
        session: AsyncSession
        user = await session.scalar(
            select(models.User).where(models.User.telegram_id == env.client.user.id) \
                .options(selectinload(models.User.forward_queue))
        )
        msg = models.GroupChatMessage(
            source_id = 0,
            cat_id = 0, 
            text = 'some text',
            url = 'https://t.me',
            text_hash = ''
        )
        user.forward_queue.append(msg)
        await session.commit()
    env.message_manager.reset_history()
    await env.client.send('/refresh_dialog')

    # Check whether the text in window was changed
    message = env.message_manager.one_message()
    assert message.text.find('You have 1 forwarded messages') > 0


# stop_bot cmd

@pytest.mark.asyncio
async def test_stopbot_cmd_from_admin(env: Env):
    with patch('adbot.domain.services.AdBotServices.stop', new=AsyncMock()):
        await env.client_admin.send('/stop_bot')
        env.ad_bot_srv.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_stopbot_cmd_from_not_admin_does_nothing(env: Env):
    with patch('adbot.domain.services.AdBotServices.stop', new=AsyncMock()):
        await env.client.send('/stop_bot')
        env.ad_bot_srv.stop.assert_not_awaited()
    

# menu navigation resets inactivity timer

# send to user who blocked bot
