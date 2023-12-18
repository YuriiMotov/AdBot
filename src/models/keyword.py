from typing import Optional

from sqlmodel import Field, SQLModel


class KeywordBase(SQLModel):
    word: str = Field(index=True, unique=True, min_length=2, max_length=50)


class Keyword(KeywordBase):
    id: Optional[int] = Field(
        primary_key=True,
        index=True,
        nullable=False,
    )


class KeywordInDB(Keyword, table=True):
    __tablename__ = "keywords"


class KeywordCreate(KeywordBase):
    pass


class KeywordOutput(Keyword):
    pass
