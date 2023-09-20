from typing import List, Optional

from sqlalchemy import Table, Column, String, Boolean, ForeignKey, UnicodeText, Unicode
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship, query_expression


class Base(DeclarativeBase):
    pass


# Table for storying links of 'many to many' relationship between User and Keyword
# (List of keywords in user's list)
user_keyword_link = Table(
    "user_keyword_link",
    Base.metadata,
    Column("user_id", ForeignKey("user_account.id"), primary_key=True),
    Column("keyword_id", ForeignKey("keyword.id"), primary_key=True),
)


# Table for storying links of 'many to many' relationship between User and GroupChatMessage
# (Queue of messages to forward to user)
user_message_link = Table(
    "user_message_link",
    Base.metadata,
    Column("user_id", ForeignKey("user_account.id"), primary_key=True),
    Column("message_id", ForeignKey("chat_message.id"), primary_key=True),
)


# Users and their settings
class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)  # Telegram user ID
    telegram_id: Mapped[int] = mapped_column(nullable=True)
    telegram_name: Mapped[str] = mapped_column(Unicode(32), nullable=True, default=None)
    subscription_state: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    forwarding_state: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    menu_closed: Mapped[bool] = mapped_column(Boolean, nullable=True, default=True)
    forward_queue_len: Mapped[int] = query_expression()
    keywords_limit: int = 10

    forward_queue: Mapped[List["GroupChatMessage"]] = relationship(
        secondary=user_message_link, back_populates="users"
    )

    keywords: Mapped[List["Keyword"]] = relationship(
        secondary=user_keyword_link, back_populates="users"
    )

    def __str__(self) -> str:
        return f"User {self.id}"


# List of keywords (unique)
class Keyword(Base):
    __tablename__ = "keyword"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(Unicode(50))

    users: Mapped[List[User]] = relationship(
        secondary=user_keyword_link, back_populates="keywords"
    )

    def __str__(self) -> str:
        return f"{self.word}"


# All messages from group chats will be stored in this table.
class GroupChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column()
    cat_id: Mapped[int] = mapped_column()
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(UnicodeText)
    url: Mapped[str] = mapped_column(String(120))
    text_hash: Mapped[str] = mapped_column(String(16))

    users: Mapped[List[User]] = relationship(
        secondary=user_message_link, back_populates="forward_queue"
    )


