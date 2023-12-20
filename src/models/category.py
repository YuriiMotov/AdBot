from typing import Optional

from sqlmodel import Field, SQLModel


class CategoryBase(SQLModel):
    name: str = Field(index=True, unique=True, min_length=2, max_length=50)


class Category(CategoryBase):
    id: Optional[int] = Field(
        primary_key=True,
        index=True,
        nullable=False,
    )


class CategoryInDB(Category, table=True):
    __tablename__ = "categories"


class CategoryCreate(CategoryBase):
    pass


class CategoryOutput(Category):
    pass
