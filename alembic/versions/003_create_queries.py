"""Create queries table.

Revision ID: 003
Revises: 002
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create queries table."""
    op.create_table(
        'queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_text', sa.String(1000), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True, index=True),
        sa.Column('collection_name', sa.String(100), nullable=False, index=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('language_code', sa.String(10), nullable=False, default='pt-BR'),
        sa.Column('status', sa.String(30), nullable=False, default='pending', index=True),
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('session_correlation_id', sa.String(100), nullable=True, index=True),
    )

    # Create indexes
    op.create_index('idx_queries_submitted_at', 'queries', ['submitted_at'])
    op.create_index('idx_queries_status_submitted', 'queries', ['status', 'submitted_at'])


def downgrade() -> None:
    """Drop queries table."""
    op.drop_index('idx_queries_status_submitted')
    op.drop_index('idx_queries_submitted_at')
    op.drop_table('queries')
