"""add_permission_audit_logs

Revision ID: c98ea8d578d4
Revises: 11518b6da746
Create Date: 2026-03-29 01:53:10.760033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c98ea8d578d4'
down_revision: Union[str, Sequence[str], None] = '11518b6da746'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'permission_audit_logs' not in inspector.get_table_names():
        op.create_table(
            'permission_audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(length=20), nullable=True),
            sa.Column('endpoint', sa.String(length=120), nullable=True),
            sa.Column('permission', sa.String(length=120), nullable=True),
            sa.Column('method', sa.String(length=16), nullable=True),
            sa.Column('path', sa.String(length=300), nullable=True),
            sa.Column('ip', sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('permission_audit_logs')}
    if 'ix_permission_audit_logs_created_at' not in existing_indexes:
        op.create_index('ix_permission_audit_logs_created_at', 'permission_audit_logs', ['created_at'])
    if 'ix_permission_audit_logs_permission' not in existing_indexes:
        op.create_index('ix_permission_audit_logs_permission', 'permission_audit_logs', ['permission'])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()
    if 'permission_audit_logs' not in table_names:
        return

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('permission_audit_logs')}
    if 'ix_permission_audit_logs_permission' in existing_indexes:
        op.drop_index('ix_permission_audit_logs_permission', table_name='permission_audit_logs')
    if 'ix_permission_audit_logs_created_at' in existing_indexes:
        op.drop_index('ix_permission_audit_logs_created_at', table_name='permission_audit_logs')

    op.drop_table('permission_audit_logs')
