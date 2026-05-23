"""ensure chat_message table exists (legacy prod skipped 30bb9011ac3c)

Revision ID: c4e8f1a2b3d0
Revises: a1b2c3d4e5f6
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

from migrations.migration_utils import table_names


revision = 'c4e8f1a2b3d0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    tables = table_names(conn)

    if 'blog_post' not in tables:
        op.create_table(
            'blog_post',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('teaser', sa.String(length=500), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('slug', sa.String(length=100), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('image_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('slug'),
        )
        tables = table_names(conn)

    if 'chat_message' in tables:
        return

    fk_args = []
    if 'blog_post' in tables:
        fk_args.append(sa.ForeignKeyConstraint(['blog_post_id'], ['blog_post.id']))

    op.create_table(
        'chat_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('blog_post_id', sa.Integer(), nullable=True),
        *fk_args,
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    conn = op.get_bind()
    if 'chat_message' in table_names(conn):
        op.drop_table('chat_message')
