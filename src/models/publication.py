from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PublicationBase(SQLModel):
    url: str = Field(min_length=2, max_length=300)
    dt: datetime
    source_id: int = Field(foreign_key="sources.id")


class Publication(PublicationBase):
    id: Optional[int] = Field(
        primary_key=True,
        index=True,
        nullable=False,
    )
    hash: str = Field(min_length=32, max_length=32, unique=True)
    preview: str = Field(min_length=2, max_length=150)
    processed: bool = Field(default=False, )


class PublicationInDB(Publication, table=True):
    __tablename__ = "publications"


class PublicationCreate(PublicationBase):
    text: str


class PublicationOutput(Publication):
    pass