"""Create embedding_jobs table.

Revision ID: 007
Revises: 006
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create embedding_jobs table."""
    op.create_table(
        'embedding_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(30), nullable=False, default='pending', index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('batch_size', sa.Integer(), nullable=False, default=100),
        sa.Column('processed_count', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_count', sa.Integer(), nullable=False, default=0),
        sa.Column('error_messages', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_embedding_jobs_status_started', 'embedding_jobs', ['status', 'started_at'])


def downgrade() -> None:
    """Drop embedding_jobs table."""
    op.drop_index('idx_embedding_jobs_status_started')
    op.drop_table('embedding_jobs')
