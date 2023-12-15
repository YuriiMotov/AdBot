from typing import Optional
import uuid as uuid_pkg

from sqlmodel import Field, SQLModel

from common_types import Lang


class UserBase(SQLModel):
    name: str = Field(index=True, unique=True, max_length=50)
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


class UserCreate(UserBase):
    pass


class UserPatch(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    lang: Optional[Lang] = None
    telegram_id: Optional[int] = None
    

class UserOutput(User):
    pass
