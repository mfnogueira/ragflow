"""Create escalation_requests table.

Revision ID: 006
Revises: 005
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create escalation_requests table."""
    op.create_table(
        'escalation_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('reason', sa.String(50), nullable=False, index=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('priority_score', sa.Float(), nullable=False, default=50.0, index=True),
        sa.Column('assignment_status', sa.String(30), nullable=False, default='queued', index=True),
        sa.Column('assigned_agent_id', sa.String(255), nullable=True, index=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_time_seconds', sa.Float(), nullable=True),
        sa.Column('agent_feedback', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['answer_id'], ['answers.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('idx_escalations_status_priority', 'escalation_requests', ['assignment_status', 'priority_score'])
    op.create_index('idx_escalations_escalated_at', 'escalation_requests', ['escalated_at'])


def downgrade() -> None:
    """Drop escalation_requests table."""
    op.drop_index('idx_escalations_escalated_at')
    op.drop_index('idx_escalations_status_priority')
    op.drop_table('escalation_requests')
