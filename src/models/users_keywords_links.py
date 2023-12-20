from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class UserKeywordLink(SQLModel, table=True):
    __tablename__ = "users_keywords_links"

    user_uuid: Optional[UUID] = Field(default=None, foreign_key="users.uuid", primary_key=True)
    keyword_id: Optional[int] = Field(default=None, foreign_key="keywords.id", primary_key=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", primary_key=True)
