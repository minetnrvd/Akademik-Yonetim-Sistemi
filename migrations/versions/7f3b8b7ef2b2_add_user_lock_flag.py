"""add_user_lock_flag

Revision ID: 7f3b8b7ef2b2
Revises: 1d65a70de5ac
Create Date: 2026-03-29 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3b8b7ef2b2'
down_revision: Union[str, Sequence[str], None] = '1d65a70de5ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}
    if 'is_locked' not in columns:
        op.add_column('users', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()))
        op.execute(sa.text('UPDATE users SET is_locked = false WHERE is_locked IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}
    if 'is_locked' in columns:
        op.drop_column('users', 'is_locked')
