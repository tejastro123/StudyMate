"""add_remote_ids

Revision ID: acb8bd63628d
Revises: a5da9b535813
Create Date: 2026-03-24 17:05:51.718186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acb8bd63628d'
down_revision: Union[str, Sequence[str], None] = 'a5da9b535813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add cloud-sync tracking columns."""
    tables = [
        "decks", "flashcards", "quizzes", "questions", 
        "timetable_events", "focus_sessions", "chat_sessions", 
        "chat_messages", "study_activity"
    ]
    
    for table in tables:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column('remote_id', sa.String(36), nullable=True))
            batch_op.add_column(sa.Column('is_dirty', sa.Integer(), server_default='0'))
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()))


def downgrade() -> None:
    """Downgrade schema: Remove cloud-sync tracking columns."""
    tables = [
        "decks", "flashcards", "quizzes", "questions", 
        "timetable_events", "focus_sessions", "chat_sessions", 
        "chat_messages", "study_activity"
    ]
    for table in tables:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column('remote_id')
            batch_op.drop_column('is_dirty')
            batch_op.drop_column('updated_at')
