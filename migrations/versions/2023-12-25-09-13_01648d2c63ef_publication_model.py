"""publication model

Revision ID: 01648d2c63ef
Revises: 169be06f24c1
Create Date: 2023-12-25 09:13:25.004580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel 


# revision identifiers, used by Alembic.
revision: str = '01648d2c63ef'
down_revision: Union[str, None] = '169be06f24c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'publications',
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('dt', sa.DateTime(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('preview', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hash')
    )
    op.create_index(op.f('ix_publications_id'), 'publications', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_publications_id'), table_name='publications')
    op.drop_table('publications')
    # ### end Alembic commands ###
