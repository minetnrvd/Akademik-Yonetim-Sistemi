"""add_query_performance_indexes

Revision ID: a9f3c1d2e4b7
Revises: 7f3b8b7ef2b2
Create Date: 2026-03-30 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f3c1d2e4b7'
down_revision: Union[str, Sequence[str], None] = '7f3b8b7ef2b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_PLAN = {
    'users': [
        ('ix_users_role', ['role']),
        ('ix_users_is_locked', ['is_locked']),
    ],
    'classes': [
        ('ix_classes_name', ['name']),
        ('ix_classes_teacher_id', ['teacher_id']),
    ],
    'attendance_sessions': [
        ('ix_attendance_sessions_class_id', ['class_id']),
        ('ix_attendance_sessions_date', ['date']),
        ('ix_attendance_sessions_active', ['active']),
        ('ix_attendance_sessions_confirmed', ['confirmed']),
        ('ix_attendance_sessions_class_active_date', ['class_id', 'active', 'date']),
        ('ix_attendance_sessions_class_confirmed_date', ['class_id', 'confirmed', 'date']),
    ],
    'attendance_records': [
        ('ix_attendance_records_student_id', ['student_id']),
        ('ix_attendance_records_session_id', ['session_id']),
        ('ix_attendance_records_present', ['present']),
        ('ix_attendance_records_session_present', ['session_id', 'present']),
        ('ix_attendance_records_student_session_present', ['student_id', 'session_id', 'present']),
    ],
    'student_calendar_events': [
        ('ix_student_calendar_events_student_id', ['student_id']),
        ('ix_student_calendar_events_event_date', ['event_date']),
    ],
    'permission_audit_logs': [
        ('ix_permission_audit_logs_created_at', ['created_at']),
        ('ix_permission_audit_logs_permission', ['permission']),
        ('ix_permission_audit_logs_role', ['role']),
        ('ix_permission_audit_logs_endpoint', ['endpoint']),
    ],
    'admin_operation_logs': [
        ('ix_admin_operation_logs_created_at', ['created_at']),
        ('ix_admin_operation_logs_actor_user_id', ['actor_user_id']),
        ('ix_admin_operation_logs_target_user_id', ['target_user_id']),
        ('ix_admin_operation_logs_action', ['action']),
        ('ix_admin_operation_logs_status', ['status']),
    ],
}


def _table_indexes(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {idx['name'] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in _INDEX_PLAN.items():
        existing_indexes = _table_indexes(inspector, table_name)
        if not existing_indexes and not inspector.has_table(table_name):
            continue
        for index_name, columns in indexes:
            if index_name not in existing_indexes:
                op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, indexes in _INDEX_PLAN.items():
        existing_indexes = _table_indexes(inspector, table_name)
        for index_name, _ in reversed(indexes):
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=table_name)
