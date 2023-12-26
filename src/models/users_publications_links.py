from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel, UniqueConstraint


class UserPublicationLink(SQLModel, table=True):
    __tablename__ = "users_publications_links"
    __table_args__ = (
        UniqueConstraint("user_uuid", "publication_id", name='u_user_pub'),
    )

    id: Optional[int] = Field(primary_key=True, index=True, nullable=False)

    user_uuid: UUID = Field(default=None, foreign_key="users.uuid")
    publication_id: int = Field(default=None, foreign_key="publications.id")


