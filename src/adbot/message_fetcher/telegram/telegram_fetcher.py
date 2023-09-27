import asyncio
import logging
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.tl.custom.dialog import Dialog
from telethon.tl.types import Chat, Channel

from ..interface import MessageFetcher, AddMessageHandler

MAX_DIALOG_HISTORY_MESSAGES_CNT = 500

logger = logging.getLogger(__name__)


def _get_dialog_name(dialog: Dialog) -> str:
    if hasattr(dialog, "name"):
        return dialog.name
    else:
        return 'None'


def _get_msg_url(chat_entity: Chat | Channel, message: Message):
    if hasattr(chat_entity, 'username') and chat_entity.username:
        return f'https://t.me/{chat_entity.username}/{message.id}'
    else:
        return f'https://t.me/c/{chat_entity.id}/{message.id}'


class TelegramMessageFetcher(MessageFetcher):

    def __init__(
        self, add_message_handler: AddMessageHandler, api_id: int, api_hash: str,
        chats_filter: Optional[list[int]]
    ):
        super().__init__(add_message_handler)
        self._client = TelegramClient(
                'telethon.session',
                api_id,
                api_hash,
                system_version="4.16.30-vxCUSTOM",
                retry_delay=3
            )
        self._chats = chats_filter
        self._ignore_bots = True


    async def fetch_messages(self) -> None:
        """
            Goes through all the Group chats and Channels, checks new messages and adds
            them to DB by calling handler stored in `_add_message_handler`.
            Skips pprivat chats, messages from bots and messages without `from_id`.
            If there are more unreaded messages in the chat than
            MAX_DIALOG_HISTORY_MESSAGES_CNT, method will parse only the last
            MAX_DIALOG_HISTORY_MESSAGES_CNT messages and skip the older ones.
        """
        logger.debug('Telegram message fetcher. `Fetch messages` started')
        async with self._client:

            # Iterate through chats and messages, add messages to DB
            async for dialog in self._client.iter_dialogs():
                chat_entity = await self._client.get_entity(dialog) # Chat or Channel obj
                await asyncio.sleep(0.1)
                if (self._chats is None) or (chat_entity.id in self._chats):
                    await self._fetch_dialog_messages(dialog, chat_entity)

        logger.debug('Telegram message fetcher. `Fetch messages` finiished')


    async def _fetch_dialog_messages(
        self, dialog: Dialog, chat_entity: Chat | Channel
    ) -> None:
        if not (dialog.is_channel or dialog.is_group):
            logger.debug(
                "Telegram message fetcher. " \
                f"Skip parsing chat '{_get_dialog_name(dialog)}' " \
                "(type is not Group or Channel)"
            )
            return

        logger.debug(
            "Telegram message fetcher. " \
            f"Parse chat '{_get_dialog_name(dialog)}'. " \
            f"Unreaded: {dialog.unread_count}"
        )

        unread_cnt = min(dialog.unread_count, MAX_DIALOG_HISTORY_MESSAGES_CNT)
        if dialog.unread_count > unread_cnt:
            skipped = (dialog.unread_count - unread_cnt)
            logger.warning(f'Telegram message fetcher. Skipped {skipped} msgs')

        max_msg_id = 0
        messages = self._client.iter_messages(dialog, limit=unread_cnt)
        message: Message
        async for message in messages:
            try:
                if hasattr(message, 'from_id') and message.from_id:
                    if message.message:
                        sender = await self._client.get_entity(message.from_id)
                        await asyncio.sleep(0.1)
                        is_not_bot = hasattr(sender, 'bot') and (not sender.bot)
                        if (not self._ignore_bots) or is_not_bot:
                            url = _get_msg_url(chat_entity, message)
                            await self._add_message_handler(0, 0, message.message, url)
                            max_msg_id = max(max_msg_id, message.id)
            except Exception as e:
                logger.error(f"Telegram message fetcher. Exception: {e}")

        if max_msg_id > 0:
            await self._client.send_read_acknowledge(dialog, max_id=max_msg_id)



