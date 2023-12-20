from typing import Optional
import uuid as uuid_pkg

from sqlmodel import Field, SQLModel, Relationship

from common_types import Lang
from models.users_keywords_links import UserKeywordLink
from models.keyword import KeywordInDB
from models.category import CategoryInDB


class UserBase(SQLModel):
    name: str = Field(index=True, unique=True, min_length=2, max_length=50)
    telegram_id: Optional[int] = Field(nullable=True, default=None, unique=True, index=True)


class User(UserBase):
    uuid: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    active: bool = Field(default=True)
    lang: Lang = Field(default=Lang.en)


class UserInDB(User, table=True):
    __tablename__ = "users"
    keywords: list[KeywordInDB] = Relationship(link_model=UserKeywordLink)


class UserCreate(UserBase):
    pass


class UserPatch(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    lang: Optional[Lang] = None
    telegram_id: Optional[int] = None
    

class UserOutput(User):
    pass
