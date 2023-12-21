from typing import Optional

from sqlmodel import Field, SQLModel

from common_types import SourceType


class SourceBase(SQLModel):
    title: str = Field(index=True, unique=True, min_length=2, max_length=100)
    type: SourceType = Field(index=True, nullable=False)
    source_info: str = Field(max_length=150)
    category_id: int = Field(nullable=False, foreign_key="categories.id")


class Source(SourceBase):
    id: Optional[int] = Field(
        primary_key=True,
        index=True,
        nullable=False,
    )


class SourceInDB(Source, table=True):
    __tablename__ = "sources"


class SourceCreate(SourceBase):
    pass


class SourcePatch(SQLModel):
    title: Optional[str] = Field(min_length=2, max_length=100, default=None)
    type: Optional[SourceType] = None
    source_info: Optional[str] = Field(max_length=150, default=None)
    category_id: Optional[int] = None


class SourceOutput(Source):
    pass
