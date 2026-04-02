"""add_admin_operation_logs

Revision ID: 1d65a70de5ac
Revises: c98ea8d578d4
Create Date: 2026-03-29 21:29:52.171742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d65a70de5ac'
down_revision: Union[str, Sequence[str], None] = 'c98ea8d578d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('admin_operation_logs'):
        op.create_table('admin_operation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('old_value', sa.String(length=60), nullable=True),
        sa.Column('new_value', sa.String(length=60), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('detail', sa.String(length=240), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('admin_operation_logs'):
        op.drop_table('admin_operation_logs')
