"""Create file_metadata table manually

Revision ID: cf83a8c12307
Revises:
Create Date: 2026-01-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = 'cf83a8c12307'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'file_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('s3_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('s3_path')
    )
    op.create_index(op.f('ix_file_metadata_owner_id'), 'file_metadata', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_file_metadata_owner_id'), table_name='file_metadata')
    op.drop_table('file_metadata')
